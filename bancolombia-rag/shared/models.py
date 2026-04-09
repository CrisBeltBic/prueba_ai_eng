from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """A piece of text extracted and processed from a Bancolombia web page."""

    chunk_id: str
    url: str
    title: str
    category: str
    text: str
    chunk_index: int
    total_chunks: int
    scraped_at: datetime


class SearchResult(BaseModel):
    """A chunk returned by the knowledge service with its relevance score."""

    chunk_id: str
    url: str
    title: str
    category: str
    text: str
    score: float


class Source(BaseModel):
    """A source URL cited in an agent response."""

    url: str
    title: str


class Message(BaseModel):
    """A single message in a conversation."""

    role: Literal["user", "assistant"]
    content: str
    sources: list[Source] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Session(BaseModel):
    """A conversation session."""

    session_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0


class ChatRequest(BaseModel):
    """Request body for the agent /chat endpoint."""

    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    """Response from the agent /chat endpoint."""

    session_id: str
    answer: str
    sources: list[Source] = Field(default_factory=list)