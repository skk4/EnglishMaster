from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.routers.auth import get_current_user
from backend.services.progress_service import (
    get_progress_summary,
    get_recent_records,
    update_vocab_progress,
)

router = APIRouter()


@router.get("/summary")
async def progress_summary(user: dict = Depends(get_current_user)):
    return await get_progress_summary(user["id"])


@router.get("/records")
async def recent_records(
    limit: int = 20,
    user: dict = Depends(get_current_user),
):
    return await get_recent_records(user["id"], limit)


class VocabUpdateRequest(BaseModel):
    word: str
    unit: str
    semester: int
    mastered: bool


@router.post("/vocab")
async def vocab_update(
    req: VocabUpdateRequest,
    user: dict = Depends(get_current_user),
):
    await update_vocab_progress(user["id"], req.word, req.unit, req.semester, req.mastered)
    return {"ok": True}
