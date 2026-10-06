"""Tests for the briefing builder (fake analyzers, real trust layer and policy)."""

from __future__ import annotations

import pytest

from src.config import DATA_DIR
from src.core.briefing.builder import BriefingBuilder
from src.core.briefing.models import Sufficiency
from src.core.exceptions import AIClientError
from src.core.models import InquiryCategory, LogEvent, LogInsight, Severity
from src.core.policy.loader import load_policy
from src.core.policy.models import AutonomyLevel
from src.core.trust.models import Customer
from tests.unit.core.conftest import make_analysis, make_draft, make_result


@pytest.fixture
def policy():
    return load_policy(DATA_DIR / "policy" / "policy.yaml")


def make_builder(
    kb_index, policy, *, analysis=None, draft=None, insight=None, error=None, id_factory=None
):
    analysis = analysis or make_analysis()

    def analyze(_text):
        if error:
            raise error
        return analysis

    def draft_fn(_text, _analysis):
        return draft or make_draft()

    log_fn = (lambda _raw: insight) if insight is not None else None
    return BriefingBuilder(
        analyze=analyze,
        draft=draft_fn,
        analyze_logs=log_fn,
        kb_index=kb_index,
        policy=policy,
        id_factory=id_factory or (lambda: "b-1"),
        clock=lambda: "2026-10-04T09:00:00",
    )


def feature_analysis(severity=Severity.LOW):
    analysis = make_analysis(severity=severity)
    analysis.category = InquiryCategory.FEATURE
    return analysis


def log_insight() -> LogInsight:
    error = LogEvent("2026-10-04T08:00:00", "ERROR", "SYNC-002 upload failed: quota exceeded")
    return LogInsight(
        summary="Uploads failing",
        errors=[error],
        slow_operations=[],
        anomalies=["1 error(s)"],
        timeline=[error],
        root_cause_hypothesis="Storage quota exceeded",
    )


def test_clean_feature_question_is_auto_simulated_and_sufficient(kb_index, policy):
    builder = make_builder(kb_index, policy, analysis=feature_analysis())
    b = builder.build("How do I enable auto-backup?", Customer(plan="pro"))
    assert b.id == "b-1"
    assert b.created_at == "2026-10-04T09:00:00"
    assert b.autonomy is AutonomyLevel.AUTO
    assert b.simulated is True
    assert b.draft_body is not None
    assert b.sufficiency is Sufficiency.SUFFICIENT
    assert b.verification_passed and b.verification_score == pytest.approx(1.0)
    assert b.status == "ready"


def test_human_only_briefing_omits_the_draft(kb_index, policy):
    builder = make_builder(kb_index, policy, analysis=feature_analysis())
    b = builder.build("We suspect a data breach", Customer(plan="pro"))
    assert b.autonomy is AutonomyLevel.HUMAN_ONLY
    assert b.draft_body is None
    assert any("breach" in r for r in b.autonomy_reasons)


def test_technical_issue_without_logs_is_insufficient(kb_index, policy):
    builder = make_builder(kb_index, policy)  # SYNC category
    b = builder.build("Uploads fail with SYNC-002", Customer(plan="pro"))
    assert b.sufficiency is Sufficiency.INSUFFICIENT
    assert any("log" in r.lower() for r in b.sufficiency_reasons)


def test_technical_issue_with_log_evidence_and_citation_is_sufficient(kb_index, policy):
    builder = make_builder(kb_index, policy, insight=log_insight())
    b = builder.build("Uploads fail with SYNC-002", Customer(plan="pro"), log_text='[{"x": 1}]')
    assert b.sufficiency is Sufficiency.SUFFICIENT
    top = b.hypotheses[0]
    assert top.statement == "Storage quota exceeded"
    assert top.log_evidence and "SYNC-002" in top.log_evidence[0]


def test_hypotheses_put_log_based_first_then_knowledge_based(kb_index, policy):
    builder = make_builder(kb_index, policy, insight=log_insight())
    b = builder.build("Uploads fail", Customer(plan="pro"), log_text="x")
    assert b.hypotheses[0].log_evidence
    assert b.hypotheses[-1].kb_evidence
    assert not b.hypotheses[-1].log_evidence


