"""Settings for agent_service."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


class Settings:
    # Where knowledge_server sends its HTTP requests
    vector_store_url: str = os.getenv(
        "VECTOR_STORE_SERVICE_URL", "http://vector_store_service:8084"
    )

    # Where the agent saves/loads chat history
    chat_service_url: str = os.getenv(
        "CHAT_SERVICE_URL", "http://chat_service:8082"
    )

    # LLM configuration
    llm_provider: str = os.getenv("LLM_PROVIDER", "groq")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant") # llama-3.3-70b-versatile


settings = Settings()
