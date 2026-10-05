"""Deterministic autonomy routing. First matching rule wins, most restrictive first."""

from __future__ import annotations

import logging
import re

from src.core.models import Severity
from src.core.policy.models import AutonomyLevel, Decision, Policy
from src.core.trust.models import FailEffect, TrustInput, VerificationReport
from src.core.trust.rules import SEVERITY_ORDER

logger = logging.getLogger(__name__)

_ROUTING_ERRORS = (TypeError, AttributeError, KeyError, ValueError, IndexError)


def _at_least(value: Severity, threshold: Severity) -> bool:
    return SEVERITY_ORDER.index(value) >= SEVERITY_ORDER.index(threshold)


class PolicyEngine:
    """Maps analysis + verification to Auto / Confirm / Human-only. No LLM involved."""

    def __init__(self, policy: Policy):
        self._policy = policy

    def route(self, inp: TrustInput, report: VerificationReport) -> Decision:
        try:
            return self._route(inp, report)
        except _ROUTING_ERRORS:
            logger.error("policy routing failed; failing safe", exc_info=True)
            return Decision(AutonomyLevel.HUMAN_ONLY, ("Fail-safe: routing error",))

    def _route(self, inp: TrustInput, report: VerificationReport) -> Decision:
        human = self._human_only_reasons(inp, report)
        if human:
            return Decision(AutonomyLevel.HUMAN_ONLY, tuple(human))

        confirm = self._confirm_reasons(inp, report)
        if confirm:
            return Decision(AutonomyLevel.CONFIRM, tuple(confirm))

        return Decision(
            AutonomyLevel.AUTO,
            (
                f"Category '{inp.analysis.category.value}' is allowed to auto-resolve",
                f"All checks passed (score {report.score:.2f})",
                f"Severity {report.effective_severity.value} within auto limit",
            ),
            simulated=not self._policy.auto_send_enabled,
        )

    def _human_only_reasons(self, inp: TrustInput, report: VerificationReport) -> list[str]:
        p = self._policy
        reasons: list[str] = []

        hits = [
            k
            for k in p.human_only_keywords
            if re.search(rf"\b{re.escape(k)}\b", inp.inquiry_text, re.I)
        ]
        if hits:
            reasons.append(f"Sensitive topic in message: {', '.join(hits)}")
        if inp.analysis.category in p.human_only_categories:
            reasons.append(f"Category '{inp.analysis.category.value}' requires a human")
        if _at_least(report.effective_severity, p.human_only_min_severity):
            reasons.append(f"Severity {report.effective_severity.value}")
        if FailEffect.FORCE_HUMAN_ONLY in report.effects:
            failed = [
                c.name
                for c in report.checks
                if c.on_fail is FailEffect.FORCE_HUMAN_ONLY and not c.passed
            ]
            reasons.append(f"Check failed: {', '.join(failed)}")
        if inp.draft is None:
            reasons.append("No draft available")
        if report.score < p.human_only_score_below:
            reasons.append(
                f"Verification score {report.score:.2f} below {p.human_only_score_below}"
            )
        return reasons

    def _confirm_reasons(self, inp: TrustInput, report: VerificationReport) -> list[str]:
        p = self._policy
        reasons: list[str] = []

        if inp.customer.plan.lower() in p.confirm_plans:
            reasons.append(f"{inp.customer.plan.capitalize()} customer")
        if _at_least(report.effective_severity, p.confirm_min_severity):
            reasons.append(f"Severity {report.effective_severity.value}")
        gating = {FailEffect.BLOCK_AUTO, FailEffect.FORCE_CONFIRM}
        failed = [c.name for c in report.checks if not c.passed and c.on_fail in gating]
        if failed:
            reasons.append(f"Check failed: {', '.join(failed)}")
        if inp.analysis.category not in p.auto_categories:
            reasons.append(f"Category '{inp.analysis.category.value}' is not auto-eligible")
        if SEVERITY_ORDER.index(report.effective_severity) > SEVERITY_ORDER.index(
            p.auto_max_severity
        ):
            reasons.append(f"Severity {report.effective_severity.value} above auto limit")
        if report.score < p.auto_min_score:
            reasons.append(f"Verification score {report.score:.2f} below {p.auto_min_score}")
        return reasons
