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
