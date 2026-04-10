import hashlib
import json
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


def extract_links(html: str, current_url: str) -> list[str]:
    """Finds all internal Bancolombia /personas links in an HTML page."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for tag in soup.find_all("a", href=True):
        full_url = urljoin(current_url, tag["href"])
        parsed = urlparse(full_url)
        if (
            parsed.netloc == "www.bancolombia.com"
            and parsed.path.startswith("/personas")
            and not parsed.path.endswith((".pdf", ".jpg", ".png", ".css", ".js"))
        ):
            links.append(f"{parsed.scheme}://{parsed.netloc}{parsed.path}")
    return links


def parse_page(html: str, url: str) -> dict | None:
    """Extracts clean text and metadata from an HTML page."""
    soup = BeautifulSoup(html, "html.parser")
    result = _parse_next_data(soup, url) or _parse_html(soup, url)
    if not result or len(result["text"]) < 100:
        return None
    return result


def split_into_chunks(page: dict, size: int = 512, overlap: int = 64) -> list[dict]:
    """Splits a page's text into overlapping chunks keeping metadata."""
    chunks = _split(page["text"], size, overlap)
    return [
        {
            "chunk_id": _make_id(page["url"], i),
            "url": page["url"],
            "title": page["title"],
            "category": page["category"],
            "text": chunk,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "scraped_at": page["scraped_at"],
        }
        for i, chunk in enumerate(chunks)
    ]


# ── private helpers ────────────────────────────────────────────────────────────

def _parse_next_data(soup: BeautifulSoup, url: str) -> dict | None:
    tag = soup.find("script", {"id": "__NEXT_DATA__"})
    if not tag:
        return None
    try:
        data = json.loads(tag.string)
        props = data.get("props", {}).get("pageProps", {})
        text = props.get("content") or props.get("body") or props.get("description") or _flatten(props)
        title = props.get("title") or props.get("name") or _get_title(soup)
        if not text:
            return None
        return {"url": url, "title": title, "text": clean(text), "category": get_category(url)}
    except Exception:
        return None


def _parse_html(soup: BeautifulSoup, url: str) -> dict | None:
    for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body
    if not main:
        return None
    return {"url": url, "title": _get_title(soup), "text": clean(main.get_text(separator=" ")), "category": get_category(url)}


def _split(text: str, size: int, overlap: int) -> list[str]:
    for sep in ["\n\n", "\n", ". ", " "]:
        parts = [p.strip() for p in text.split(sep) if p.strip()]
        chunks = _merge(parts, size, overlap, sep)
        if len(chunks) > 1:
            return chunks
    return [text[i : i + size] for i in range(0, len(text), size - overlap)]


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


def _get_title(soup: BeautifulSoup) -> str:
    tag = soup.find("h1") or soup.find("title")
    return tag.get_text(strip=True) if tag else "Sin título"


def _flatten(data: dict, depth: int = 0) -> str:
    if depth > 4:
        return ""
    parts = []
    for value in data.values():
        if isinstance(value, str) and len(value) > 20:
            parts.append(value)
        elif isinstance(value, dict):
            parts.append(_flatten(value, depth + 1))
    return " ".join(parts)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def get_category(url: str) -> str:
    parts = urlparse(url).path.strip("/").split("/")
    return parts[1] if len(parts) > 1 else "general"


def make_id(url: str, index: int) -> str:
    return hashlib.sha256(f"{url}:{index}".encode()).hexdigest()[:16]
