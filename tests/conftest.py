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
    """Mock MiniMax 客户端（同步 fixture，避免 async generator 问题）。
    重要：agent_service/quiz_service 调用的是同步 OpenAI SDK，
    所以 chat.completions.create 必须是普通 MagicMock（不是 AsyncMock）。
    另：from X import Y 会复制引用，需 patch 每个消费模块。
    """
    mock = MagicMock()
    mock.chat.completions.create = MagicMock()
    modules_to_patch = [
        "backend.dependencies.get_chat_client",
        "backend.services.agent_service.get_chat_client",
        "backend.services.quiz_service.get_chat_client",
    ]
    patchers = [patch(m, return_value=mock) for m in modules_to_patch]
    for p in patchers:
        p.start()
    request.addfinalizer(lambda: [p.stop() for p in patchers])
    return mock


@pytest_asyncio.fixture
async def mock_pinecone() -> AsyncGenerator[MagicMock, None]:
    """Mock Pinecone index。"""
    mock = MagicMock()
    mock.describe_index_stats.return_value = MagicMock(
        total_vector_count=841, dimension=1024
    )
    # 模拟 query 返回空 matches
    mock.query.return_value = MagicMock(matches=[])
    with patch("backend.dependencies.get_pinecone_index", return_value=mock):
        yield mock


# ==================== HTTP Client ====================

@pytest_asyncio.fixture
async def async_client(temp_db, mock_minimax, mock_pinecone) -> AsyncGenerator[AsyncClient, None]:
    """
    完整配置好的 httpx 异步客户端。
    - 用 ASGITransport，无需起真服务器
    - 临时 DB + M3/Pinecone mock
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