def test_failed_verification_makes_briefing_insufficient(kb_index, policy):
    bad = make_draft(body="See SYNC-099 and enable SSO.", citations=[])
    builder = make_builder(kb_index, policy, analysis=feature_analysis(), draft=bad)
    b = builder.build("How do I enable auto-backup?", Customer(plan="free"))
    assert b.sufficiency is Sufficiency.INSUFFICIENT
    assert any("score" in r.lower() or "citation" in r.lower() for r in b.sufficiency_reasons)


def test_severity_floor_is_applied_to_effective_severity(kb_index, policy):
    analysis = make_analysis(severity=Severity.LOW)
    builder = make_builder(kb_index, policy, analysis=analysis, insight=log_insight())
    b = builder.build("Everyone in our company cannot sync", Customer(plan="enterprise"), "x")
    assert b.model_severity is Severity.LOW
    assert b.effective_severity is Severity.HIGH


def test_citations_are_recorded_with_doc_ids(kb_index, policy):
    draft = make_draft(citations=[make_result("doc-2", "Webhooks")])
    analysis = make_analysis(articles=[make_result("doc-2", "Webhooks")])
    b = make_builder(kb_index, policy, analysis=analysis, draft=draft).build(
        "q", Customer(plan="pro")
    )
    assert [(c.doc_id, c.title) for c in b.citations] == [("doc-2", "Webhooks")]


def test_pipeline_failure_still_produces_a_fail_safe_briefing(kb_index, policy):
    builder = make_builder(kb_index, policy, error=AIClientError("api down"))
    b = builder.build("Anything", Customer(plan="pro"))
    assert b.id == "b-1"
    assert b.autonomy is AutonomyLevel.HUMAN_ONLY
    assert b.sufficiency is Sufficiency.INSUFFICIENT
    assert b.draft_body is None
    assert "api down" in b.summary
    assert b.status == "ready"


def test_log_analysis_failure_degrades_to_insufficient_not_crash(kb_index, policy):
    def boom(_raw):
        raise AIClientError("log model down")

    builder = BriefingBuilder(
        analyze=lambda _t: make_analysis(),
        draft=lambda _t, _a: make_draft(),
        analyze_logs=boom,
        kb_index=kb_index,
        policy=policy,
        id_factory=lambda: "b-1",
        clock=lambda: "t",
    )
    b = builder.build("Uploads fail", Customer(plan="pro"), log_text="x")
    assert b.sufficiency is Sufficiency.INSUFFICIENT
    assert any("log" in r.lower() for r in b.sufficiency_reasons)


def test_unexpected_exception_in_analyzer_still_yields_a_briefing(kb_index, policy):
    builder = make_builder(kb_index, policy, error=RuntimeError("chroma exploded"))
    b = builder.build("Anything", Customer(plan="pro"))
    assert b.autonomy is AutonomyLevel.HUMAN_ONLY
    assert "chroma exploded" in b.summary


def test_explicit_briefing_id_overrides_the_factory(kb_index, policy):
    b = make_builder(kb_index, policy).build("q", Customer(plan="pro"), briefing_id="fixed-1")
    assert b.id == "fixed-1"


def test_origin_is_attached_to_the_briefing(kb_index, policy):
    from src.core.briefing.models import Origin

    origin = Origin("linear", "abc", "SUP-7", "https://linear.app/x/SUP-7")
    b = make_builder(kb_index, policy).build("q", Customer(plan="pro"), origin=origin)
    assert b.origin == origin


def test_origin_survives_a_pipeline_failure(kb_index, policy):
    from src.core.briefing.models import Origin

    origin = Origin("linear", "abc", "SUP-7", "https://linear.app/x/SUP-7")
    b = make_builder(kb_index, policy, error=RuntimeError("boom")).build(
        "q", Customer(plan="pro"), origin=origin
    )
    assert b.origin == origin
