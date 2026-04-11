"""
Recursive text chunker.

Strategy: try to split on natural boundaries first (paragraph → line → sentence → word).
If none of those produce more than one chunk, fall back to a hard character-level cut.
This preserves semantic units as much as possible before resorting to brute force.

Each chunk carries the full page metadata so the vector store can filter and retrieve
without needing to join back to the original document.
"""

import hashlib


def split_into_chunks(page: dict, size: int = 512, overlap: int = 64) -> list[dict]:
    """Splits a page's text into overlapping chunks keeping all metadata."""
    chunks = _split(page["text"], size, overlap)
    return [
        {
            "chunk_id": _make_id(page["url"], i),
            "url": page["url"],
            "title": page["title"],
            "category": page["category"],
            "chunk_index": i,
            "total_chunks": len(chunks),
            "scraped_at": page.get("scraped_at", ""),
            "text": chunk,
        }
        for i, chunk in enumerate(chunks)
    ]


def _make_id(url: str, index: int) -> str:
    """Deterministic ID: same URL + same position always produces the same hash.
    This makes upserts idempotent — re-running ingestion won't duplicate chunks."""
    return hashlib.sha256(f"{url}:{index}".encode()).hexdigest()[:16]


def _split(text: str, size: int, overlap: int) -> list[str]:
    """Try each separator in order of coarseness. Stop as soon as we get multiple chunks.
    Fallback: hard cut at character level (guarantees we never exceed `size`)."""
    for sep in ["\n\n", "\n", ". ", " "]:
        parts = [p.strip() for p in text.split(sep) if p.strip()]
        chunks = _merge(parts, size, overlap, sep)
        if len(chunks) > 1:
            return chunks
    # Hard cut — only reached if the entire text has no whitespace or punctuation
    return [text[i: i + size] for i in range(0, len(text), size - overlap)]


def _merge(parts: list[str], size: int, overlap: int, sep: str) -> list[str]:
    """Greedily accumulates parts into a chunk until `size` is exceeded.
    When a chunk is full, the tail (`overlap` chars) is carried into the next chunk
    so that context is not lost at the boundary."""
    chunks: list[str] = []
    current = ""
    for part in parts:
        candidate = f"{current}{sep}{part}".strip() if current else part
        if len(candidate) <= size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # Seed the next chunk with the overlap tail from the previous one
            current = current[-overlap:] + sep + part if overlap else part
    if current:
        chunks.append(current)
    return chunks
