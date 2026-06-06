"""
pytest 全局 fixture

设计原则：
1. 每个测试独立临时 SQLite（test 隔离）
2. MiniMax / Pinecone 全部 mock（不消耗 token、不依赖网络）
3. 测试结束后自动清理

用法：
    async def test_foo(async_client, stan_token):
        resp = await async_client.get("/api/chat/stream", ...)
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# 确保 backend 路径可导入
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ==================== 事件循环 ====================

# 显式让 pytest-asyncio 用 function scope 避免 fixture 跨测试缓存
# pytest-asyncio v0.21+ 配置方式
# 设置在 pyproject.toml / pytest.ini 也可；这里用 fixture override 兜底
@pytest.fixture
def event_loop():
    """每个测试用独立 event loop。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ==================== 临时数据库 ====================

@pytest_asyncio.fixture
async def temp_db(monkeypatch) -> AsyncGenerator[str, None]:
    """
    每个测试独立临时 SQLite。
    关键：重置 backend.models.db_models 里的全局 engine + AsyncSessionLocal + Base.metadata
    """
    import importlib
    from backend.models import db_models
    from backend.models.db_models import Base

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{path}")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_SECRET", "test-secret-for-testing-only-32bytes")

    # 重建新 engine
    new_engine = create_async_engine(f"sqlite+aiosqlite:///{path}", echo=False)
    new_session = async_sessionmaker(new_engine, expire_on_commit=False)

    # 替换全局引用（db_models 模块顶）
    db_models.engine = new_engine
    db_models.AsyncSessionLocal = new_session

    # 关键：patch 所有 service 模块顶部的 AsyncSessionLocal 引用
    # （它们 at import time 就 capture 了旧 sessionmaker）
    patcher_auth = patch("backend.services.auth_service.AsyncSessionLocal", new_session)
    patcher_chat = patch("backend.services.chat_history_service.AsyncSessionLocal", new_session)
    patcher_progress = patch("backend.services.progress_service.AsyncSessionLocal", new_session)
    patcher_auth.start()
    patcher_chat.start()
    patcher_progress.start()

    # 在新 engine 上建表（Base.metadata 中的模型已通过 import 注册）
    async with new_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield path

    # 清理 patch
    patcher_progress.stop()
    patcher_chat.stop()
    patcher_auth.stop()

    # 清理
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


# ==================== Mocks ====================

@pytest.fixture
def mock_minimax(request):
    """Mock LLM 客户端（同步 fixture，避免 async generator 问题）。
    重要：agent_service/quiz_service 调用的是同步 OpenAI SDK，
    所以 chat.completions.create 必须是普通 MagicMock（不是 AsyncMock）。
    另：from X import Y 会复制引用，需 patch 每个消费模块。

    重构：get_chat_client → get_llm_client，返回 LLMClient(client, provider, model)
    """
    # 模拟 OpenAI 客户端
    fake_openai_client = MagicMock()
    fake_openai_client.chat.completions.create = MagicMock()

    # 模拟 LLMClient dataclass
    from backend.dependencies import LLMClient
    fake_llm = LLMClient(
        client=fake_openai_client,
        provider="minimax",
        model="MiniMax-M3",
    )

    modules_to_patch = [
        "backend.dependencies.get_llm_client",
        "backend.services.agent_service.get_llm_client",
        "backend.services.quiz_service.get_llm_client",
    ]
    patchers = [patch(m, return_value=fake_llm) for m in modules_to_patch]
    for p in patchers:
        p.start()
    request.addfinalizer(lambda: [p.stop() for p in patchers])
    return fake_openai_client  # 返回 OpenAI 客户端本身，便于测试设置 response


@pytest_asyncio.fixture
async def mock_pinecone() -> AsyncGenerator[MagicMock, None]:
    """Mock Pinecone index（健康检查依赖 vector store）。"""
    mock = MagicMock()
    mock.describe_index_stats.return_value = MagicMock(
        total_vector_count=841, dimension=1024
    )
    # 模拟 query 返回空 matches
    mock.query.return_value = MagicMock(matches=[])

    # 新版本用 get_vector_store_singleton 而非 get_pinecone_index
    from backend.services import vector_store as vs_mod
    fake_store = MagicMock()
    fake_store.describe_stats.return_value = {
        "total_vector_count": 841,
        "dimension": 1024,
    }
    with patch.object(vs_mod, "get_vector_store", return_value=fake_store):
        yield mock


