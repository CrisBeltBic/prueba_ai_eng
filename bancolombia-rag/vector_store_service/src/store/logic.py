"""
Business logic for the vector store service.

Responsibilities:
- Ingestion pipeline: read pages.jsonl → chunk → embed → upsert into the vector store.
- Semantic search: embed the query → retrieve top-k chunks → expand each result with
  its neighboring chunks (prev + match + next) so the LLM receives richer context.
- Job tracking: each long-running operation (ingest) gets a UUID so the caller can
  poll for status without blocking.

The vector store is initialised lazily on first use (_get_store). This avoids a crash
at startup if ChromaDB is not yet ready, and lets the health check respond immediately.
"""

import contextlib
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
    """Lazy singleton — creates the adapter on first call, reuses it afterwards."""
    global _store
    if _store is None:
        _store = create_vector_store()
    return _store


#Job management 

def create_job() -> str:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"phase": "starting", "pages_read": 0, "chunks_indexed": 0, "errors": 0}
    return job_id


def get_job_status(job_id: str) -> dict:
    if job_id not in _jobs:
        return {"error": "Job not found"}
    return {"job_id": job_id, **_jobs[job_id]}


# Ingestion pipeline 

def run_ingest(job_id: str) -> None:
    """Reads pages.jsonl, chunks each page, embeds and upserts into the vector store.

    Pipeline per page:
      1. split_into_chunks  — recursive text splitter, produces overlapping char-windows
      2. embed_texts        — batch encode via sentence-transformers (batch_size=32)
      3. upsert             — idempotent write; re-running is safe (chunk_id is deterministic)
    """
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
            for chunk, embedding in zip(chunks, embeddings, strict=True):
                chunk["embedding"] = embedding
            _get_store().upsert(chunks)
            status["chunks_indexed"] = status.get("chunks_indexed", 0) + len(chunks)
        except Exception:
            status["errors"] = status.get("errors", 0) + 1

    status["phase"] = "done"
    status["finished_at"] = datetime.utcnow().isoformat()


#  Search

def search(query: str, top_k: int, category: str | None) -> list[dict]:
    """Semantic search — returns top_k matches each expanded with neighbor chunks."""
    embedding = embed_query(query)
    results = _get_store().search(embedding, top_k, category)

    for result in results:
        result["context"] = _build_context(result["url"], result["chunk_index"])
        result.pop("text", None)

    return results


def _build_context(url: str, chunk_index: int) -> str:
    """Returns the matched chunk plus its immediate neighbours from the same page.

    Sending prev + match + next to the LLM recovers context that was cut at chunk
    boundaries. Missing neighbours (first/last chunk) are silently skipped.
    """
    all_chunks = _get_store().get_by_url(url)
    by_index = {c["chunk_index"]: c["text"] for c in all_chunks}

    parts = []
    for i in [chunk_index - 1, chunk_index, chunk_index + 1]:
        if i in by_index:
            parts.append(by_index[i])

    return " ".join(parts)


#Passthrough to store

def get_by_url(url: str) -> list[dict]:
    return _get_store().get_by_url(url)


def list_categories() -> list[str]:
    return _get_store().list_categories()


def get_stats() -> dict:
    return _get_store().get_stats()


#Private helpers

def _read_jsonl(path) -> list[dict]:
    pages = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                with contextlib.suppress(json.JSONDecodeError):
                    pages.append(json.loads(line))
    return pages
