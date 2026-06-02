"""
X-Request-ID 中间件

每个请求自动注入 request_id（如果客户端没传则生成 UUID），
存到 request.state.request_id，并加到响应头。
所有日志和 Sentry 事件都带这个 ID，方便跨服务追踪。
"""
import uuid
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # 优先用客户端传入的 ID（方便跨服务追踪）
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
