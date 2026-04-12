"""
HTTP calls to vector_store_service.

This module knows nothing about MCP — it just fetches data over HTTP.
The server.py wraps these functions as MCP tools.
"""

import httpx

from config import settings


async def search(query: str, top_k: int = 5, category: str | None = None) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{settings.vector_store_url}/search",
            json={"query": query, "top_k": top_k, "category": category},
        )
        response.raise_for_status()
        return response.json()


async def get_article(url: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{settings.vector_store_url}/article",
            params={"url": url},
        )
        response.raise_for_status()
        return response.json()["chunks"]


async def list_categories() -> list[str]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{settings.vector_store_url}/categories")
        response.raise_for_status()
        return response.json()["categories"]


async def get_stats() -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{settings.vector_store_url}/stats")
        response.raise_for_status()
        return response.json()
