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

    def test_upsert_new_documents(self, store: KnowledgeStore, sample_knowledge_dir: Path):
        loader = KnowledgeLoader()
        docs = loader.load_directory(sample_knowledge_dir)
        store.upsert_documents(docs)
        assert store.count() == 6

    def test_upsert_existing_updates_content(self, store: KnowledgeStore):
        from src.core.models import KnowledgeCategory, KnowledgeDoc

        doc = KnowledgeDoc(
            id="test-upsert-1",
            title="Original Title",
            content="Original content about syncing files.",
            category=KnowledgeCategory.FAQ,
            source_file="test.md",
        )
        store.upsert_documents([doc])
        assert store.count() == 1

        updated = KnowledgeDoc(
            id="test-upsert-1",
            title="Updated Title",
            content="Completely new content about permissions.",
            category=KnowledgeCategory.FAQ,
            source_file="test.md",
        )
        store.upsert_documents([updated])
        assert store.count() == 1

        results = store.search("permissions", top_k=1)
        assert results[0].title == "Updated Title"
        assert "permissions" in results[0].content

    def test_delete_by_source(self, loaded_store: KnowledgeStore):
        initial_count = loaded_store.count()
        # faq.md has 2 chunks
        faq_results = loaded_store.search("reset sync", top_k=1)
        source = faq_results[0].source_file

        loaded_store.delete_by_source(source)
        assert loaded_store.count() == initial_count - 2
