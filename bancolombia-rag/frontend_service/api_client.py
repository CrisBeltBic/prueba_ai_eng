"""
HTTP clients for agent_service and chat_service.

Uses synchronous `requests` — Streamlit runs in a single thread and does not
need async I/O here. Each method handles exceptions gracefully so the UI
degrades without crashing.
"""

import os

import requests

_AGENT_URL = os.getenv("AGENT_SERVICE_URL", "http://localhost:8080")
_CHAT_URL = os.getenv("CHAT_SERVICE_URL", "http://localhost:8082")
_API_KEY = os.getenv("AGENT_API_SERVICE_KEY", "")


class AgentClient:
    """Thin wrapper around POST /chat on agent_service."""

    def __init__(self, base_url: str = _AGENT_URL) -> None:
        self._base = base_url.rstrip("/")
        self._headers = {"X-API-Key": _API_KEY} if _API_KEY else {}

    def chat(self, message: str, chat_id: str | None) -> dict:
        """Send a user message.  Returns {chat_id, reply, sources}."""
        resp = requests.post(
            f"{self._base}/chat",
            json={"message": message, "chat_id": chat_id},
            headers=self._headers,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()

    def health(self) -> bool:
        try:
            return requests.get(f"{self._base}/health", timeout=3).ok
        except Exception:
            return False


class ChatClient:
    """Thin wrapper around chat_service read endpoints."""

    def __init__(self, base_url: str = _CHAT_URL) -> None:
        self._base = base_url.rstrip("/")

    def list_chats(self) -> list[dict]:
        """Return all chats sorted newest-first. Empty list on error."""
        try:
            resp = requests.get(f"{self._base}/chats", timeout=5)
            resp.raise_for_status()
            chats = resp.json()
            return sorted(chats, key=lambda c: c["started_at"], reverse=True)
        except Exception:
            return []

    def get_messages(self, chat_id: str) -> list[dict]:
        """Return ordered messages for a chat. Empty list on error."""
        try:
            resp = requests.get(f"{self._base}/chats/{chat_id}/messages", timeout=5)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return []