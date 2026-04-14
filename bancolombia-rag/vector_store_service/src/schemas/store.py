from pydantic import BaseModel


class IngestResponse(BaseModel):
    job_id: str


class JobStatus(BaseModel):
    job_id: str
    phase: str
    pages_read: int = 0
    chunks_indexed: int = 0
    errors: int = 0
    finished_at: str | None = None
    detail: str | None = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    category: str | None = None


class SearchResult(BaseModel):
    chunk_id: str
    context: str    # chunk anterior + match + chunk siguiente
    url: str
    title: str
    category: str
    score: float
