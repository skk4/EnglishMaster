"""
统一错误响应格式 + 错误码体系

所有 API 错误都返回以下结构：
{
    "error": {
        "code": "QUIZ_001",
        "message": "AI 出题失败，请稍后重试",
        "details": {...},          // 可选，调试用
        "request_id": "abc-123"    // 关联 X-Request-ID
    }
}

错误码分段：
- AUTH_xxx  认证授权
- QUIZ_xxx  出题/批改
- CHAT_xxx  聊天
- DATA_xxx  数据（教材、词汇）
- SYSTEM_xxx  系统级（5xx）
"""
from typing import Any, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


# 错误码常量
class ErrorCode:
    # AUTH
    AUTH_MISSING_TOKEN = "AUTH_001"
    AUTH_INVALID_TOKEN = "AUTH_002"
    AUTH_EXPIRED_TOKEN = "AUTH_003"
    AUTH_INVALID_CREDENTIALS = "AUTH_004"
    AUTH_USERNAME_TAKEN = "AUTH_005"
    AUTH_WEAK_CREDENTIALS = "AUTH_006"
    AUTH_FORBIDDEN = "AUTH_007"

    # QUIZ
    QUIZ_INVALID_INPUT = "QUIZ_001"
    QUIZ_GENERATION_FAILED = "QUIZ_002"
    QUIZ_GRADING_FAILED = "QUIZ_003"
    QUIZ_PARSING_FAILED = "QUIZ_004"

    # CHAT
    CHAT_INVALID_INPUT = "CHAT_001"
    CHAT_SESSION_NOT_FOUND = "CHAT_002"
    CHAT_UPSTREAM_FAILED = "CHAT_003"
    CHAT_STREAM_FAILED = "CHAT_004"

    # DATA
    DATA_VOCAB_NOT_FOUND = "DATA_001"
    DATA_SESSION_NOT_FOUND = "DATA_002"

    # SYSTEM
    SYSTEM_INTERNAL_ERROR = "SYSTEM_001"
    SYSTEM_UPSTREAM_TIMEOUT = "SYSTEM_002"
    SYSTEM_RATE_LIMITED = "SYSTEM_003"


class APIError(HTTPException):
    """统一 API 错误基类。"""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[dict] = None,
    ):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(status_code=status_code, detail=message)


# 常用快捷类
class AuthError(APIError):
    def __init__(self, code: str = ErrorCode.AUTH_INVALID_TOKEN, message: str = "认证失败"):
        super().__init__(code, message, status.HTTP_401_UNAUTHORIZED)


class NotFoundError(APIError):
    def __init__(self, message: str = "资源不存在", code: str = ErrorCode.DATA_SESSION_NOT_FOUND):
        super().__init__(code, message, status.HTTP_404_NOT_FOUND)


class ValidationError(APIError):
    def __init__(self, message: str = "请求参数无效", code: str = ErrorCode.QUIZ_INVALID_INPUT):
        super().__init__(code, message, status.HTTP_400_BAD_REQUEST)


class ServerError(APIError):
    def __init__(self, message: str = "服务器内部错误", code: str = ErrorCode.SYSTEM_INTERNAL_ERROR):
        super().__init__(code, message, status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpstreamError(APIError):
    def __init__(self, message: str = "上游服务异常", code: str = ErrorCode.CHAT_UPSTREAM_FAILED):
        super().__init__(code, message, status.HTTP_502_BAD_GATEWAY)


# 统一异常处理器
async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """把 APIError 转成标准 JSON 响应。"""
    request_id = getattr(request.state, "request_id", None)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": request_id,
            }
        },
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """捕获所有未处理的 HTTPException，转标准格式。"""
    from fastapi import HTTPException
    request_id = getattr(request.state, "request_id", None)

    # 映射常见状态码到错误码
    code_map = {
        400: ErrorCode.QUIZ_INVALID_INPUT,
        401: ErrorCode.AUTH_INVALID_TOKEN,
        403: ErrorCode.AUTH_FORBIDDEN,
        404: ErrorCode.DATA_SESSION_NOT_FOUND,
        422: ErrorCode.QUIZ_INVALID_INPUT,
        500: ErrorCode.SYSTEM_INTERNAL_ERROR,
        502: ErrorCode.CHAT_UPSTREAM_FAILED,
        503: ErrorCode.SYSTEM_UPSTREAM_TIMEOUT,
    }

    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        message = str(exc.detail)
    else:
        status_code = 500
        message = "Internal Server Error"

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code_map.get(status_code, ErrorCode.SYSTEM_INTERNAL_ERROR),
                "message": message,
                "details": None,
                "request_id": request_id,
            }
        },
    )
