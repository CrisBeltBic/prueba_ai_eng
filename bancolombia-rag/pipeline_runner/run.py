"""
Pipeline runner — runs once at startup to populate the knowledge base.

Steps:
  1. POST /scraper/start     → crawl bancolombia.com/personas → pages.jsonl
  2. Poll until scraping done
  3. POST /ingest/start      → chunk + embed + upsert into ChromaDB
  4. Poll until ingestion done
  5. Exit 0
"""

import os
import sys
import time

import httpx

SCRAPER_URL = os.getenv("SCRAPER_SERVICE_URL", "http://scraper_service:8083")
STORE_URL = os.getenv("VECTOR_STORE_SERVICE_URL", "http://vector_store_service:8084")
POLL_INTERVAL = int(os.getenv("PIPELINE_POLL_SECONDS", "5"))


def log(msg: str) -> None:
    print(f"[pipeline] {msg}", flush=True)


def post(url: str, body: dict | None = None) -> dict:
    response = httpx.post(url, json=body, timeout=30)
    response.raise_for_status()
    return response.json()


def get(url: str) -> dict:
    response = httpx.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def poll_until_done(status_url: str, job_id: str) -> None:
    while True:
        status = get(f"{status_url}/{job_id}")
        phase = status.get("phase", "unknown")
        log(f"  phase={phase} | {status}")
        if phase == "done":
            return
        if phase == "error":
            log(f"Job failed: {status.get('detail', '')}")
            sys.exit(1)
        time.sleep(POLL_INTERVAL)


def main() -> None:
    # ── Step 1: Scraping ───────────────────────────────────────────────────────
    log("Starting scraper...")
    result = post(f"{SCRAPER_URL}/scraper/start", body={"max_pages": 5, "delay": 1.0})
    job_id = result["job_id"]
    log(f"Scraper job started: {job_id}")
    poll_until_done(f"{SCRAPER_URL}/scraper/status", job_id)
    log("Scraping complete.")

    # ── Step 2: Ingestion ──────────────────────────────────────────────────────
    log("Starting ingestion...")
    result = post(f"{STORE_URL}/ingest/start")
    job_id = result["job_id"]
    log(f"Ingest job started: {job_id}")
    poll_until_done(f"{STORE_URL}/ingest/status", job_id)
    log("Ingestion complete. Knowledge base ready.")


if __name__ == "__main__":
    main()
