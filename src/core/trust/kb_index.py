"""Lightweight index of what exists in the knowledge base, for existence checks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.core.models import KnowledgeDoc

ERROR_CODE_RE = re.compile(r"\b([A-Z]{2,5})-(\d{3})\b")


@dataclass(frozen=True)
class KnowledgeIndex:
    doc_ids: frozenset[str]
    error_codes: frozenset[str]

    @property
    def error_prefixes(self) -> frozenset[str]:
        return frozenset(code.split("-")[0] for code in self.error_codes)


def build_kb_index(docs: list[KnowledgeDoc]) -> KnowledgeIndex:
    """Index doc ids and the error codes defined by error-code documents."""
    codes: set[str] = set()
    for doc in docs:
        if doc.category.value != "error_code":
            continue
        codes.update(m.group(0) for m in ERROR_CODE_RE.finditer(doc.title))
    return KnowledgeIndex(doc_ids=frozenset(d.id for d in docs), error_codes=frozenset(codes))
