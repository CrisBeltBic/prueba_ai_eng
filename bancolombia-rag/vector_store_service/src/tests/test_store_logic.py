"""Tests for store/logic.py — search, get_by_url, list_categories, get_stats."""
# docker exec bancolombia-rag-vector_store_service-1 pytest /app/tests/ -v

from unittest.mock import MagicMock, patch

from store.logic import get_by_url, get_stats, list_categories, search

# Helpers

def _make_store(
    search_results=None,
    chunks_by_url=None,
    categories=None,
    stats=None,
) -> MagicMock:
    """Build a fake VectorStore with controllable return values."""
    store = MagicMock()
    store.search.return_value = search_results or []
    store.get_by_url.return_value = chunks_by_url or []
    store.list_categories.return_value = categories or []
    store.get_stats.return_value = stats or {}
    return store


# search

def test_search_returns_results_with_context():
    mock_store = _make_store(
        search_results=[
            {"url": "https://bancolombia.com/credito", "chunk_index": 1,
             "title": "Crédito", "category": "creditos", "score": 0.9},
        ],
        chunks_by_url=[
            {"chunk_index": 0, "text": "Bancolombia ofrece"},
            {"chunk_index": 1, "text": "crédito hipotecario"},
            {"chunk_index": 2, "text": "a 20 años plazo"},
        ],
    )
    with patch("store.logic._get_store", return_value=mock_store), \
         patch("store.logic.embed_query", return_value=[0.1, 0.2, 0.3]):
        result = search("crédito hipotecario", top_k=5, category=None)

    assert len(result) == 1
    assert "context" in result[0]
    assert "Bancolombia ofrece" in result[0]["context"]
    assert "crédito hipotecario" in result[0]["context"]
    assert "a 20 años plazo" in result[0]["context"]


def test_search_removes_text_field():
    mock_store = _make_store(
        search_results=[
            {"url": "https://bancolombia.com", "chunk_index": 0,
             "text": "raw chunk text", "score": 0.8},
        ],
    )
    with patch("store.logic._get_store", return_value=mock_store), \
         patch("store.logic.embed_query", return_value=[0.1]):
        result = search("query", top_k=1, category=None)

    assert "text" not in result[0]


def test_search_forwards_category_to_store():
    mock_store = _make_store()
    with patch("store.logic._get_store", return_value=mock_store), \
         patch("store.logic.embed_query", return_value=[0.1]):
        search("query", top_k=3, category="creditos")

    _, call_top_k, call_category = mock_store.search.call_args[0]
    assert call_top_k == 3
    assert call_category == "creditos"


def test_search_returns_empty_list_when_no_results():
    mock_store = _make_store(search_results=[])
    with patch("store.logic._get_store", return_value=mock_store), \
         patch("store.logic.embed_query", return_value=[0.1]):
        result = search("nada", top_k=5, category=None)

    assert result == []


# get_by_url

def test_get_by_url_returns_chunks():
    chunks = [
        {"chunk_index": 0, "text": "primer chunk"},
        {"chunk_index": 1, "text": "segundo chunk"},
    ]
    mock_store = _make_store(chunks_by_url=chunks)
    with patch("store.logic._get_store", return_value=mock_store):
        result = get_by_url("https://bancolombia.com/credito")

    assert len(result) == 2
    assert result[0]["text"] == "primer chunk"


def test_get_by_url_returns_empty_for_unknown_url():
    mock_store = _make_store(chunks_by_url=[])
    with patch("store.logic._get_store", return_value=mock_store):
        result = get_by_url("https://bancolombia.com/no-existe")

    assert result == []


# list_categories

def test_list_categories_returns_all_categories():
    mock_store = _make_store(categories=["creditos", "cuentas", "seguros"])
    with patch("store.logic._get_store", return_value=mock_store):
        result = list_categories()

    assert "creditos" in result
    assert "cuentas" in result
    assert len(result) == 3


def test_list_categories_returns_empty_when_none_indexed():
    mock_store = _make_store(categories=[])
    with patch("store.logic._get_store", return_value=mock_store):
        result = list_categories()

    assert result == []


# get_stats

def test_get_stats_returns_store_stats():
    stats = {"total_chunks": 500, "categories": 5, "embedding_model": "paraphrase-multilingual"}
    mock_store = _make_store(stats=stats)
    with patch("store.logic._get_store", return_value=mock_store):
        result = get_stats()

    assert result["total_chunks"] == 500
    assert result["embedding_model"] == "paraphrase-multilingual"
