"""
LLM factory — returns the right client based on LLM_PROVIDER env var.

To add a new provider:
  1. Create its module (e.g. openai.py) implementing LLMClient.
  2. Add a case below.
  3. Set LLM_PROVIDER in .env.
"""

from agent.llm.base import LLMClient
from config import settings


def create_llm() -> LLMClient:
    match settings.llm_provider:
        case "groq":
            from agent.llm.groq import GroqClient
            return GroqClient()
        case _:
            raise ValueError(
                f"Unknown LLM_PROVIDER: '{settings.llm_provider}'. "
                "Supported: groq"
            )
