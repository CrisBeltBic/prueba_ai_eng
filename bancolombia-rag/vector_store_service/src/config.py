import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


class Settings:
    vector_store_provider: str = os.getenv("VECTOR_STORE_PROVIDER", "chroma")
    chroma_host: str = os.getenv("CHROMA_HOST", "localhost")
    chroma_port: int = int(os.getenv("CHROMA_PORT", "8000"))

    embedding_model: str = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-mpnet-base-v2")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "512"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "64"))

    raw_file: Path = Path(os.getenv("RAW_FILE", "data/pages.jsonl"))


settings = Settings()
