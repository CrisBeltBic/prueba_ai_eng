from pydantic import BaseModel


class ScrapeRequest(BaseModel):
    max_pages: int = 200
    delay: float = 1.0


class JobStatus(BaseModel):
    job_id: str
    phase: str
    urls_found: int = 0
    pages_scraped: int = 0
    errors: int = 0
    finished_at: str | None = None
