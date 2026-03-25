"""ChromaDB-backed knowledge store for semantic search."""

from __future__ import annotations

import chromadb
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

from src.core.models import KnowledgeDoc, SearchResult


class KnowledgeStore:
    """Vector store for knowledge documents using ChromaDB."""

    COLLECTION_NAME = "support_knowledge"

    def __init__(self, persist_dir: str | None = None):
        if persist_dir:
            self._client = chromadb.PersistentClient(path=persist_dir)
        else:
            self._client = chromadb.EphemeralClient()

        # Force CPU-only to avoid CoreML crashes on macOS
        self._ef = ONNXMiniLM_L6_V2(preferred_providers=["CPUExecutionProvider"])
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
            embedding_function=self._ef,
        )

    def add_documents(self, docs: list[KnowledgeDoc]) -> None:
        if not docs:
            return

        self._collection.add(
            ids=[d.id for d in docs],
            documents=[d.content for d in docs],
            metadatas=[
                {
                    "title": d.title,
                    "category": d.category.value,
                    "source_file": d.source_file,
                    "parent_title": d.metadata.get("parent_title", ""),
                }
                for d in docs
            ],
        )

    def search(
        self, query: str, top_k: int = 5, category: str | None = None
    ) -> list[SearchResult]:
        if self._collection.count() == 0:
            return []

        where_filter = {"category": category} if category else None
        top_k = min(top_k, self._collection.count())

        results = self._collection.query(
            query_texts=[query] if query else [""],
            n_results=top_k,
            where=where_filter,
        )

        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0.0
                score = 1.0 - distance  # cosine distance → similarity

                search_results.append(
                    SearchResult(
                        doc_id=doc_id,
                        title=meta.get("title", ""),
                        content=results["documents"][0][i] if results["documents"] else "",
                        category=meta.get("category", ""),
                        score=score,
                        source_file=meta.get("source_file", ""),
                    )
                )

        return search_results

    def upsert_documents(self, docs: list[KnowledgeDoc]) -> None:
        if not docs:
            return

        self._collection.upsert(
            ids=[d.id for d in docs],
            documents=[d.content for d in docs],
            metadatas=[
                {
                    "title": d.title,
                    "category": d.category.value,
                    "source_file": d.source_file,
                    "parent_title": d.metadata.get("parent_title", ""),
                }
                for d in docs
            ],
        )

    def delete_by_source(self, source_file: str) -> None:
        self._collection.delete(where={"source_file": source_file})

    def delete_document(self, doc_id: str) -> None:
        self._collection.delete(ids=[doc_id])

    def count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        self._client.delete_collection(self.COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
