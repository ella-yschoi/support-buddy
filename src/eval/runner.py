"""Run golden cases through a pipeline, the trust layer and the autonomy policy."""

from __future__ import annotations

import dataclasses
import logging
import time
from collections.abc import Sequence

import anthropic

from src.core.exceptions import SupportBuddyError
from src.core.models import InquiryCategory, Severity
from src.core.policy.engine import PolicyEngine
from src.core.policy.models import AutonomyLevel, Policy
from src.core.trust.kb_index import KnowledgeIndex
from src.core.trust.models import TrustInput
from src.core.trust.verifier import Verifier
from src.eval.cases import GoldenCase
from src.eval.models import CaseResult, Usage
from src.eval.pipeline import Pipeline

logger = logging.getLogger(__name__)

# Errors a pipeline may raise. Anything else is a bug and should surface.
_PIPELINE_ERRORS = (SupportBuddyError, anthropic.APIError, OSError, ValueError, KeyError, TypeError)


class EvalRunner:
    def __init__(
        self,
        pipeline: Pipeline,
        kb_index: KnowledgeIndex,
        policy: Policy,
        verifier: Verifier | None = None,
    ):
        self._pipeline = pipeline
        self._kb_index = kb_index
        self._engine = PolicyEngine(policy)
        self._verifier = verifier or Verifier()

    def run(self, cases: Sequence[GoldenCase]) -> list[CaseResult]:
        return [self._run_case(case) for case in cases]

    def _run_case(self, case: GoldenCase) -> CaseResult:
        started = time.perf_counter()
        try:
            output = self._pipeline.run(case)
        except _PIPELINE_ERRORS as exc:
            logger.error("pipeline failed on case %s", case.id, exc_info=True)
            return self._error_result(case, f"{type(exc).__name__}: {exc}")
        latency = time.perf_counter() - started

        inp = TrustInput(
            inquiry_text=case.inquiry,
            analysis=output.analysis,
            draft=output.draft,
            kb_index=self._kb_index,
            customer=case.customer,
            log_text=case.log_text,
        )
        report = self._verifier.verify(inp)
        decision = self._engine.route(inp, report)

        by_name = {c.name: c for c in report.checks}
        citations_valid = all(
            name in by_name and by_name[name].passed
            for name in ("citations_exist", "citations_retrieved")
        )
        draft = output.draft
        return CaseResult(
            case_id=case.id,
            expected=case.expected,
            predicted_category=output.analysis.category,
            model_severity=output.analysis.severity,
            effective_severity=report.effective_severity,
            autonomy=decision.level,
            verification_passed=report.passed,
            verification_score=report.score,
            failed_checks=tuple(c.name for c in report.checks if not c.passed),
            cited_titles=tuple(c.title for c in draft.citations) if draft else (),
            citations_valid=draft is not None and citations_valid,
            has_draft=draft is not None,
            draft_body=draft.body if draft else "",
            usage=dataclasses.replace(output.usage, latency_s=latency),
        )

    @staticmethod
    def _error_result(case: GoldenCase, message: str) -> CaseResult:
        return CaseResult(
            case_id=case.id,
            expected=case.expected,
            predicted_category=InquiryCategory.UNKNOWN,
            model_severity=Severity.LOW,
            effective_severity=Severity.LOW,
            autonomy=AutonomyLevel.HUMAN_ONLY,
            verification_passed=False,
            verification_score=0.0,
            failed_checks=("pipeline_error",),
            cited_titles=(),
            citations_valid=False,
            has_draft=False,
            draft_body="",
            usage=Usage(),
            error=message,
        )
