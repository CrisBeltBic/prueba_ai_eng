from datetime import datetime

from pydantic import BaseModel


class MessageIn(BaseModel):
    chat_id: str | None = None  # if not provided, backend generates a new one
    role: str                   # 'user' | 'assistant'
    content: str
    sources: list[str] = []
    user_id: str | None = None


class MessageOut(BaseModel):
    chat_id: str
    role: str
    content: str
    sources: list[str]
    timestamp: datetime


class ChatSummary(BaseModel):
    chat_id: str
    started_at: datetime
    message_count: int
