"""Agent service entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from agent.api import router
from agent.logic import AgentLogic
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    logic = AgentLogic(chat_service_url=settings.chat_service_url)
    await logic.start()
    app.state.logic = logic
    yield
    await logic.stop()
    app.state.logic = None


app = FastAPI(title="Agent Service", lifespan=lifespan)
app.include_router(router)
