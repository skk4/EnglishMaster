from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.routers.auth import get_current_user
from backend.services.chat_history_service import (
    create_session,
    delete_session,
    get_session_with_messages,
    list_sessions,
)

router = APIRouter()


class CreateSessionRequest(BaseModel):
    title: str = "新对话"


@router.get("/sessions")
async def sessions_list(
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    return await list_sessions(user["id"], limit)


@router.post("/sessions")
async def sessions_create(
    request: CreateSessionRequest,
    user: dict = Depends(get_current_user),
):
    sid = await create_session(user["id"], request.title)
    return {"id": sid, "title": request.title}


@router.get("/sessions/{session_id}")
async def session_detail(
    session_id: int,
    user: dict = Depends(get_current_user),
):
    result = await get_session_with_messages(session_id, user["id"])
    if not result:
        raise HTTPException(status_code=404, detail="会话不存在")
    return result


@router.delete("/sessions/{session_id}")
async def session_delete(
    session_id: int,
    user: dict = Depends(get_current_user),
):
    ok = await delete_session(session_id, user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True}
