"""Knowledge Engine — orchestrates loading, storing, and searching knowledge."""

from __future__ import annotations

from pathlib import Path

from src.core.knowledge.loader import KnowledgeLoader
from src.core.knowledge.store import KnowledgeStore
from src.core.models import SearchResult


class KnowledgeEngine:
    """Main entry point for knowledge base operations."""

    def __init__(self, persist_dir: str | None = None):
        self._loader = KnowledgeLoader()
        self._store = KnowledgeStore(persist_dir=persist_dir)

    def ingest_directory(self, dir_path: str | Path) -> int:
        """Load all Markdown files from a directory into the knowledge store.

        Returns the number of document chunks ingested.
        """
        docs = self._loader.load_directory(Path(dir_path))
        self._store.add_documents(docs)
        return len(docs)

    def ingest_file(self, file_path: str | Path) -> int:
        """Load a single file into the knowledge store.

        Returns the number of document chunks ingested.
        """
        docs = self._loader.load_file(Path(file_path))
        self._store.add_documents(docs)
        return len(docs)

    def search(
        self, query: str, top_k: int = 5, category: str | None = None
    ) -> list[SearchResult]:
        """Search the knowledge base."""
        return self._store.search(query, top_k=top_k, category=category)

    def doc_count(self) -> int:
        return self._store.count()

    def reset(self) -> None:
        self._store.reset()
