"""
/api/auth/* 接口测试

覆盖矩阵（TEST_PLAN §2.3）：
- AUTH-01..11 共 11 个场景
"""
import pytest
from httpx import AsyncClient

from conftest import auth_headers


@pytest.mark.asyncio
async def test_register_success(async_client: AsyncClient):
    """AUTH-01: 正常注册"""
    resp = await async_client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "pw1234", "display_name": "Alice"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "user" in data
    assert "token" in data
    assert data["user"]["username"] == "alice"
    assert data["user"]["display_name"] == "Alice"
    assert len(data["token"]) > 50  # JWT 不是空


@pytest.mark.asyncio
async def test_register_username_too_short(async_client: AsyncClient):
    """AUTH-02: 用户名 < 3 字符"""
    resp = await async_client.post(
        "/api/auth/register",
        json={"username": "ab", "password": "pw1234"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert "error" in body
    assert "用户名至少 3 位" in body["error"]["message"]
    assert body["error"]["code"] == "AUTH_006"


@pytest.mark.asyncio
async def test_register_password_too_short(async_client: AsyncClient):
    """AUTH-03: 密码 < 4 字符"""
    resp = await async_client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "ab"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert "密码至少 4 位" in body["error"]["message"]


@pytest.mark.asyncio
async def test_register_duplicate_username(async_client: AsyncClient, alice_user):
    """AUTH-04: 用户名已存在"""
    resp = await async_client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "different"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert "用户名已存在" in body["error"]["message"]
    assert body["error"]["code"] == "AUTH_006"


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, alice_user):
    """AUTH-05: 正常登录"""
    resp = await async_client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "pw1234"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "user" in data
    assert "token" in data
    assert data["user"]["username"] == "alice"
    assert "token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(async_client: AsyncClient, alice_user):
    """AUTH-06: 密码错误"""
    resp = await async_client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "wrong_password"},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert "error" in body
    assert "用户名或密码错误" in body["error"]["message"]
    assert body["error"]["code"] == "AUTH_004"


@pytest.mark.asyncio
async def test_login_user_not_exists(async_client: AsyncClient):
    """AUTH-07: 用户不存在（不暴露此信息）"""
    resp = await async_client.post(
        "/api/auth/login",
        json={"username": "nonexistent_user_xyz", "password": "any"},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert "用户名或密码错误" in body["error"]["message"]


@pytest.mark.asyncio
async def test_me_without_token(async_client: AsyncClient):
    """AUTH-08: 无 token"""
    resp = await async_client.get("/api/auth/me")
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "AUTH_001"


@pytest.mark.asyncio
async def test_me_fake_token(async_client: AsyncClient):
    """AUTH-09: 假 token"""
    resp = await async_client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer fake.jwt.token"},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "AUTH_002"


@pytest.mark.asyncio
async def test_me_expired_token(async_client: AsyncClient):
    """AUTH-10: token 过期"""
    import jwt
    from datetime import datetime, timedelta, timezone
    expired_payload = {
        "sub": "1",
        "username": "alice",
        "iat": datetime.now(timezone.utc) - timedelta(days=31),
        "exp": datetime.now(timezone.utc) - timedelta(days=1),
    }
    expired = jwt.encode(
        expired_payload,
        "test-secret-for-testing-only-32bytes",
        algorithm="HS256",
    )
    resp = await async_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired}"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_success(async_client: AsyncClient, alice_user):
    """AUTH-11: /me 正常"""
    resp = await async_client.get(
        "/api/auth/me",
        headers=auth_headers(alice_user["token"]),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "alice"
    assert data["id"] == alice_user["id"]


# ==================== 新增：错误响应格式 ====================


@pytest.mark.asyncio
async def test_error_response_format(async_client: AsyncClient):
    """所有错误响应必须有 error.code / error.message / error.request_id"""
    resp = await async_client.get("/api/auth/me")
    assert resp.status_code == 401
    body = resp.json()
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]
    assert "request_id" in body["error"]
    # 响应头也要有 X-Request-ID
    assert "x-request-id" in resp.headers


@pytest.mark.asyncio
async def test_security_headers_present(async_client: AsyncClient):
    """所有响应必须有安全头"""
    resp = await async_client.get("/api/health/live")
    assert "x-content-type-options" in resp.headers
    assert "x-frame-options" in resp.headers
    assert "content-security-policy" in resp.headers
