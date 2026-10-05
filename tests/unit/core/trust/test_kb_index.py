"""Tests for the knowledge index builder."""

from __future__ import annotations

from src.core.models import KnowledgeCategory, KnowledgeDoc
from src.core.trust.kb_index import build_kb_index


def _doc(doc_id: str, title: str, category: KnowledgeCategory) -> KnowledgeDoc:
    return KnowledgeDoc(id=doc_id, title=title, content="", category=category, source_file="x.md")


def test_build_index_collects_ids_and_error_codes():
    docs = [
        _doc("a", "SYNC-001: File Conflict", KnowledgeCategory.ERROR_CODE),
        _doc("b", "AUTH-002: Token expired", KnowledgeCategory.ERROR_CODE),
        _doc("c", "How do I reset sync?", KnowledgeCategory.FAQ),
    ]
    index = build_kb_index(docs)
    assert index.doc_ids == frozenset({"a", "b", "c"})
    assert index.error_codes == frozenset({"SYNC-001", "AUTH-002"})
    assert index.error_prefixes == frozenset({"SYNC", "AUTH"})


def test_non_error_docs_mentioning_codes_are_not_definitions():
    docs = [_doc("c", "Troubleshooting SYNC-009 loops", KnowledgeCategory.TROUBLESHOOTING)]
    assert build_kb_index(docs).error_codes == frozenset()


def test_empty_docs_gives_empty_index():
    index = build_kb_index([])
    assert index.doc_ids == frozenset()
    assert index.error_codes == frozenset()


def test_real_knowledge_base_defines_known_codes():
    from src.config import KNOWLEDGE_DIR
    from src.core.knowledge.loader import KnowledgeLoader

    index = build_kb_index(KnowledgeLoader().load_directory(KNOWLEDGE_DIR))
    assert {"SYNC-001", "SYNC-002", "API-002"} <= index.error_codes


def test_title_defining_several_codes_indexes_all_of_them():
    docs = [_doc("a", "SYNC-001 / SYNC-002: Upload problems", KnowledgeCategory.ERROR_CODE)]
    assert build_kb_index(docs).error_codes == frozenset({"SYNC-001", "SYNC-002"})
