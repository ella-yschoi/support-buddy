"""Tests for the eval runner (fake pipelines, real trust layer and policy)."""

from __future__ import annotations

from src.core.exceptions import AIClientError
from src.core.models import InquiryCategory, Severity
from src.core.policy.models import AutonomyLevel
from src.eval.models import Usage
from src.eval.pipeline import PipelineOutput
from src.eval.runner import EvalRunner
from tests.unit.eval.conftest import analysis, article, draft, golden_case


class FakePipeline:
    def __init__(self, output=None, error=None):
        self._output = output
        self._error = error

    def run(self, case):
        if self._error:
            raise self._error
        return self._output


def run_one(pipeline, case, kb_index, policy):
    return EvalRunner(pipeline, kb_index, policy).run([case])[0]


def test_clean_low_risk_feature_case_is_auto(kb_index, policy):
    out = PipelineOutput(analysis(), draft(), Usage(input_tokens=10, output_tokens=5, cost_usd=0.1))
    result = run_one(FakePipeline(out), golden_case(), kb_index, policy)
    assert result.autonomy is AutonomyLevel.AUTO
    assert result.verification_passed
    assert result.predicted_category is InquiryCategory.FEATURE
    assert result.has_draft
    assert result.cited_titles == ("SYNC-002: Upload Failed",)
    assert result.citations_valid
    assert result.error is None
    assert result.usage.input_tokens == 10
    assert result.usage.cost_usd == 0.1


def test_runner_measures_wall_clock_latency(kb_index, policy):
    out = PipelineOutput(analysis(), draft(), Usage())
    result = run_one(FakePipeline(out), golden_case(), kb_index, policy)
    assert result.usage.latency_s >= 0.0


def test_pipeline_error_is_recorded_and_fails_safe(kb_index, policy):
    result = run_one(FakePipeline(error=AIClientError("down")), golden_case(), kb_index, policy)
    assert result.error and "down" in result.error
    assert result.autonomy is AutonomyLevel.HUMAN_ONLY
    assert not result.has_draft
    assert not result.verification_passed


def test_trust_layer_raises_effective_severity(kb_index, policy):
    case = golden_case(
        inquiry="Everyone in our company cannot sync",
        plan="enterprise",
        category=InquiryCategory.SYNC,
        min_severity=Severity.HIGH,
        autonomy=AutonomyLevel.CONFIRM,
    )
    out = PipelineOutput(analysis(InquiryCategory.SYNC, Severity.LOW), draft(), Usage())
    result = run_one(FakePipeline(out), case, kb_index, policy)
    assert result.model_severity is Severity.LOW
    assert result.effective_severity is Severity.HIGH
    assert "severity_floor" in result.failed_checks


def test_log_values_leaked_into_draft_are_caught(kb_index, policy):
    case = golden_case(log_text="client 203.0.113.9 failed")
    out = PipelineOutput(analysis(), draft(body="The IP 203.0.113.9 was blocked."), Usage())
    result = run_one(FakePipeline(out), case, kb_index, policy)
    assert "pii_leak" in result.failed_checks
    assert result.autonomy is not AutonomyLevel.AUTO


def test_uncited_hallucinated_draft_is_not_auto(kb_index, policy):
    out = PipelineOutput(analysis(), draft(body="See SYNC-099.", citations=[]), Usage())
    result = run_one(FakePipeline(out), golden_case(), kb_index, policy)
    assert not result.citations_valid
    assert result.autonomy is not AutonomyLevel.AUTO


def test_run_returns_one_result_per_case_in_order(kb_index, policy):
    out = PipelineOutput(analysis(), draft(), Usage())
    cases = [golden_case("a"), golden_case("b"), golden_case("c")]
    results = EvalRunner(FakePipeline(out), kb_index, policy).run(cases)
    assert [r.case_id for r in results] == ["a", "b", "c"]
    assert article().doc_id == "doc-1"
