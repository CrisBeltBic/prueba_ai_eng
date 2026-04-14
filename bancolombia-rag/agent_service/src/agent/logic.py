"""
Agent logic — ReAct loop.

Flow per request:
  1. Load chat history from chat_service (if chat_id provided)
  2. Build messages: system prompt + history + user message
  3. Fetch available MCP tools
  4. Call LLM → if it requests tools, execute them and loop back (max N iterations)
  5. When LLM produces a text reply, save both turns to chat_service
  6. Return reply + collected source URLs + chat_id
"""

import json
from pathlib import Path

import httpx
import yaml

from agent.llm.base import LLMClient
from agent.llm.factory import create_llm
from agent.mcp_client import MCPClient

# ---------------------------------------------------------------------------
# Capabilities — loaded once at import time
# ---------------------------------------------------------------------------

_caps_path = Path(__file__).parent.parent / "capabilities.yaml"
_caps: dict = yaml.safe_load(_caps_path.read_text())

_MAX_TOOL_CALLS: int = _caps["retrieval"]["max_tool_calls"]
_HISTORY_TURNS: int = _caps["memory"]["history_turns"]
_OUT_OF_SCOPE: str = _caps["scope"]["out_of_scope_message"]
_AGENT_NAME: str = _caps["agent"]["name"]
_TONE: str = _caps["agent"]["tone"]

_SYSTEM_PROMPT = f"""Eres {_AGENT_NAME}, un asistente virtual de Bancolombia.
Tu tono debe ser {_TONE}.
Solo respondes preguntas sobre productos y servicios de Bancolombia para personas naturales.
Cuando necesites información, usa las herramientas disponibles para buscar en la base de conocimiento.
Si la información no está disponible en la base de conocimiento, indícalo claramente.
Responde siempre en español."""


# ---------------------------------------------------------------------------
# AgentLogic
# ---------------------------------------------------------------------------

