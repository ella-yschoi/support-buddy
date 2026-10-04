"""Tests for pure eval metric functions."""

from __future__ import annotations

import pytest

from src.core.models import InquiryCategory, Severity
from src.core.policy.models import AutonomyLevel
from src.eval.cases import Expected
from src.eval.metrics import compute_metrics
from src.eval.models import CaseResult, Usage
from src.eval.pricing import estimate_cost


def result(
    *,
    case_id: str = "c",
    exp_category: InquiryCategory = InquiryCategory.SYNC,
    exp_severity: Severity = Severity.MEDIUM,
    exp_autonomy: AutonomyLevel = AutonomyLevel.CONFIRM,
    must_cite: tuple[str, ...] = (),
    must_not_say: tuple[str, ...] = (),
    category: InquiryCategory = InquiryCategory.SYNC,
    model_severity: Severity = Severity.MEDIUM,
    effective_severity: Severity | None = None,
    autonomy: AutonomyLevel = AutonomyLevel.CONFIRM,
    passed: bool = True,
    cited_titles: tuple[str, ...] = (),
    citations_valid: bool = True,
    body: str = "ok",
    has_draft: bool = True,
    usage: Usage | None = None,
    error: str | None = None,
) -> CaseResult:
    return CaseResult(
        case_id=case_id,
        expected=Expected(exp_category, exp_severity, exp_autonomy, must_cite, must_not_say),
        predicted_category=category,
        model_severity=model_severity,
        effective_severity=effective_severity or model_severity,
        autonomy=autonomy,
        verification_passed=passed,
        verification_score=1.0 if passed else 0.5,
        failed_checks=() if passed else ("x",),
        cited_titles=cited_titles,
        citations_valid=citations_valid,
        has_draft=has_draft,
        draft_body=body,
        usage=usage or Usage(),
        error=error,
    )


def test_empty_results_give_zeroed_metrics():
    m = compute_metrics([])
    assert m.n == 0
    assert m.category_accuracy == 0.0


def test_category_accuracy():
    m = compute_metrics([result(), result(category=InquiryCategory.API), result(), result()])
    assert m.category_accuracy == pytest.approx(0.75)


def test_severity_under_triage_uses_model_severity():
    m = compute_metrics(
        [
            result(exp_severity=Severity.HIGH, model_severity=Severity.LOW),
            result(exp_severity=Severity.HIGH, model_severity=Severity.CRITICAL),
        ]
    )
    assert m.severity_under_triage_rate == pytest.approx(0.5)


def test_effective_under_triage_shows_trust_layer_correction():
    m = compute_metrics(
        [
            result(
                exp_severity=Severity.HIGH,
                model_severity=Severity.LOW,
                effective_severity=Severity.HIGH,
            )
        ]
    )
    assert m.severity_under_triage_rate == 1.0
    assert m.effective_under_triage_rate == 0.0


def test_citation_validity_counts_only_cases_with_a_draft():
    m = compute_metrics(
        [
            result(citations_valid=True),
            result(citations_valid=False),
            result(has_draft=False, citations_valid=False),
        ]
    )
    assert m.citation_validity == pytest.approx(0.5)


def test_must_cite_rate_matches_substrings_case_insensitively():
    m = compute_metrics(
        [
            result(must_cite=("SYNC-002",), cited_titles=("sync-002: Upload Failed",)),
            result(must_cite=("SYNC-002",), cited_titles=("Other",)),
            result(),  # no must_cite: excluded
        ]
    )
    assert m.must_cite_rate == pytest.approx(0.5)


def test_must_not_say_violation_rate():
    m = compute_metrics(
        [
            result(must_not_say=("guarantee",), body="We Guarantee it"),
            result(must_not_say=("guarantee",), body="We will look into it"),
        ]
    )
    assert m.must_not_say_violation_rate == pytest.approx(0.5)


def test_routing_agreement():
    m = compute_metrics(
        [
            result(autonomy=AutonomyLevel.CONFIRM, exp_autonomy=AutonomyLevel.CONFIRM),
            result(autonomy=AutonomyLevel.AUTO, exp_autonomy=AutonomyLevel.CONFIRM),
        ]
    )
    assert m.routing_agreement == pytest.approx(0.5)


