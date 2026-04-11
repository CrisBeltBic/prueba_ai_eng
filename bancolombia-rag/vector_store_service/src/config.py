"""
Settings for vector_store_service.

All values are read from the service's own .env file (loaded at import time).
Change VECTOR_STORE_PROVIDER to swap the underlying database without touching
any other code — the factory in store/bridge/factory.py handles the wiring.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


class Settings:
    # Which vector database adapter to use. Currently only "chroma" is supported.
    vector_store_provider: str = os.getenv("VECTOR_STORE_PROVIDER", "chroma")

    # ChromaDB connection — must match the service name in docker-compose.
    chroma_host: str = os.getenv("CHROMA_HOST", "localhost")
    chroma_port: int = int(os.getenv("CHROMA_PORT", "8000"))

    # Local sentence-transformers model. Downloaded on first run, then cached.
    # paraphrase-multilingual-mpnet-base-v2 produces 768-dim vectors and handles Spanish well.
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-mpnet-base-v2")

    # Chunk size in characters (not tokens). 800 chars ≈ 150–200 tokens for this model,
    # which fits comfortably within the 512-token limit while preserving semantic units.
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "512"))

    # Overlap carried over from the previous chunk so context is not lost at boundaries.
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "64"))

    # JSONL file written by scraper_service. Shared via the raw_data Docker volume.
    raw_file: Path = Path(os.getenv("RAW_FILE", "data/pages.jsonl"))


settings = Settings()
