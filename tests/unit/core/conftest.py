"""Shared builders for trust layer tests."""

from __future__ import annotations

import pytest

from src.core.models import (
    DraftResponse,
    InquiryCategory,
    InquiryResult,
    SearchResult,
    Severity,
)
from src.core.trust.kb_index import KnowledgeIndex
from src.core.trust.models import Customer, TrustInput


def make_result(doc_id: str = "doc-1", title: str = "SYNC-002: Upload Failed") -> SearchResult:
    return SearchResult(
        doc_id=doc_id,
        title=title,
        content="content",
        category="error_code",
        score=0.9,
        source_file="error_codes.md",
    )


def make_analysis(
    severity: Severity = Severity.MEDIUM,
    articles: list[SearchResult] | None = None,
) -> InquiryResult:
    return InquiryResult(
        category=InquiryCategory.SYNC,
        severity=severity,
        summary="Uploads failing",
        checklist=["Check quota"],
        follow_up_questions=[],
        relevant_articles=articles if articles is not None else [make_result()],
        confidence=0.8,
    )


def make_draft(
    body: str = "Please check your storage quota (SYNC-002).",
    citations: list[SearchResult] | None = None,
) -> DraftResponse:
    return DraftResponse(
        body=body,
        citations=citations if citations is not None else [make_result()],
        confidence=0.95,
        needs_escalation=False,
        suggested_internal_note="",
    )


@pytest.fixture
def kb_index() -> KnowledgeIndex:
    return KnowledgeIndex(
        doc_ids=frozenset({"doc-1", "doc-2"}),
        error_codes=frozenset({"SYNC-001", "SYNC-002", "AUTH-001", "API-002"}),
    )


@pytest.fixture
def make_input(kb_index: KnowledgeIndex):
    def _make(
        *,
        inquiry_text: str = "Uploads fail with SYNC-002",
        analysis: InquiryResult | None = None,
        draft: DraftResponse | None = None,
        plan: str = "pro",
        log_text: str = "",
        process_state=None,
        with_draft: bool = True,
    ) -> TrustInput:
        return TrustInput(
            inquiry_text=inquiry_text,
            analysis=analysis or make_analysis(),
            draft=(draft or make_draft()) if with_draft else None,
            kb_index=kb_index,
            customer=Customer(plan=plan),
            log_text=log_text,
            process_state=process_state,
        )

    return _make
