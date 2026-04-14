"""
Groq LLM client.

Uses the OpenAI-compatible Groq API — same request/response format as OpenAI,
just a different base_url and api_key.
"""

import json
import re

from groq import AsyncGroq, BadRequestError

from config import settings


class GroqClient:
    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=settings.groq_api_key)
        self._model = settings.groq_model

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> dict:
        kwargs = {"model": self._model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = await self._client.chat.completions.create(**kwargs)
            choice = response.choices[0].message
            print(f'choice: {choice}', flush=True)
            return {
                "content": choice.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "args": tc.function.arguments,
                    }
                    for tc in (choice.tool_calls or [])
                ] or None,
            }

        except BadRequestError as e:
            # Some llama models generate tool calls in <function=name {...}> text
            # format instead of structured JSON. Groq rejects this with 400 and
            # includes the raw generation in failed_generation. We recover from it.
            tool_call = _parse_failed_generation(e)
            if tool_call:
                print(f"[groq] recuperado tool call: {tool_call['name']}", flush=True)
                return {"content": None, "tool_calls": [tool_call]}
            raise


def _parse_failed_generation(error: BadRequestError) -> dict | None:
    """Extract a tool call from Groq's failed_generation error field."""
    try:
        body = error.response.json()
        failed = body.get("error", {}).get("failed_generation", "")
        match = re.search(r"<function=(\w+)\s*(\{.*?\})\s*</function>", failed, re.DOTALL)
        if not match:
            return None
        name = match.group(1)
        args = match.group(2).strip()
        json.loads(args)  # valida que sea JSON válido
        return {"id": "recovered-0", "name": name, "args": args}
    except Exception:
        return None
