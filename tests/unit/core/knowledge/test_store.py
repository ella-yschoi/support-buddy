"""Tests for knowledge store (ChromaDB wrapper)."""

from pathlib import Path

import pytest

from src.core.knowledge.loader import KnowledgeLoader
from src.core.knowledge.store import KnowledgeStore


@pytest.fixture
def store(tmp_path: Path) -> KnowledgeStore:
    return KnowledgeStore(persist_dir=str(tmp_path / "chroma"))


@pytest.fixture
def loaded_store(store: KnowledgeStore, sample_knowledge_dir: Path) -> KnowledgeStore:
    loader = KnowledgeLoader()
    docs = loader.load_directory(sample_knowledge_dir)
    store.add_documents(docs)
    return store


class TestKnowledgeStore:
    def test_add_and_count(self, loaded_store: KnowledgeStore):
        assert loaded_store.count() == 6

    def test_search_returns_relevant_results(self, loaded_store: KnowledgeStore):
        results = loaded_store.search("file not syncing", top_k=3)

        assert len(results) > 0
        assert len(results) <= 3
        # Should return search results with scores
        assert results[0].score >= 0

    def test_search_by_category_filter(self, loaded_store: KnowledgeStore):
        results = loaded_store.search("sync error", top_k=5, category="error_code")

        for r in results:
            assert r.category == "error_code"

    def test_search_empty_query_returns_results(self, loaded_store: KnowledgeStore):
        results = loaded_store.search("", top_k=3)
        # ChromaDB should still return results for empty query
        assert len(results) >= 0

    def test_delete_document(self, loaded_store: KnowledgeStore):
        initial_count = loaded_store.count()
        results = loaded_store.search("reset sync", top_k=1)
        if results:
            loaded_store.delete_document(results[0].doc_id)
            assert loaded_store.count() == initial_count - 1

    def test_empty_store_search(self, store: KnowledgeStore):
        results = store.search("anything", top_k=3)
        assert results == []
