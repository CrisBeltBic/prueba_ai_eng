from config import settings
from store.bridge.base import VectorStore
from store.bridge.chroma import ChromaAdapter


def create_vector_store() -> VectorStore:
    """Returns the vector store adapter based on VECTOR_STORE_PROVIDER env var."""
    match settings.vector_store_provider:
        case "chroma":
            return ChromaAdapter()
        case _:
            raise ValueError(f"Unknown VECTOR_STORE_PROVIDER: {settings.vector_store_provider}")
