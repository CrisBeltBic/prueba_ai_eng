from fastapi import APIRouter, Depends, HTTPException, Request

from agent.logic import AgentLogic
from config import settings
from helpers.auth import verify_api_key
from schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


# Dependencies
def get_logic(request: Request) -> AgentLogic:
    """Retrieve the shared AgentLogic instance stored in app.state."""
    logic: AgentLogic | None = request.app.state.logic
    if logic is None:
        raise HTTPException(status_code=503, detail="Agent not ready")
    return logic


# Endpoints
@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
async def chat(req: ChatRequest, logic: AgentLogic = Depends(get_logic)) -> ChatResponse:
    result = await logic.chat(message=req.message, chat_id=req.chat_id)
    return ChatResponse(**result)


@router.get("/health")
async def health(logic: AgentLogic = Depends(get_logic)) -> dict:
    mcp_connected = logic._mcp._session is not None
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "mcp_connected": mcp_connected,
    }
