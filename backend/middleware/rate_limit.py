"""
简单内存版限流中间件

防御策略：
- 登录：5 分钟内同 IP ≤ 10 次
- AI 类（chat/quiz/vocab）：1 分钟内同 IP ≤ 30 次（够学生正常使用）
- 公开（register/me）：1 分钟内同 IP ≤ 60 次

生产环境建议用 Redis 替代内存（多实例可共享）。
"""
import time
import logging
from collections import defaultdict
from typing import DefaultDict

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.errors import ErrorCode

logger = logging.getLogger(__name__)


class _Window:
    """Sliding window counter (key: (client_id, route), value: timestamps)."""

    def __init__(self):
        self.events: DefaultDict[tuple, list[float]] = defaultdict(list)

    def is_allowed(self, key: tuple, max_requests: int, window_seconds: int) -> bool:
        now = time.time()
        # 清理过期
        self.events[key] = [t for t in self.events[key] if t > now - window_seconds]
        if len(self.events[key]) >= max_requests:
            return False
        self.events[key].append(now)
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    """内存限流中间件（开发期使用）。生产环境改用 Redis。"""

    def __init__(self, app):
        super().__init__(app)
        self.window = _Window()
        # 路径规则：(prefix, max_per_window, window_seconds)
        self.rules = [
            ("/api/auth/login", 10, 5 * 60),       # 10 / 5min
            ("/api/auth/register", 5, 60 * 60),   # 5 / hour
            ("/api/chat", 30, 60),                 # 30 / min
            ("/api/quiz/generate", 10, 60),       # 10 / min
            ("/api/quiz/grade", 60, 60),          # 60 / min
            ("/api/vocab", 60, 60),                # 60 / min
        ]

    def _get_client_id(self, request: Request) -> str:
        """客户端标识：优先 X-Forwarded-For，最后用 client.host。"""
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    async def dispatch(self, request, call_next):
        # 测试环境禁用限流（不污染测试结果）
        import os
        if os.getenv("APP_ENV") == "test":
            return await call_next(request)

        path = request.url.path
        for prefix, max_req, window_sec in self.rules:
            if path.startswith(prefix):
                client = self._get_client_id(request)
                key = (client, prefix)
                if not self.window.is_allowed(key, max_req, window_sec):
                    logger.warning(f"[ratelimit] {client} exceeded {max_req}/{window_sec}s on {prefix}")
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": {
                                "code": ErrorCode.SYSTEM_RATE_LIMITED,
                                "message": f"Too many requests. Max {max_req} per {window_sec}s.",
                                "details": {"limit": max_req, "window_seconds": window_sec},
                                "request_id": getattr(request.state, "request_id", None),
                            }
                        },
                        headers={"Retry-After": str(window_sec)},
                    )
                break
        return await call_next(request)
