# -------------------------------------------------------------------------
# Copyright. All rights reserved.
# by Cristian Beltran
# --------------------------------------------------------------------------

"""
Scraper business logic.

Two-phase pipeline:
  Phase 1 — _crawl:            BFS from /personas, collecting allowed URLs up to max_pages.
  Phase 2 — _scrape_and_save:  Fetches each URL, parses the page, appends to pages.jsonl.

robots.txt is loaded once at the start of each job and checked before every request.
Concurrency is controlled by asyncio.Semaphore to limit simultaneous open connections.
"""

import asyncio
import contextlib
import json
import uuid
from datetime import datetime
from typing import Any
from urllib.robotparser import RobotFileParser

import httpx

from config import settings
from helpers.page_parser import extract_links, parse_page

_jobs: dict[str, dict[str, Any]] = {}


#Job management

def create_job() -> str:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"phase": "starting", "urls_found": 0, "pages_scraped": 0, "errors": 0}
    return job_id


def get_job_status(job_id: str) -> dict:
    if job_id not in _jobs:
        return {"error": "Job not found"}
    return {"job_id": job_id, **_jobs[job_id]}


def list_jobs() -> list[dict]:
    return [{"job_id": jid, **s} for jid, s in _jobs.items()]


# robots.txt

def _load_robots(base_url: str, user_agent: str) -> RobotFileParser:
    """Fetches and parses robots.txt. If unreachable, allows everything."""
    rp = RobotFileParser()
    rp.set_url(f"{base_url}/robots.txt")
    with contextlib.suppress(Exception):
        rp.read()  # If robots.txt is unreachable we proceed — public site, no restriction found
    return rp


def _is_allowed(rp: RobotFileParser, url: str, user_agent: str) -> bool:
    return rp.can_fetch(user_agent, url)


# Pipeline

async def run_scraper(job_id: str, max_pages: int, delay: float) -> None:
    """Crawls /personas, parses each page and saves results to a JSONL file."""
    status = _jobs[job_id]

    rp = _load_robots(settings.base_url, settings.user_agent)

    status["phase"] = "crawling"
    urls = await _crawl(max_pages, delay, status, rp)

    status["phase"] = "scraping"
    await _scrape_and_save(urls, delay, status, rp)

    status["phase"] = "done"
    status["finished_at"] = datetime.utcnow().isoformat()


async def _crawl(max_pages: int, delay: float, status: dict, rp: RobotFileParser) -> list[str]:
    """BFS from start_path. Collects unique /personas URLs up to max_pages.

    Disallowed URLs are added to `visited` immediately so they are never retried.
    The semaphore limits open connections; the delay after each fetch is the politeness gap.
    """
    visited: set[str] = set()
    queue: list[str] = [settings.base_url + settings.start_path]
    headers = {"User-Agent": settings.user_agent}

    async with httpx.AsyncClient(headers=headers, timeout=10, follow_redirects=True) as client:
        semaphore = asyncio.Semaphore(settings.max_concurrent)

        while queue and len(visited) < max_pages:
            url = queue.pop(0)
            if url in visited:
                continue

            if not _is_allowed(rp, url, settings.user_agent):
                visited.add(url)  # mark visited so we don't retry disallowed URLs
                continue

            async with semaphore:
                try:
                    response = await client.get(url)
                    visited.add(url)
                    await asyncio.sleep(delay)
                    for link in extract_links(response.text, url):
                        if link not in visited:
                            queue.append(link)
                except Exception:
                    visited.add(url)

    status["urls_found"] = len(visited)
    return list(visited)


async def _scrape_and_save(urls: list[str], delay: float, status: dict, rp: RobotFileParser) -> None:
    raw_file = settings.raw_file
    headers = {"User-Agent": settings.user_agent}

    raw_file.parent.mkdir(parents=True, exist_ok=True)
    raw_file.unlink(missing_ok=True)  # truncate before writing so re-runs don't duplicate lines

    async with httpx.AsyncClient(headers=headers, timeout=10, follow_redirects=True) as client:
        for url in urls:
            if not _is_allowed(rp, url, settings.user_agent):
                continue
            try:
                response = await client.get(url)
                page = parse_page(response.text, url)
                if page:
                    page["scraped_at"] = datetime.utcnow().isoformat()
                    with raw_file.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(page) + "\n")
                    status["pages_scraped"] = status.get("pages_scraped", 0) + 1
                await asyncio.sleep(delay)
            except Exception:
                status["errors"] = status.get("errors", 0) + 1
