from typing import Optional
from pydantic import BaseModel


class Message(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = []
    mode: str = "general"
    filter_unit: Optional[str] = None
    filter_semester: Optional[int] = None
    session_id: Optional[int] = None
