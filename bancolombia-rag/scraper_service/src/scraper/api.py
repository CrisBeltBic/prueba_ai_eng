from fastapi import APIRouter, BackgroundTasks

from schemas.scraper import JobStatus, ScrapeRequest
from scraper import logic

router = APIRouter()


@router.post("/start")
async def start_scraping(body: ScrapeRequest, background_tasks: BackgroundTasks):
    job_id = logic.create_job()
    background_tasks.add_task(logic.run_scraper, job_id, body.max_pages, body.delay)
    return {"job_id": job_id}


@router.get("/status/{job_id}", response_model=JobStatus)
async def get_status(job_id: str):
    return logic.get_job_status(job_id)


@router.get("/jobs")
async def list_jobs():
    return logic.list_jobs()