def test_auto_resolvable_requires_passed_checks_and_non_human_level():
    m = compute_metrics(
        [
            result(autonomy=AutonomyLevel.AUTO, passed=True),
            result(autonomy=AutonomyLevel.CONFIRM, passed=True),
            result(autonomy=AutonomyLevel.CONFIRM, passed=False),
            result(autonomy=AutonomyLevel.HUMAN_ONLY, passed=True),
        ]
    )
    assert m.auto_resolvable_rate == pytest.approx(0.5)


def test_auto_resolvable_in_scope_excludes_expected_human_only_cases():
    m = compute_metrics(
        [
            result(autonomy=AutonomyLevel.CONFIRM),
            result(exp_autonomy=AutonomyLevel.HUMAN_ONLY, autonomy=AutonomyLevel.HUMAN_ONLY),
        ]
    )
    assert m.auto_resolvable_rate == pytest.approx(0.5)
    assert m.auto_resolvable_in_scope_rate == pytest.approx(1.0)


def test_unsafe_pass_counts_human_only_cases_routed_lower():
    m = compute_metrics(
        [
            result(exp_autonomy=AutonomyLevel.HUMAN_ONLY, autonomy=AutonomyLevel.CONFIRM),
            result(exp_autonomy=AutonomyLevel.HUMAN_ONLY, autonomy=AutonomyLevel.HUMAN_ONLY),
            result(),
        ]
    )
    assert m.unsafe_pass_count == 1
    assert m.unsafe_pass_rate == pytest.approx(0.5)


def test_unsafe_pass_rate_zero_when_no_human_only_cases():
    assert compute_metrics([result()]).unsafe_pass_rate == 0.0


def test_errored_cases_are_excluded_from_rates_not_counted_as_safe():
    ok = result(exp_autonomy=AutonomyLevel.HUMAN_ONLY, autonomy=AutonomyLevel.HUMAN_ONLY)
    failed = result(
        exp_autonomy=AutonomyLevel.HUMAN_ONLY,
        autonomy=AutonomyLevel.HUMAN_ONLY,
        category=InquiryCategory.UNKNOWN,
        error="api down",
    )
    m = compute_metrics([ok, failed])
    assert m.n == 2
    assert m.n_scored == 1
    assert m.error_count == 1
    assert m.category_accuracy == pytest.approx(1.0)  # would be 0.5 if the error counted


def test_all_cases_errored_yields_zero_scored_and_no_safe_claims():
    m = compute_metrics([result(error="x"), result(error="y")])
    assert m.n_scored == 0
    assert m.routing_agreement == 0.0
    assert m.unsafe_pass_rate == 0.0
    assert m.error_count == 2


def test_auto_rate_counts_only_auto_routing_with_passed_checks():
    m = compute_metrics(
        [
            result(autonomy=AutonomyLevel.AUTO, passed=True),
            result(autonomy=AutonomyLevel.CONFIRM, passed=True),
        ]
    )
    assert m.auto_rate == pytest.approx(0.5)
    assert m.auto_resolvable_rate == pytest.approx(1.0)


def test_errors_are_counted_and_cost_latency_aggregated():
    m = compute_metrics(
        [
            result(usage=Usage(input_tokens=100, output_tokens=50, latency_s=1.0, cost_usd=0.01)),
            result(
                usage=Usage(input_tokens=300, output_tokens=150, latency_s=3.0, cost_usd=0.03),
                error="boom",
            ),
        ]
    )
    assert m.error_count == 1
    assert m.total_input_tokens == 400
    assert m.total_output_tokens == 200
    assert m.total_cost_usd == pytest.approx(0.04)
    assert m.mean_latency_s == pytest.approx(2.0)


class TestPricing:
    def test_known_model_cost(self):
        # Sonnet 5.5: $2 / $10 per MTok
        assert estimate_cost("claude-sonnet-5-5", 1_000_000, 100_000) == pytest.approx(3.0)

    def test_haiku_cost(self):
        # Haiku 4.5: $1 / $5 per MTok
        assert estimate_cost("claude-haiku-4-5-20251001", 2_000_000, 0) == pytest.approx(2.0)

    def test_unknown_model_returns_none(self):
        assert estimate_cost("mystery-model", 1000, 1000) is None
