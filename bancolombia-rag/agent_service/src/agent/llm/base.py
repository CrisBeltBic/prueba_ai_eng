"""
LLM client protocol — the contract every provider must implement.

Adding a new provider means:
  1. Create a new file (e.g. openai.py) that implements this protocol.
  2. Add a case in factory.py.
  3. Set LLM_PROVIDER in .env.
"""

from typing import Protocol


class LLMClient(Protocol):
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> dict:
        """Send messages to the LLM and return its response.

        Args:
            messages: Conversation history in OpenAI format
                      [{"role": "user"|"assistant"|"system", "content": "..."}]
            tools:    Optional list of tools the LLM can invoke.

        Returns:
            {
                "content":   str | None,      # text response (None if tool call)
                "tool_calls": list | None,    # tool calls requested by the LLM
            }
        """
        ...
