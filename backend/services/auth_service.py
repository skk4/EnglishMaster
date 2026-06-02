"""Auth service — password hashing + JWT token issuing."""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.config import get_settings
from backend.models.db_models import AsyncSessionLocal, User

settings = get_settings()
JWT_SECRET = os.getenv("JWT_SECRET", settings.app_secret_key)
JWT_ALGO = "HS256"
TOKEN_EXPIRE_DAYS = 30


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    expected = hashlib.sha256((salt + password).encode()).hexdigest()
    return hmac.compare_digest(digest, expected)


def create_token(user_id: int, username: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError:
        return None


async def register_user(username: str, password: str, display_name: str = "") -> dict:
    if len(username) < 3 or len(password) < 4:
        raise ValueError("用户名至少 3 位，密码至少 4 位")
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(User).where(User.username == username))
        if existing.scalar_one_or_none():
            raise ValueError("用户名已存在")
        user = User(
            username=username,
            password_hash=hash_password(password),
            display_name=display_name or username,
        )
        session.add(user)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise ValueError("用户名已存在")
        await session.refresh(user)
        return {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
        }


async def authenticate(username: str, password: str) -> Optional[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):
            return None
        return {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
        }


async def get_user_by_id(user_id: int) -> Optional[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        return {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
        }
