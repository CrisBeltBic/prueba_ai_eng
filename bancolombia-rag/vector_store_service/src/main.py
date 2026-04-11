from contextlib import asynccontextmanager

from fastapi import FastAPI

from helpers.embedder import get_model
from store.api import router as store_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_model()  # load embedding model at startup, not on first request
    yield


app = FastAPI(title="Vector Store Service", lifespan=lifespan)

app.include_router(store_router)


@app.get("/health")
def health():
    return {"status": "ok"}


#docker build -t vector_store_service .
#docker run --env-file .env -p 8084:8084 vector_store_service
