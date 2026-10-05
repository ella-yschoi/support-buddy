"""Shared helpers for eval tests."""

from __future__ import annotations

import pytest

from src.config import DATA_DIR
from src.core.models import (
    DraftResponse,
    InquiryCategory,
    InquiryResult,
    SearchResult,
    Severity,
)
from src.core.policy.loader import load_policy
from src.core.policy.models import AutonomyLevel, Policy
from src.core.trust.kb_index import KnowledgeIndex
from src.core.trust.models import Customer
from src.eval.cases import Expected, GoldenCase


def article(doc_id: str = "doc-1", title: str = "SYNC-002: Upload Failed") -> SearchResult:
    return SearchResult(doc_id, title, "content", "error_code", 0.9, "error_codes.md")


def analysis(
    category: InquiryCategory = InquiryCategory.FEATURE,
    severity: Severity = Severity.LOW,
    articles: list[SearchResult] | None = None,
) -> InquiryResult:
    return InquiryResult(
        category=category,
        severity=severity,
        summary="s",
        checklist=["c"],
        follow_up_questions=[],
        relevant_articles=articles if articles is not None else [article()],
        confidence=0.9,
    )


def draft(body: str = "Here is how to do it.", citations=None) -> DraftResponse:
    return DraftResponse(
        body=body,
        citations=citations if citations is not None else [article()],
        confidence=0.9,
        needs_escalation=False,
        suggested_internal_note="",
    )


def golden_case(
    case_id: str = "case-1",
    inquiry: str = "How do I enable auto-backup?",
    plan: str = "pro",
    category: InquiryCategory = InquiryCategory.FEATURE,
    min_severity: Severity = Severity.LOW,
    autonomy: AutonomyLevel = AutonomyLevel.AUTO,
    log_text: str = "",
    must_cite: tuple[str, ...] = (),
    must_not_say: tuple[str, ...] = (),
) -> GoldenCase:
    return GoldenCase(
        id=case_id,
        inquiry=inquiry,
        customer=Customer(plan=plan),
        expected=Expected(category, min_severity, autonomy, must_cite, must_not_say),
        log_text=log_text,
    )


@pytest.fixture
def kb_index() -> KnowledgeIndex:
    return KnowledgeIndex(
        doc_ids=frozenset({"doc-1", "doc-2"}),
        error_codes=frozenset({"SYNC-002", "API-002"}),
    )


@pytest.fixture
def policy() -> Policy:
    return load_policy(DATA_DIR / "policy" / "policy.yaml")
