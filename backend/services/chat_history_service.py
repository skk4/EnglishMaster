"""Chat history service — persist chat sessions and messages to SQLite."""
import json
import re
from datetime import datetime, timezone
from typing import Optional


def strip_think_blocks(content: str) -> str:
    """
    去除 M3 输出中的 <think>...</think> 推理块。
    处理多种情况：
    1. 完整 <think>...</think>（多个）
    2. 只有开始标签<think>（推理截断）— 整段丢弃
    3. 没有开始但有 </think>（异常情况）— 丢弃 </think> 之后的内容
    """
    if not content or "<think>" not in content and "</think>" not in content:
        return content

    # 反复剥完整块
    while True:
        m = re.search(r"<think>.*?</think>", content, re.DOTALL)
        if not m:
            break
        content = content[:m.start()] + content[m.end():]
    content = content.strip()

    # 残留<think>（推理截断）— 丢弃到结尾
    if "<think>" in content:
        idx = content.find("<think>")
        content = content[:idx].strip()

    # 残留</think>（异常）— 丢弃
    if "</think>" in content:
        idx = content.find("</think>")
        content = content[idx + len("</think>"):].strip()

    return content

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.db_models import AsyncSessionLocal, ChatMessage, ChatSession


async def create_session(user_id: int, title: str = "新对话") -> int:
    async with AsyncSessionLocal() as session:
        s = ChatSession(user_id=user_id, title=title)
        session.add(s)
        await session.commit()
        await session.refresh(s)
        return s.id


async def save_message(
    session_id: int,
    role: str,
    content: str,
    sources: Optional[list[dict]] = None,
    mode: str = "",
) -> int:
    # Strip <think> reasoning block (MiniMax M3) — 用共用函数
    if role == "assistant":
        content = strip_think_blocks(content)

    async with AsyncSessionLocal() as session:
        msg = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            sources_json=json.dumps(sources or [], ensure_ascii=False),
            mode=mode,
        )
        session.add(msg)

        # Bump session updated_at
        result = await session.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        chat_session = result.scalar_one_or_none()
        if chat_session:
            chat_session.updated_at = datetime.now(timezone.utc)
            # Auto-generate title from first user message
            if chat_session.title == "新对话" and role == "user":
                chat_session.title = content[:30] + ("..." if len(content) > 30 else "")

        await session.commit()
        await session.refresh(msg)
        return msg.id


async def list_sessions(user_id: int, limit: int = 50) -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(desc(ChatSession.updated_at))
            .limit(limit)
        )
        sessions = result.scalars().all()
        return [
            {
                "id":         s.id,
                "title":      s.title,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in sessions
        ]


async def get_session_with_messages(session_id: int, user_id: int) -> Optional[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        chat_session = result.scalar_one_or_none()
        if not chat_session or chat_session.user_id != user_id:
            return None

        result = await session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id)
        )
        messages = result.scalars().all()

        return {
            "id":         chat_session.id,
            "title":      chat_session.title,
            "created_at": chat_session.created_at.isoformat(),
            "updated_at": chat_session.updated_at.isoformat(),
            "messages":   [
                {
                    "id":         m.id,
                    "role":       m.role,
                    "content":    m.content,
                    "sources":    json.loads(m.sources_json) if m.sources_json else [],
                    "mode":       m.mode or "",
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ],
        }


async def delete_session(session_id: int, user_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        chat_session = result.scalar_one_or_none()
        if not chat_session or chat_session.user_id != user_id:
            return False
        await session.delete(chat_session)
        await session.commit()
        return True
