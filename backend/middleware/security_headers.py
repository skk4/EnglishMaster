"""
安全响应头中间件

添加 OWASP 推荐的安全响应头，防御 XSS / clickjacking / MIME 嗅探 / 协议降级等攻击。
"""
from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.config import get_settings


def _build_csp() -> str:
    """Build CSP header dynamically based on configured LLM provider base_url."""
    s = get_settings()
    provider_url = s.openai_base_url if s.llm_provider == "openai" else s.minimax_base_url
    # Extract origin (scheme + host) from the provider URL for CSP
    parsed = urlparse(provider_url)
    provider_origin = f"{parsed.scheme}://{parsed.hostname}"

    return (
        "default-src 'self'; "
        "frame-ancestors 'none'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        f"connect-src 'self' {provider_origin} https://xsjkndb01-*.pinecone.io"
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # 防 XSS
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 动态 CSP（connect-src 根据 provider 变化）
        response.headers["Content-Security-Policy"] = _build_csp()

        # 强制 HTTPS
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Referrer 策略
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response
