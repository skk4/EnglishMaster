from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.dependencies import shutdown_services, startup_services
from backend.errors import APIError, api_error_handler, generic_error_handler
from backend.middleware.request_id import RequestIDMiddleware
from backend.middleware.security_headers import SecurityHeadersMiddleware
from backend.middleware.rate_limit import RateLimitMiddleware
from backend.models.db_models import init_db
from backend.routers import auth, chat, health, history, progress, quiz, vocabulary

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_services()
    await init_db()
    yield
    await shutdown_services()


app = FastAPI(
    title="EnglishMaster Agent API",
    version="1.0.0",
    description="八年级英语 AI 学习助手后端接口",
    lifespan=lifespan,
)

# 中间件：执行顺序从下到上（最下面最先执行）
# 1. Request ID 注入（最先，所有请求都带 ID）
app.add_middleware(RequestIDMiddleware)
# 2. 限流
app.add_middleware(RateLimitMiddleware)
# 3. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 4. 安全响应头（最后添加，包裹所有响应）
app.add_middleware(SecurityHeadersMiddleware)

# 统一错误处理
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(Exception, generic_error_handler)

# 路由
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(history.router, prefix="/api/history", tags=["History"])
app.include_router(quiz.router, prefix="/api/quiz", tags=["Quiz"])
app.include_router(progress.router, prefix="/api/progress", tags=["Progress"])
app.include_router(vocabulary.router, prefix="/api/vocab", tags=["Vocabulary"])
app.include_router(health.router, prefix="/api/health", tags=["Health"])

