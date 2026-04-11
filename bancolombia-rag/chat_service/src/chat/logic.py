"""
Chat queries — raw SQL via asyncpg.

Each function receives only the parameters it needs for filters or inserts.
No ORM, no models, no business logic beyond what the query itself expresses.
"""

import json
import uuid

from db import get_pool


def _parse_row(row) -> dict:
    """Normalize asyncpg row to plain Python types for Pydantic serialization."""
    row = dict(row)
    if isinstance(row.get("sources"), str):
        row["sources"] = json.loads(row["sources"])
    if row.get("chat_id") is not None:
        row["chat_id"] = str(row["chat_id"])
    return row


async def add_message(
    chat_id: str | None,
    role: str,
    content: str,
    sources: list[str],
    user_id: str | None,
) -> dict:
    # Generate a new chat_id if none provided (new conversation)
    resolved_chat_id = chat_id or str(uuid.uuid4())

    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO chats (chat_id, user_id, role, content, sources)
        VALUES ($1, $2, $3, $4, $5::jsonb)
        RETURNING chat_id, role, content, sources, timestamp
        """,
        resolved_chat_id, user_id, role, content, json.dumps(sources),
    )
    return _parse_row(row)


async def get_messages(chat_id: str, limit: int | None = None) -> list[dict]:
    pool = await get_pool()
    if limit:
        rows = await pool.fetch(
            """
            SELECT chat_id, role, content, sources, timestamp
            FROM (
                SELECT * FROM chats
                WHERE chat_id = $1
                ORDER BY timestamp DESC
                LIMIT $2
            ) sub
            ORDER BY timestamp ASC
            """,
            chat_id, limit,
        )
    else:
        rows = await pool.fetch(
            """
            SELECT chat_id, role, content, sources, timestamp
            FROM chats
            WHERE chat_id = $1
            ORDER BY timestamp ASC
            """,
            chat_id,
        )
    return [_parse_row(r) for r in rows]


async def list_chats() -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT chat_id, MIN(timestamp) AS started_at, COUNT(*) AS message_count
        FROM chats
        GROUP BY chat_id
        ORDER BY MIN(timestamp) DESC
        """
    )
    return [dict(r) for r in rows]
