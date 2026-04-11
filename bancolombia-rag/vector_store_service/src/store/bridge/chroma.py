from chromadb import HttpClient

from config import settings


class ChromaAdapter:
    """ChromaDB implementation of the VectorStore interface."""

    def __init__(self) -> None:
        self._client = HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        self._collection = self._client.get_or_create_collection(
            "knowledge",
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, chunks: list[dict]) -> None:
        self._collection.upsert(
            ids=[c["chunk_id"] for c in chunks],
            embeddings=[c["embedding"] for c in chunks],
            documents=[c["text"] for c in chunks],
            metadatas=[
                {
                    "url": c["url"],
                    "title": c["title"],
                    "category": c["category"],
                    "chunk_index": c["chunk_index"],
                    "total_chunks": c["total_chunks"],
                    "scraped_at": c["scraped_at"],
                }
                for c in chunks
            ],
        )

    def search(self, embedding: list[float], top_k: int, category: str | None) -> list[dict]:
        where = {"category": category} if category else None
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        return [
            {
                "chunk_id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "url": results["metadatas"][0][i]["url"],
                "title": results["metadatas"][0][i]["title"],
                "category": results["metadatas"][0][i]["category"],
                "chunk_index": results["metadatas"][0][i]["chunk_index"],
                "score": 1 - results["distances"][0][i],
            }
            for i in range(len(results["ids"][0]))
        ]

    def get_by_url(self, url: str) -> list[dict]:
        results = self._collection.get(where={"url": url}, include=["documents", "metadatas"])
        return [
            {
                "chunk_id": results["ids"][i],
                "text": results["documents"][i],
                **results["metadatas"][i],
            }
            for i in range(len(results["ids"]))
        ]

    def list_categories(self) -> list[str]:
        results = self._collection.get(include=["metadatas"])
        return list({m["category"] for m in results["metadatas"] if "category" in m})

    def get_stats(self) -> dict:
        results = self._collection.get(include=["metadatas"])
        categories = list({m.get("category", "") for m in results["metadatas"]})
        return {
            "total_chunks": self._collection.count(),
            "categories": categories,
            "embedding_model": settings.embedding_model,
        }
