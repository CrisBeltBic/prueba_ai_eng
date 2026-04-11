import json
import uuid
from datetime import datetime
from typing import Any

from config import settings
from helpers.chunker import split_into_chunks
from helpers.embedder import embed_query, embed_texts
from store.bridge.base import VectorStore
from store.bridge.factory import create_vector_store

_store: VectorStore | None = None
_jobs: dict[str, dict[str, Any]] = {}


def _get_store() -> VectorStore:
    global _store
    if _store is None:
        _store = create_vector_store()
    return _store


# ── Job management ─────────────────────────────────────────────────────────────

def create_job() -> str:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"phase": "starting", "pages_read": 0, "chunks_indexed": 0, "errors": 0}
    return job_id


def get_job_status(job_id: str) -> dict:
    if job_id not in _jobs:
        return {"error": "Job not found"}
    return {"job_id": job_id, **_jobs[job_id]}


# ── Ingestion pipeline ─────────────────────────────────────────────────────────

def run_ingest(job_id: str) -> None:
    """Reads pages.jsonl, chunks each page, embeds and upserts into the vector store."""
    status = _jobs[job_id]
    raw_file = settings.raw_file

    if not raw_file.exists():
        status["phase"] = "error"
        status["detail"] = f"{raw_file} not found — run the scraper first"
        return

    status["phase"] = "reading"
    pages = _read_jsonl(raw_file)
    status["pages_read"] = len(pages)

    status["phase"] = "indexing"
    for page in pages:
        try:
            chunks = split_into_chunks(page, settings.chunk_size, settings.chunk_overlap)
            texts = [c["text"] for c in chunks]
            embeddings = embed_texts(texts)
            for chunk, embedding in zip(chunks, embeddings):
                chunk["embedding"] = embedding
            _get_store().upsert(chunks)
            status["chunks_indexed"] = status.get("chunks_indexed", 0) + len(chunks)
        except Exception:
            status["errors"] = status.get("errors", 0) + 1

    status["phase"] = "done"
    status["finished_at"] = datetime.utcnow().isoformat()


# ── Search ─────────────────────────────────────────────────────────────────────

def search(query: str, top_k: int, category: str | None) -> list[dict]:
    """Semantic search — returns top_k matches each expanded with neighbor chunks."""
    embedding = embed_query(query)
    results = _get_store().search(embedding, top_k, category)

    for result in results:
        result["context"] = _build_context(result["url"], result["chunk_index"])

    return results


def _build_context(url: str, chunk_index: int) -> str:
    """Fetches prev + current + next chunks from the same page and concatenates them."""
    all_chunks = _get_store().get_by_url(url)

    # index chunks by position
    by_index = {c["chunk_index"]: c["text"] for c in all_chunks}

    parts = []
    for i in [chunk_index - 1, chunk_index, chunk_index + 1]:
        if i in by_index:
            parts.append(by_index[i])

    return " ".join(parts)


# ── Passthrough to store ───────────────────────────────────────────────────────

def get_by_url(url: str) -> list[dict]:
    return _get_store().get_by_url(url)


def list_categories() -> list[str]:
    return _get_store().list_categories()


def get_stats() -> dict:
    return _get_store().get_stats()


# ── Private helpers ────────────────────────────────────────────────────────────

def _read_jsonl(path) -> list[dict]:
    pages = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    pages.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return pages
