from contextlib import asynccontextmanager

from fastapi import FastAPI

from chat.api import router as chat_router
from db import close_pool, init_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()   # open db postgresql connection pool at startup
    yield
    await close_pool()  # close gracefully on shutdown


app = FastAPI(title="Chat Service", lifespan=lifespan)

app.include_router(chat_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
