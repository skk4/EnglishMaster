"""
安全响应头中间件

添加 OWASP 推荐的安全响应头，防御 XSS / clickjacking / MIME 嗅探 / 协议降级等攻击。
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # 防 XSS
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 防 clickjacking（已 DENY 是 fallback，更严格用 CSP frame-ancestors）
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "frame-ancestors 'none'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.minimax.io https://xsjkndb01-*.pinecone.io"
        )

        # 强制 HTTPS
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Referrer 策略
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response
