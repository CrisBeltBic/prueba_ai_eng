from fastapi import APIRouter, BackgroundTasks

from schemas.store import IngestResponse, JobStatus, SearchRequest, SearchResult
from store import logic

router = APIRouter()


@router.post("/ingest/start", response_model=IngestResponse)
def start_ingest(background_tasks: BackgroundTasks):
    job_id = logic.create_job()
    background_tasks.add_task(logic.run_ingest, job_id)
    return {"job_id": job_id}


@router.get("/ingest/status/{job_id}", response_model=JobStatus)
def ingest_status(job_id: str):
    return logic.get_job_status(job_id)


@router.post("/search", response_model=list[SearchResult])
def search(body: SearchRequest):
    return logic.search(body.query, body.top_k, body.category)


@router.get("/article")
def get_by_url(url: str):
    return {"chunks": logic.get_by_url(url)}


@router.get("/categories")
def list_categories():
    return {"categories": logic.list_categories()}


@router.get("/stats")
def get_stats():
    return logic.get_stats()
