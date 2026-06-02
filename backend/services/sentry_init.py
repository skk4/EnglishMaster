"""
Sentry 后端初始化
用法：在 main.py 的 lifespan 启动时调用 init_sentry()
"""
import os
import logging
from typing import Any

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """初始化 Sentry 错误追踪。在生产环境启用。"""
    dsn = os.getenv("SENTRY_DSN")
    env = os.getenv("APP_ENV", "development")

    if not dsn or env != "production":
        if env != "production":
            logger.info("[sentry] Skipping Sentry init (non-production env)")
        else:
            logger.warning("[sentry] SENTRY_DSN not set, skipping")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=env,
            release=os.getenv("RELEASE_VERSION", "dev"),
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            integrations=[
                FastApiIntegration(),
                StarletteIntegration(),
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR,
                ),
            ],
            # 不收集用户密码 / token 等
            before_send=scrub_sensitive_data,
        )
        logger.info("[sentry] Initialized for env=%s", env)
    except ImportError:
        logger.warning("[sentry] sentry-sdk not installed, skipping")


def scrub_sensitive_data(event: Any, hint: Any) -> Any:
    """事件发送前脱敏。"""
    # 移除 Authorization header
    if "request" in event and "headers" in event.get("request", {}):
        headers = event["request"]["headers"]
        for key in list(headers.keys()):
            if key.lower() in ("authorization", "cookie", "x-api-key"):
                headers[key] = "[REDACTED]"

    # 移除 user.email / user.ip_address
    if "user" in event:
        user = event["user"]
        for key in ("email", "ip_address", "username"):
            if key in user:
                del user[key]

    # 移除 extra 里的敏感字段
    if "extra" in event:
        for key in list(event["extra"].keys()):
            if any(s in key.lower() for s in ("password", "token", "secret", "key")):
                event["extra"][key] = "[REDACTED]"

    return event


def capture_exception(error: Exception, **context) -> None:
    """手动捕获异常（用于 try/except 块）。"""
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for k, v in context.items():
                scope.set_extra(k, v)
            sentry_sdk.capture_exception(error)
    except ImportError:
        logger.exception("[sentry-not-installed] %s", error)
