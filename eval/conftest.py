"""
eval/conftest.py — 真实集成测试 fixture

和 tests/conftest.py 的核心区别：
- 不用任何 Mock
- 直接连真实服务器（需先启动 uvicorn）
- 真实 Pinecone + 真实 LLM（会消耗 token）
- 只在上线前手动跑

使用前提：
    uvicorn backend.main:app --reload

代理说明：
    .env 里设了 HTTPS_PROXY=127.0.0.1:1082，给后端访问 Pinecone / LLM 用。
    但 eval 测试连本地 8000 必须直连，否则代理对 127.0.0.1 处理 5 秒后断开
    （httpx 自动读环境变量，连本地也被代理劫持）。

    解决：eval 自己的 httpx 客户端显式 trust_env=False。
    不影响后端进程：uvicorn 启动时已读到代理，照常走代理查 Pinecone。

    端口：BACKEND_URL 环境变量控制，默认 localhost:8000。
         BACKEND_URL=http://localhost:8001 pytest eval/
"""
import os
import pytest
import httpx

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
EVAL_USER = {
    "username": "eval_user_001",
    "password": "evaltest123",
    "display_name": "评测账号"
}


def pytest_configure(config):
    config.addinivalue_line("markers", "real: 需要真实服务器，上线前跑")


@pytest.fixture(scope="session", autouse=True)
def require_server():
    """所有 eval 测试开始前，先确认服务器已启动（直连不走代理）"""
    try:
        r = httpx.get(f"{BASE_URL}/api/health", timeout=10, trust_env=False)
        if r.status_code != 200:
            pytest.exit("❌ 服务器未就绪，请先运行：uvicorn backend.main:app --reload")
    except Exception:
        pytest.exit("❌ 无法连接服务器，请先运行：uvicorn backend.main:app --reload")


@pytest.fixture(scope="session")
def client():
    """整个 session 共用一个 httpx 客户端（直连本地，不走代理）"""
    with httpx.Client(base_url=BASE_URL, timeout=30, trust_env=False) as c:
        yield c


@pytest.fixture(scope="session")
def token(client):
    """注册或登录，拿真实 token，整个 session 只做一次"""
    r = client.post("/api/auth/register", json=EVAL_USER)
    if r.status_code in [400, 409]:
        r = client.post("/api/auth/login", json={
            "username": EVAL_USER["username"],
            "password": EVAL_USER["password"],
        })
    assert r.status_code == 200, f"获取 token 失败：{r.text}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def auth(token):
    """认证 header，直接传给 headers 参数"""
    return {"Authorization": f"Bearer {token}"}