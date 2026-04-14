"""
MCP server — exposes the knowledge base as tools the agent can invoke.

Transport: stdio (mandatory per spec). The agent launches this script as a
subprocess and communicates via stdin/stdout using the MCP JSON-RPC protocol.

Run standalone for testing:
    python knowledge_server/server.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP

from knowledge_server import logic

mcp = FastMCP("bancolombia-knowledge")


# Tools

@mcp.tool()
async def search_knowledge_base(query: str, top_k: int = 5) -> list[dict]:
    """Search knowledge base using a natural language query.

    Returns the most relevant document chunks with their source URLs and
    relevance scores. Use this tool whenever the user asks about Bancolombia
    products, services, rates, or any information that may be on their website.

    Args:
        query: The user's question in natural language.
        top_k: Number of results to return (default 5).
    """
    try:
        return await logic.search(query, top_k, category=None)
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
async def get_article_by_url(url: str) -> list[dict]:
    """Retrieve the full content of a Bancolombia article by its URL.

    Use this tool when the user asks for more details about a specific page
    already referenced in a previous search result.

    Args:
        url: The full URL of the Bancolombia article.
    """
    try:
        return await logic.get_article(url)
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
async def list_categories() -> list[str]|list[dict]:
    """List all available categories in the knowledge base.

    Use this tool to understand what topics are indexed before searching,
    or when the user asks what subjects the assistant can help with.
    """
    try:
        return await logic.list_categories()
    except Exception as e:
        return [{"error": str(e)}]


# Resource endpoints
@mcp.resource("knowledgebase://stats")
async def get_stats() -> dict:
    """Knowledge base statistics: total chunks, categories, embedding model."""
    try:
        return await logic.get_stats()
    except Exception as e:
        return {"error": str(e)}


# Entry point

if __name__ == "__main__":
    mcp.run()  # stdio transport by default