@pytest.fixture
def mock_embedding():
    """Mock embedding model，避免加载 3GB+ 的真实 SentenceTransformer。

    patch 两个点（因为 `from X import Y` 会复制引用）：
    - backend.dependencies.get_embedding_model  (AgentService 等用)
    - backend.services.rag_service.get_embedding_model  (RAGService 用)
    """
    from backend import dependencies as deps_mod
    from backend.services import rag_service as rag_mod

    fake = MagicMock()
    # encode() 返回 mock numpy 数组，.tolist() 返回 1024 维 0 向量
    # 真实 sentence-transformers.encode() 返回的是 numpy.ndarray，所以 .tolist() 是方法
    fake_array = MagicMock()
    fake_array.tolist.return_value = [0.0] * 1024
    fake.encode.return_value = fake_array

    patchers = [
        patch.object(deps_mod, "get_embedding_model", return_value=fake),
        patch.object(rag_mod, "get_embedding_model", return_value=fake),
    ]
    for p in patchers:
        p.start()
    try:
        yield fake
    finally:
        for p in patchers:
            p.stop()


# ==================== HTTP Client ====================

@pytest_asyncio.fixture
async def async_client(temp_db, mock_minimax, mock_pinecone, mock_embedding) -> AsyncGenerator[AsyncClient, None]:
    """
    完整配置好的 httpx 异步客户端。
    - 用 ASGITransport，无需起真服务器
    - 临时 DB + M3/Pinecone/Embedding mock（绕过 startup_services）
    """
    # 关键：不通过 main.py 的 lifespan（那会冻结 DATABASE_URL 到首次启动）。
    # 我们直接建表 + 重新构造 app，绕过 lifespan。
    from backend.models import db_models
    from backend.config import get_settings
    from backend.routers import auth, chat, health, history, progress, quiz, vocabulary
    from backend.errors import APIError, api_error_handler, generic_error_handler
    from backend.middleware.request_id import RequestIDMiddleware
    from backend.middleware.security_headers import SecurityHeadersMiddleware
    from backend.middleware.rate_limit import RateLimitMiddleware
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(title="EnglishMaster Agent API (test)", version="0.0.test")
    settings = get_settings()
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://test"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)
    app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
    app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
    app.include_router(history.router, prefix="/api/history", tags=["History"])
    app.include_router(quiz.router, prefix="/api/quiz", tags=["Quiz"])
    app.include_router(progress.router, prefix="/api/progress", tags=["Progress"])
    app.include_router(vocabulary.router, prefix="/api/vocab", tags=["Vocabulary"])
    app.include_router(health.router, prefix="/api/health", tags=["Health"])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ==================== 认证 ====================

def _register_user_sync(client, username: str, password: str, display_name: str) -> dict:
    """同步版本（避开 async fixture 缓存问题）。"""
    import asyncio as _asyncio
    coro = client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "display_name": display_name},
    )
    loop = _asyncio.new_event_loop()
    try:
        resp = loop.run_until_complete(coro)
    finally:
        loop.close()
    return resp


@pytest.fixture
def alice_user(async_client):
    """注册并返回 alice 用户 + token（用 .result() 拿 async_client 的结果）。"""
    # 借助 client.post 返回的 coroutine，直接在同步上下文 await
    import asyncio
    resp = asyncio.get_event_loop().run_until_complete(
        async_client.post(
            "/api/auth/register",
            json={"username": "alice", "password": "pw1234", "display_name": "Alice"},
        )
    )
    data = resp.json()
    if "user" not in data:
        raise RuntimeError(f"alice_user fixture failed: {data}")
    return {
        "id": data["user"]["id"],
        "username": data["user"]["username"],
        "display_name": data["user"]["display_name"],
        "token": data["token"],
    }


@pytest.fixture
def bob_user(async_client):
    import asyncio
    resp = asyncio.get_event_loop().run_until_complete(
        async_client.post(
            "/api/auth/register",
            json={"username": "bob", "password": "pw5678", "display_name": "Bob"},
        )
    )
    data = resp.json()
    return {
        "id": data["user"]["id"],
        "username": data["user"]["username"],
        "token": data["token"],
    }


@pytest.fixture
def stan_user(async_client):
    import asyncio
    resp = asyncio.get_event_loop().run_until_complete(
        async_client.post(
            "/api/auth/register",
            json={"username": "stan", "password": "xsj123", "display_name": "Stan"},
        )
    )
    data = resp.json()
    return {
        "id": data["user"]["id"],
        "username": data["user"]["username"],
        "token": data["token"],
    }


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
