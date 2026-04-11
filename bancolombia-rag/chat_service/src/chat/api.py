from fastapi import APIRouter

from chat import logic
from schemas.chat import ChatSummary, MessageIn, MessageOut

router = APIRouter()


@router.get("/chats", response_model=list[ChatSummary])
async def list_chats():
    return await logic.list_chats()


@router.post("/chats/messages", response_model=MessageOut, status_code=201)
async def add_message(body: MessageIn):
    return await logic.add_message(body.chat_id, body.role, body.content, body.sources, body.user_id)


@router.get("/chats/{chat_id}/messages", response_model=list[MessageOut])
async def get_messages(chat_id: str, limit: int | None = None):
    return await logic.get_messages(chat_id, limit)
