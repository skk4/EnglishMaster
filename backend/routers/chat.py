import json
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.models.request_models import ChatRequest
from backend.routers.auth import get_current_user
from backend.services.agent_service import AgentService
from backend.services.chat_history_service import (
    create_session,
    get_session_with_messages,
    save_message,
)

router = APIRouter()


def _history_to_dicts(request: ChatRequest) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in request.history]


class ChatStreamRequest(ChatRequest):
    session_id: Optional[int] = None  # None = create new session


async def _resolve_session(user_id: int, session_id: Optional[int]) -> int:
    if session_id:
        # Verify ownership
        data = await get_session_with_messages(session_id, user_id)
        if not data:
            raise ValueError(f"Session {session_id} not found")
        return session_id
    return await create_session(user_id)


@router.post("/sync")
async def chat_sync(request: ChatRequest, user: dict = Depends(get_current_user)):
    """Synchronous chat — returns complete response + saves to history."""
    session_id = await _resolve_session(user["id"], request.session_id)

    agent = AgentService()
    result = agent.chat_sync(
        user_message=request.message,
        conversation_history=_history_to_dicts(request),
        mode=request.mode,
        filter_unit=request.filter_unit,
        filter_semester=request.filter_semester,
    )

    # Persist both messages
    await save_message(session_id, "user", request.message, mode=request.mode)
    await save_message(session_id, "assistant", result["content"], result["sources"], mode=request.mode)

    result["session_id"] = session_id
    return result


@router.post("/stream")
async def chat_stream(request: ChatStreamRequest, user: dict = Depends(get_current_user)):
    """Streaming chat — saves to history, returns SSE."""
    session_id = await _resolve_session(user["id"], request.session_id)

    agent = AgentService()
    text_gen, sources = agent.chat_stream(
        user_message=request.message,
        conversation_history=_history_to_dicts(request),
        mode=request.mode,
        filter_unit=request.filter_unit,
        filter_semester=request.filter_semester,
    )

    full_content_parts: list[str] = []
    last_user_msg = request.message

    async def generate() -> AsyncIterator[str]:
        for text in text_gen:
            full_content_parts.append(text)
            data = json.dumps({"type": "text", "content": text}, ensure_ascii=False)
            yield f"data: {data}\n\n"

        full_content = "".join(full_content_parts)
        # Persist both messages
        await save_message(session_id, "user", last_user_msg, mode=request.mode)
        await save_message(session_id, "assistant", full_content, sources, mode=request.mode)

        done = json.dumps(
            {"type": "done", "sources": sources, "session_id": session_id},
            ensure_ascii=False,
        )
        yield f"data: {done}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
