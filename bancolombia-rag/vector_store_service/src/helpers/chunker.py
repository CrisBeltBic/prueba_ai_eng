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
    return hashlib.sha256(f"{url}:{index}".encode()).hexdigest()[:16]


def _split(text: str, size: int, overlap: int) -> list[str]:
    for sep in ["\n\n", "\n", ". ", " "]:
        parts = [p.strip() for p in text.split(sep) if p.strip()]
        chunks = _merge(parts, size, overlap, sep)
        if len(chunks) > 1:
            return chunks
    return [text[i: i + size] for i in range(0, len(text), size - overlap)]


def _merge(parts: list[str], size: int, overlap: int, sep: str) -> list[str]:
    chunks: list[str] = []
    current = ""
    for part in parts:
        candidate = f"{current}{sep}{part}".strip() if current else part
        if len(candidate) <= size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = current[-overlap:] + sep + part if overlap else part
    if current:
        chunks.append(current)
    return chunks
