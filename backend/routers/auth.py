from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from backend import metrics
from backend.errors import AuthError, ErrorCode, NotFoundError, ValidationError
from backend.services.auth_service import (
    authenticate,
    create_token,
    decode_token,
    get_user_by_id,
    register_user,
)

router = APIRouter()


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


async def get_current_user(authorization: str = Header(None)) -> dict:
    """FastAPI dependency — extract user from Authorization: Bearer <token>."""
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthError(ErrorCode.AUTH_MISSING_TOKEN, "未登录")
    token = authorization[7:].strip()
    payload = decode_token(token)
    if not payload:
        raise AuthError(ErrorCode.AUTH_INVALID_TOKEN, "token 无效或已过期")
    user = {"id": int(payload["sub"]), "username": payload["username"]}
    metrics.set_current_user_id(str(user["id"]))
    return user


@router.post("/register")
async def register(request: RegisterRequest):
    try:
        user = await register_user(
            request.username, request.password, request.display_name
        )
    except ValueError as e:
        raise ValidationError(str(e), ErrorCode.AUTH_WEAK_CREDENTIALS)
    token = create_token(user["id"], user["username"])
    return {"user": user, "token": token}


@router.post("/login")
async def login(request: LoginRequest):
    user = await authenticate(request.username, request.password)
    if not user:
        raise AuthError(ErrorCode.AUTH_INVALID_CREDENTIALS, "用户名或密码错误")
    token = create_token(user["id"], user["username"])
    return {"user": user, "token": token}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    full = await get_user_by_id(user["id"])
    if not full:
        raise NotFoundError("用户不存在")
    return full
