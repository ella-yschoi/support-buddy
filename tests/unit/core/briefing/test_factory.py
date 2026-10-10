"""Tests for local and Claude briefing wiring and log insight."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.config import SAMPLE_LOGS_DIR
from src.core.briefing.factory import build_claude_builder, build_local_builder, local_log_insight
from src.core.briefing.models import Sufficiency
from src.core.knowledge.engine import KnowledgeEngine
from src.core.models import DraftResponse, InquiryCategory, InquiryResult, Severity
from src.core.policy.models import AutonomyLevel
from src.core.trust.models import Customer


def test_local_log_insight_extracts_errors_and_codes():
    raw = (SAMPLE_LOGS_DIR / "sync_error.json").read_text()
    insight = local_log_insight(raw)
    assert insight.errors
    assert "SYNC" in insight.root_cause_hypothesis


def test_local_log_insight_handles_empty_and_unparseable_input():
    assert local_log_insight("").errors == []
    garbage = local_log_insight("\x00\x01 not a log at all")
    assert garbage.errors == []
    assert garbage.root_cause_hypothesis


@pytest.fixture(scope="module")
def builder(tmp_path_factory):
    from src.config import KNOWLEDGE_DIR

    tmp = tmp_path_factory.mktemp("kb")
    engine = KnowledgeEngine(persist_dir=str(tmp))
    engine.ingest_directory(KNOWLEDGE_DIR)
    return build_local_builder(engine)


def test_local_builder_produces_sufficient_briefing_for_sync_case_with_logs(builder):
    raw = (SAMPLE_LOGS_DIR / "sync_error.json").read_text()
    b = builder.build(
        "My files are not syncing and I see SYNC-002", Customer(plan="free"), log_text=raw
    )
    assert b.sufficiency is Sufficiency.SUFFICIENT
    assert b.hypotheses[0].log_evidence
    assert b.autonomy is AutonomyLevel.CONFIRM


def test_local_builder_breach_is_human_only(builder):
    b = builder.build("We think there was a data breach", Customer(plan="enterprise"))
    assert b.autonomy is AutonomyLevel.HUMAN_ONLY
    assert b.draft_body is None


# ---------------------------------------------------------------------------
# Claude builder tests (mock AI components - no real API calls)
# ---------------------------------------------------------------------------

def _make_stub_analysis() -> InquiryResult:
    return InquiryResult(
        category=InquiryCategory.ACCOUNT,
        severity=Severity.LOW,
        summary="Account question",
        checklist=["Check plan", "Verify payment"],
        follow_up_questions=[],
        relevant_articles=[],
        confidence=0.9,
    )


def _make_stub_draft(analysis: InquiryResult) -> DraftResponse:
    return DraftResponse(
        body="Thank you for your question about billing.",
        citations=[],
        confidence=0.8,
        needs_escalation=False,
        suggested_internal_note="",
    )


@pytest.fixture(scope="module")
def claude_builder(tmp_path_factory):
    from src.config import KNOWLEDGE_DIR

    tmp = tmp_path_factory.mktemp("kb_claude")
    engine = KnowledgeEngine(persist_dir=str(tmp))
    engine.ingest_directory(KNOWLEDGE_DIR)

    with (
        patch("src.core.briefing.factory.AIInquiryAnalyzer") as mock_analyzer_cls,
        patch("src.core.briefing.factory.ResponseDrafter") as mock_drafter_cls,
    ):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.side_effect = lambda text: _make_stub_analysis()
        mock_analyzer_cls.return_value = mock_analyzer

        mock_drafter = MagicMock()
        mock_drafter.draft.side_effect = lambda text, analysis: _make_stub_draft(analysis)
        mock_drafter_cls.return_value = mock_drafter

        yield build_claude_builder(engine, api_key="sk-ant-test-key")


def test_claude_builder_redacts_pii_before_ai_call(tmp_path):
    """PII in the inquiry must not reach the AI analyzer."""
    from src.config import KNOWLEDGE_DIR

    engine = KnowledgeEngine(persist_dir=str(tmp_path / "kb"))
    engine.ingest_directory(KNOWLEDGE_DIR)

    received_texts: list[str] = []

    def capturing_analyze(text: str) -> InquiryResult:
        received_texts.append(text)
        return _make_stub_analysis()

    def stub_draft(text: str, analysis: InquiryResult) -> DraftResponse:
        received_texts.append(text)
        return _make_stub_draft(analysis)

    with (
        patch("src.core.briefing.factory.AIInquiryAnalyzer") as mock_analyzer_cls,
        patch("src.core.briefing.factory.ResponseDrafter") as mock_drafter_cls,
    ):
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.side_effect = capturing_analyze
        mock_analyzer_cls.return_value = mock_analyzer

        mock_drafter = MagicMock()
        mock_drafter.draft.side_effect = stub_draft
        mock_drafter_cls.return_value = mock_drafter

        builder = build_claude_builder(engine, api_key="sk-ant-test-key")
        builder.build(
            "Please help user@secret.com at IP 10.0.0.5",
            Customer(plan="pro"),
        )

    for text in received_texts:
        assert "user@secret.com" not in text, "Email leaked to AI"
        assert "10.0.0.5" not in text, "IP leaked to AI"


def test_claude_builder_returns_valid_briefing(claude_builder):
    b = claude_builder.build("I have a billing question", Customer(plan="pro"))
    assert b.id
    assert b.created_at
    assert b.category is InquiryCategory.ACCOUNT
