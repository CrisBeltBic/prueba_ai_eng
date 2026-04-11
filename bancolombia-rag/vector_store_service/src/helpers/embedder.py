from sentence_transformers import SentenceTransformer

from config import settings

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Loads the model once and reuses it (singleton)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generates embeddings for a list of texts in batch."""
    model = get_model()
    vectors = model.encode(texts, batch_size=32, show_progress_bar=False)
    return [v.tolist() for v in vectors]


def embed_query(text: str) -> list[float]:
    """Generates a single embedding for a search query."""
    return embed_texts([text])[0]
