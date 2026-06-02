"""
/api/health 测试

OPS_PLAN §4.3 健康检查要求。
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(async_client: AsyncClient):
    resp = await async_client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "model" in data
