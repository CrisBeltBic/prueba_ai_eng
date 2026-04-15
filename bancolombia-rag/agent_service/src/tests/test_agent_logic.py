"""Tests for agent/logic.py — chat, _get_tools, _load_history."""
# docker exec bancolombia-rag-agent_service-1 pytest /app/tests/ -v
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.logic import AgentLogic


@pytest.fixture
def agent():
    """AgentLogic instance with LLM and MCP mocked out."""
    with patch("agent.logic.create_llm"), patch("agent.logic.MCPClient"):
        return AgentLogic(chat_service_url="http://test:8082")


# _load_history

async def test_load_history_returns_empty_when_no_chat_id(agent):
    result = await agent._load_history(None)
    assert result == []


async def test_load_history_returns_formatted_messages(agent):
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": "¿en qué te ayudo?"},
    ]
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("agent.logic.httpx.AsyncClient", return_value=mock_client):
        result = await agent._load_history("chat-123")

    assert len(result) == 2
    assert result[0] == {"role": "user", "content": "hola"}


async def test_load_history_returns_empty_on_error(agent):
    with patch("agent.logic.httpx.AsyncClient", side_effect=Exception("connection error")):
        result = await agent._load_history("chat-123")
    assert result == []


# _get_tools

async def test_get_tools_returns_empty_when_no_session(agent):
    agent._mcp._session = None
    result = await agent._get_tools()
    assert result == []


async def test_get_tools_returns_openai_format(agent):
    mock_tool = MagicMock()
    mock_tool.name = "search_knowledge_base"
    mock_tool.description = "Search the knowledge base"
    mock_tool.inputSchema = {"type": "object", "properties": {"query": {"type": "string"}}}

    mock_session = AsyncMock()
    mock_session.list_tools.return_value = MagicMock(tools=[mock_tool])
    agent._mcp._session = mock_session

    result = await agent._get_tools()

    assert len(result) == 1
    assert result[0]["type"] == "function"
    assert result[0]["function"]["name"] == "search_knowledge_base"


# chat

async def test_chat_returns_expected_structure(agent):
    agent._load_history = AsyncMock(return_value=[])
    agent._get_tools = AsyncMock(return_value=[])
    agent._react_loop = AsyncMock(return_value=("respuesta del agente", ["https://bancolombia.com"]))
    agent._save_turn = AsyncMock(return_value="chat-abc")

    result = await agent.chat("¿qué es un CDT?", chat_id=None)

    assert result["chat_id"] == "chat-abc"
    assert result["reply"] == "respuesta del agente"
    assert result["sources"] == ["https://bancolombia.com"]
