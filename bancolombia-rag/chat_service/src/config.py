"""
Settings for chat_service.
DATABASE_URL uses the native asyncpg format (postgresql://, not postgresql+asyncpg://).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://chat_user:chat_password@postgres:5432/chat_db",
    )


settings = Settings()
