# -------------------------------------------------------------------------
# Copyright. All rights reserved.
# by Cristian Beltran
# --------------------------------------------------------------------------


"""
HTML parsing helpers for bancolombia.com.

Parse strategy (in order):
  1. __NEXT_DATA__ — Bancolombia's site is a Next.js app. The server embeds a JSON blob
     in a <script id="__NEXT_DATA__"> tag that contains the pre-rendered page props,
     including cleaned text fields. This gives us structured content without needing
     to strip navigation, ads, or repeated chrome.
  2. BeautifulSoup fallback — if Next.js data is absent or yields no usable text,
     we remove layout noise (nav, footer, header, aside) and extract the main body.

Pages with fewer than 100 characters after cleaning are discarded as empty/error pages.
"""

import json
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


def extract_links(html: str, current_url: str) -> list[str]:
    """Finds all internal pages links in an HTML page."""
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


def _parse_next_data(soup: BeautifulSoup, url: str) -> dict | None:
    """Extracts content from the Next.js __NEXT_DATA__ JSON blob.

    Next.js embeds the full page props as JSON so the client can hydrate without
    a second request. For content pages this usually has 'content', 'body', or
    'description' at the top level of pageProps. If none of those exist, _flatten
    walks the props tree and concatenates any string longer than 20 chars.
    """
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


def _get_title(soup: BeautifulSoup) -> str:
    tag = soup.find("h1") or soup.find("title")
    return tag.get_text(strip=True) if tag else "Sin título"


def _flatten(data: dict, depth: int = 0) -> str:
    """Recursively collects string values from a nested dict.

    Used as a last-resort when no known field name ('content', 'body', etc.) is found
    in pageProps. Depth is capped at 4 to avoid traversing arbitrarily deep React trees.
    Only strings longer than 20 chars are kept to filter out IDs, class names, and booleans.
    """
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
