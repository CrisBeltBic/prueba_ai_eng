"""
MCP client — launches knowledge_server as a subprocess and keeps the session alive.

Usage:
    client = MCPClient()
    await client.connect()
    results = await client.call_tool("search_knowledge_base", {"query": "créditos"})
    await client.close()
"""

import json
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    def __init__(self) -> None:
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None

    async def connect(self) -> None:
        """Launch knowledge_server/server.py as a subprocess and open MCP session."""
        server_params = StdioServerParameters(
            command=sys.executable,                 # same python binary as the agent # Equivale a hacer python knowledge_server/server.py en la terminal.
            args=["knowledge_server/server.py"],
        )

        self._exit_stack = AsyncExitStack()
        read, write = await self._exit_stack.enter_async_context(stdio_client(server_params))
        self._session = await self._exit_stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()

    async def call_tool(self, name: str, args: dict) -> list:
        """Call an MCP tool and return the result as plain Python objects.

        MCP wraps results in TextContent objects where .text holds the
        JSON-serialized return value. This method unwraps them so callers
        always receive a plain list of dicts.
        """
        if not self._session:
            raise RuntimeError("MCPClient not connected — call connect() first")
        result = await self._session.call_tool(name, args)

        items = []
        for content in result.content:
            if hasattr(content, "text"):
                try:
                    parsed = json.loads(content.text)
                    if isinstance(parsed, list):
                        items.extend(parsed)
                    else:
                        items.append(parsed)
                except (json.JSONDecodeError, TypeError):
                    items.append({"text": content.text})
        return items

    async def close(self) -> None:
        """Close the session and terminate the subprocess."""
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
            self._session = None
