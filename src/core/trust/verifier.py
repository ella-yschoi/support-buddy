"""Run all deterministic checks and build a VerificationReport."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence

from src.core.trust import checks as default_checks
from src.core.trust.models import Check, FailEffect, TrustInput, VerificationReport
from src.core.trust.rules import SEVERITY_ORDER

logger = logging.getLogger(__name__)

CheckFn = Callable[[TrustInput], Check]

# A check that cannot run is treated as a failure, never a pass.
_CHECK_ERRORS = (ValueError, KeyError, TypeError, AttributeError, IndexError)


class Verifier:
    """Deterministic gate for AI output. Never calls an LLM."""

    def __init__(self, check_fns: Sequence[CheckFn] | None = None):
        self._check_fns = tuple(check_fns) if check_fns is not None else default_checks.ALL_CHECKS

    def verify(self, inp: TrustInput) -> VerificationReport:
        results = tuple(self._run(fn, inp) for fn in self._check_fns)

        total = sum(c.weight for c in results)
        passed_weight = sum(c.weight for c in results if c.passed)
        score = passed_weight / total if total else 1.0

        effects = frozenset(
            c.on_fail for c in results if not c.passed and c.on_fail is not FailEffect.NONE
        )
        floors = [c.floor for c in results if c.floor is not None]
        floor = max(floors, key=SEVERITY_ORDER.index) if floors else None
        effective = inp.analysis.severity
        if floor is not None and SEVERITY_ORDER.index(floor) > SEVERITY_ORDER.index(effective):
            effective = floor

        return VerificationReport(
            checks=results,
            passed=all(c.passed for c in results),
            score=score,
            effects=effects,
            severity_floor=floor,
            effective_severity=effective,
        )

    @staticmethod
    def _run(fn: CheckFn, inp: TrustInput) -> Check:
        try:
            return fn(inp)
        except _CHECK_ERRORS as exc:
            logger.error("trust check %s failed to run", fn.__name__, exc_info=True)
            return Check(
                fn.__name__, False, 1.0, f"check error: {exc}", FailEffect.FORCE_HUMAN_ONLY
            )
