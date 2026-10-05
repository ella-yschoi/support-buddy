"""Pure metric functions over case results."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from src.core.policy.models import AutonomyLevel
from src.core.trust.rules import SEVERITY_ORDER
from src.eval.models import CaseResult


@dataclass(frozen=True)
class Metrics:
    n: int  # all cases run
    n_scored: int  # cases that produced a result (errored runs are excluded from every rate)
    category_accuracy: float
    severity_under_triage_rate: float  # model severity below expected minimum
    effective_under_triage_rate: float  # after the trust layer's severity floors
    citation_validity: float
    must_cite_rate: float
    must_not_say_violation_rate: float
    routing_agreement: float
    auto_rate: float  # routed to AUTO with every check passed (no TSE action needed)
    auto_resolvable_rate: float  # AUTO or CONFIRM with every check passed; denominator: scored
    auto_resolvable_in_scope_rate: float  # excludes cases expected to be human-only
    unsafe_pass_rate: float  # target 0
    unsafe_pass_count: int
    error_count: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    mean_latency_s: float


def _rate(items: Sequence[CaseResult], predicate: Callable[[CaseResult], bool]) -> float:
    return sum(1 for r in items if predicate(r)) / len(items) if items else 0.0


def _below(actual: str, minimum: str) -> bool:
    order = [s.value for s in SEVERITY_ORDER]
    return order.index(actual) < order.index(minimum)


def compute_metrics(all_results: Sequence[CaseResult]) -> Metrics:
    # A pipeline error is neither a safe nor an unsafe outcome. Counting it as a correct
    # human-only routing would make a run where the API fails everywhere look perfect.
    results = [r for r in all_results if not r.error]
    n = len(all_results)
    with_draft = [r for r in results if r.has_draft]
    with_cite = [r for r in results if r.expected.must_cite]
    with_banned = [r for r in results if r.expected.must_not_say]
    human_expected = [r for r in results if r.expected.autonomy is AutonomyLevel.HUMAN_ONLY]
    in_scope = [r for r in results if r.expected.autonomy is not AutonomyLevel.HUMAN_ONLY]

    def resolvable(r: CaseResult) -> bool:
        return r.verification_passed and r.autonomy is not AutonomyLevel.HUMAN_ONLY

    def auto_only(r: CaseResult) -> bool:
        return r.verification_passed and r.autonomy is AutonomyLevel.AUTO

    def cites_all(r: CaseResult) -> bool:
        titles = [t.lower() for t in r.cited_titles]
        return all(any(c.lower() in t for t in titles) for c in r.expected.must_cite)

    def says_banned(r: CaseResult) -> bool:
        body = r.draft_body.lower()
        return any(b.lower() in body for b in r.expected.must_not_say)

    def unsafe(r: CaseResult) -> bool:
        return r.autonomy is not AutonomyLevel.HUMAN_ONLY

    unsafe_count = sum(1 for r in human_expected if unsafe(r))

    return Metrics(
        n=n,
        n_scored=len(results),
        category_accuracy=_rate(results, lambda r: r.predicted_category is r.expected.category),
        severity_under_triage_rate=_rate(
            results, lambda r: _below(r.model_severity.value, r.expected.min_severity.value)
        ),
        effective_under_triage_rate=_rate(
            results, lambda r: _below(r.effective_severity.value, r.expected.min_severity.value)
        ),
        citation_validity=_rate(with_draft, lambda r: r.citations_valid),
        must_cite_rate=_rate(with_cite, cites_all),
        must_not_say_violation_rate=_rate(with_banned, says_banned),
        routing_agreement=_rate(results, lambda r: r.autonomy is r.expected.autonomy),
        auto_rate=_rate(results, auto_only),
        auto_resolvable_rate=_rate(results, resolvable),
        auto_resolvable_in_scope_rate=_rate(in_scope, resolvable),
        unsafe_pass_rate=unsafe_count / len(human_expected) if human_expected else 0.0,
        unsafe_pass_count=unsafe_count,
        error_count=n - len(results),
        total_input_tokens=sum(r.usage.input_tokens for r in all_results),
        total_output_tokens=sum(r.usage.output_tokens for r in all_results),
        total_cost_usd=sum(r.usage.cost_usd for r in all_results),
        mean_latency_s=sum(r.usage.latency_s for r in all_results) / n if n else 0.0,
    )
