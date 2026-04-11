"""
VectorStore Protocol — the contract every database adapter must satisfy.

Adding a new backend (e.g. pgvector, Pinecone) means:
  1. Create a new file in this folder that implements this Protocol.
  2. Add a new case in store/bridge/factory.py.
  3. Set VECTOR_STORE_PROVIDER in .env.
No other code needs to change.
"""

from typing import Protocol


class VectorStore(Protocol):
    """Interface that every vector database adapter must implement."""

    def upsert(self, chunks: list[dict]) -> None:
        """Stores or updates chunks with their embeddings."""
        ...

    def search(self, embedding: list[float], top_k: int, category: str | None) -> list[dict]:
        """Returns the top_k most similar chunks to the given embedding."""
        ...

    def get_by_url(self, url: str) -> list[dict]:
        """Returns all chunks from a specific source URL."""
        ...

    def list_categories(self) -> list[str]:
        """Returns all distinct categories in the store."""
        ...

    def get_stats(self) -> dict:
        """Returns general stats: doc count, categories, last update."""
        ...