class AgentLogic:
    def __init__(self, chat_service_url: str) -> None:
        self._chat_url = chat_service_url
        self._llm: LLMClient = create_llm()
        self._mcp: MCPClient = MCPClient()

    async def start(self) -> None:
        """Connect to MCP server. Call once at app startup."""
        await self._mcp.connect()

    async def stop(self) -> None:
        """Disconnect from MCP server. Call once at app shutdown."""
        await self._mcp.close()

    async def chat(self, message: str, chat_id: str | None) -> dict:
        """Run one user turn through the ReAct loop.

        Returns:
            {
                "chat_id": str,
                "reply":   str,
                "sources": list[str],
            }
        """
        history = await self._load_history(chat_id)
        tools = await self._get_tools()

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            *history,
            {"role": "user", "content": message},
        ]

        reply, sources = await self._react_loop(messages, tools)

        saved_chat_id = await self._save_turn(
            chat_id=chat_id,
            user_message=message,
            assistant_reply=reply,
            sources=sources,
        )

        return {"chat_id": saved_chat_id, "reply": reply, "sources": sources}

    # Internal helpers
    async def _react_loop( self, messages: list[dict], tools: list[dict]) -> tuple[str, list[str]]:
        """Iterate LLM - tools until the LLM produces a text reply.

        Returns (reply_text, collected_source_urls).
        """
        sources: list[str] = []
        #print(f"tools: {tools}", flush=True)

        for iteration in range(_MAX_TOOL_CALLS):
            #print(f"\n[{iteration + 1}] mensajes en contexto: {len(messages)}", flush=True)
            response = await self._llm.chat(messages, tools=tools)
            #print(f"[ {iteration + 1}] respuesta del LLM recibida; {response}", flush=True)
            #print(f"[{iteration + 1}] tool_calls: {response['tool_calls']}", flush=True)
            #print(f"[{iteration + 1}] content: {str(response['content'])[:200]}", flush=True)

            # LLM wants to call one or more tools
            if response["tool_calls"]:
                messages.append({
                    "role": "assistant",
                    "content": response["content"],
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": tc["args"],
                            },
                        }
                        for tc in response["tool_calls"]
                    ],
                })

                #print(f"Messages after appending tool calls: {messages}", flush=True)

                for tc in response["tool_calls"]:
                    #print(f"[react loop {iteration + 1}] ejecutando tool '{tc['name']}' args: {tc['args']}", flush=True)
                    args = json.loads(tc["args"]) if isinstance(tc["args"], str) else tc["args"]
                    result = await self._mcp.call_tool(tc["name"], args)
                    #print(f"[react loop {iteration + 1}] resultado: {len(result)} items", flush=True)

                    for item in result:
                        if isinstance(item, dict) and item.get("url"):
                            if item["url"] not in sources:
                                sources.append(item["url"])

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(result, ensure_ascii=False),
                    })

                continue

            if response["content"]:
                return response["content"], sources

        return _OUT_OF_SCOPE, sources

    async def _get_tools(self) -> list[dict]:
        """Fetch available MCP tools and convert to OpenAI tool format."""
        session = self._mcp._session  # noqa: SLF001
        if session is None:
            return []
        result = await session.list_tools()
        return [_mcp_tool_to_openai(t) for t in result.tools]

    async def _load_history(self, chat_id: str | None) -> list[dict]:
        """Fetch the last N turns from chat_service for this chat_id."""
        if not chat_id:
            return []
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"{self._chat_url}/chats/{chat_id}/messages",
                    params={"limit": _HISTORY_TURNS * 2},  # *2: user+assistant per turn
                )
                resp.raise_for_status()
                rows = resp.json()
        except Exception:
            return []

        return [{"role": r["role"], "content": r["content"]} for r in rows]

    async def _save_turn(self, chat_id: str | None, user_message: str, assistant_reply: str, sources: list[str]) -> str:
        """Save user + assistant messages to chat_service. Returns chat_id."""
        async with httpx.AsyncClient(timeout=5) as client:
            # Save user message — chat_id may be None (new conversation)
            resp = await client.post(
                f"{self._chat_url}/chats/messages",
                json={"chat_id": chat_id, "role": "user", "content": user_message},
            )
            resp.raise_for_status()
            resolved_chat_id: str = resp.json()["chat_id"]

            # Save assistant reply with the same chat_id
            await client.post(
                f"{self._chat_url}/chats/messages",
                json={
                    "chat_id": resolved_chat_id,
                    "role": "assistant",
                    "content": assistant_reply,
                    "sources": sources,
                },
            )

        return resolved_chat_id


# Helper
def _mcp_tool_to_openai(tool) -> dict:
    """Convert an MCP Tool object to OpenAI function-calling format.

    Sanitizes the schema: replaces anyOf nullable patterns with plain types
    so models that don't handle complex schemas don't fail.
    """
    schema = _sanitize_schema(tool.inputSchema or {"type": "object", "properties": {}})
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": schema,
        },
    }


def _sanitize_schema(schema: dict) -> dict:
    """Flatten anyOf/oneOf nullable patterns into plain types.

    FastMCP generates `"anyOf": [{"type": "string"}, {"type": "null"}]` for
    optional parameters. Most LLMs handle simple types better.
    """
    if not isinstance(schema, dict):
        return schema

    result = {}
    for key, value in schema.items():
        if key == "properties" and isinstance(value, dict):
            result[key] = {k: _sanitize_schema(v) for k, v in value.items()}
        elif key == "anyOf" and isinstance(value, list):
            # Extract the non-null type from anyOf
            non_null = [t for t in value if t.get("type") != "null"]
            if len(non_null) == 1:
                result.update(non_null[0])
            else:
                result[key] = value
        else:
            result[key] = value

    # Remove fields LLMs don't need
    result.pop("title", None)
    result.pop("default", None)

    return result
