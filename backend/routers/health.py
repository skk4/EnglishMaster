"""
健康检查端点

3 个端点：
- GET /api/health        综合健康（带依赖检查）
- GET /api/health/live   进程存活（liveness probe）
- GET /api/health/ready  就绪（readiness probe，含依赖）
"""
import asyncio
import logging
import time
from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()

_health_cache: dict[str, Any] = {"last_check": 0, "data": None}
_CACHE_TTL_SECONDS = 30  # 缓存 30s，避免每次请求都查依赖


async def _check_dependencies() -> dict[str, Any]:
    """检查所有依赖健康。"""
    from backend.config import get_settings
    s = get_settings()
    provider_key = s.llm_provider  # "minimax" | "openai"

    deps = {
        "pinecone": {"status": "unknown", "latency_ms": 0, "error": None},
        provider_key: {"status": "unknown", "latency_ms": 0, "error": None},
        "sqlite": {"status": "unknown", "error": None},
    }

    # 1. Pinecone
    try:
        from backend.dependencies import get_pinecone_index
        idx = get_pinecone_index()
        if idx is None:
            deps["pinecone"]["status"] = "down"
            deps["pinecone"]["error"] = "Pinecone not initialized"
        else:
            t0 = time.time()
            stats = await asyncio.to_thread(idx.describe_index_stats)
            deps["pinecone"]["latency_ms"] = int((time.time() - t0) * 1000)
            deps["pinecone"]["status"] = "up" if stats.total_vector_count > 0 else "empty"
    except Exception as e:
        deps["pinecone"]["status"] = "down"
        deps["pinecone"]["error"] = str(e)[:200]

    # 2. LLM provider（动态 key: "minimax" | "openai"）
    try:
        from backend.dependencies import get_llm_client
        llm = get_llm_client()
        deps[provider_key]["status"] = "up" if llm is not None else "down"
    except Exception as e:
        deps[provider_key]["status"] = "down"
        deps[provider_key]["error"] = str(e)[:200]

    # 3. SQLite（用主进程连接测试）
    try:
        from backend.models.db_models import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        deps["sqlite"]["status"] = "up"
    except Exception as e:
        deps["sqlite"]["status"] = "down"
        deps["sqlite"]["error"] = str(e)[:200]

    return deps


def _overall_status(deps: dict[str, Any]) -> str:
    """综合状态：所有依赖 up → ok；任一 down → degraded。"""
    statuses = [v.get("status") for v in deps.values()]
    if all(s == "up" for s in statuses):
        return "ok"
    if any(s == "down" for s in statuses):
        return "degraded"
    return "ok"  # "empty"/"unknown" 不算 down


@router.get("")
async def health_check(request: Request):
    """综合健康检查（带依赖）。"""
    now = time.time()
    if now - _health_cache["last_check"] < _CACHE_TTL_SECONDS and _health_cache["data"]:
        cached = _health_cache["data"]
    else:
        deps = await _check_dependencies()
        from backend.dependencies import get_llm_client
        from backend.config import get_settings as _gs
        llm = get_llm_client()
        cached = {
            "status": _overall_status(deps),
            "checks": deps,
            "provider": _gs().llm_provider,
            "model": llm.model if llm else "unknown",
        }
        _health_cache["data"] = cached
        _health_cache["last_check"] = now

    # 附加 request_id
    cached["request_id"] = getattr(request.state, "request_id", None)

    # degraded 状态返回 503，让 LB 摘掉
    status_code = 200 if cached["status"] == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=cached, status_code=status_code)


@router.get("/live")
async def liveness():
    """Liveness probe：进程是否存活。最简实现，不查任何依赖。"""
    return {"status": "alive"}


@router.get("/ready")
async def readiness(request: Request):
    """Readiness probe：进程是否准备好接受流量。"""
    deps = await _check_dependencies()
    is_ready = _overall_status(deps) == "ok"
    payload = {
        "ready": is_ready,
        "checks": deps,
        "request_id": getattr(request.state, "request_id", None),
    }
    return JSONResponse(
        content=payload,
        status_code=200 if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE,
    )
