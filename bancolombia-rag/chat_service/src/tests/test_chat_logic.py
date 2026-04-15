"""Tests for chat/logic.py — _parse_row, add_message, get_messages."""
#docker exec bancolombia-rag-chat_service-1 pytest /app/tests/ -v

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch
from chat.logic import _parse_row, add_message, add_message, get_messages


# _parse_row — pure function, no mocking needed

def test_parse_row_deserializes_sources_string():
    row = {"chat_id": "abc", "role": "user", "content": "hola",
           "sources": '["https://bancolombia.com"]', "timestamp": datetime.now()}
    result = _parse_row(row)
    assert result["sources"] == ["https://bancolombia.com"]


def test_parse_row_converts_uuid_to_str():
    uid = uuid.uuid4()
    row = {"chat_id": uid, "role": "user", "content": "hola",
           "sources": [], "timestamp": datetime.now()}
    result = _parse_row(row)
    assert isinstance(result["chat_id"], str)
    assert result["chat_id"] == str(uid)


# add_message — mocked pool

async def test_add_message_returns_message_with_chat_id():
    chat_id = str(uuid.uuid4())
    mock_row = {"chat_id": chat_id, "role": "user", "content": "hola",
                "sources": "[]", "timestamp": datetime.now()}
    mock_pool = AsyncMock()
    mock_pool.fetchrow.return_value = mock_row

    with patch("chat.logic.get_pool", new=AsyncMock(return_value=mock_pool)):
        result = await add_message(chat_id, "user", "hola", [], None)

    assert result["chat_id"] == chat_id
    assert result["role"] == "user"


async def test_add_message_generates_chat_id_when_none():
    mock_pool = AsyncMock()
    mock_pool.fetchrow.return_value = {
        "chat_id": "generated", "role": "user",
        "content": "hola", "sources": "[]", "timestamp": datetime.now(),
    }

    with patch("chat.logic.get_pool", new=AsyncMock(return_value=mock_pool)):
        await add_message(None, "user", "hola", [], None)

    # second positional arg to the SQL query is the chat_id
    call_args = mock_pool.fetchrow.call_args[0]
    assert call_args[1] is not None


# get_messages — mocked pool

async def test_get_messages_returns_all_messages():
    now = datetime.now()
    mock_rows = [
        {"chat_id": "abc", "role": "user", "content": "hola", "sources": "[]", "timestamp": now},
        {"chat_id": "abc", "role": "assistant", "content": "¿en qué te ayudo?", "sources": "[]", "timestamp": now},
    ]
    mock_pool = AsyncMock()
    mock_pool.fetch.return_value = mock_rows

    with patch("chat.logic.get_pool", new=AsyncMock(return_value=mock_pool)):
        result = await get_messages("abc")

    assert len(result) == 2
    assert result[0]["role"] == "user"
    assert result[1]["role"] == "assistant"
