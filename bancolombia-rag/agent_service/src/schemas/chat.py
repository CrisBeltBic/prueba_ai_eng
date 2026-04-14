"""Request and response schemas for the agent API."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    chat_id: str | None = None


class ChatResponse(BaseModel):
    chat_id: str
    reply: str
    sources: list[str]
