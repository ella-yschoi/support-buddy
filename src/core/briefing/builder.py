"""Build a briefing: analysis, evidence, verification and routing, prepared in advance."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import datetime

from src.core.briefing.models import (
    Briefing,
    CheckView,
    Citation,
    Hypothesis,
    Sufficiency,
)
from src.core.models import DraftResponse, InquiryCategory, InquiryResult, LogInsight, Severity
from src.core.policy.engine import PolicyEngine
from src.core.policy.models import AutonomyLevel, Policy
from src.core.trust.kb_index import KnowledgeIndex
from src.core.trust.models import Customer, TrustInput
from src.core.trust.verifier import Verifier

logger = logging.getLogger(__name__)

# A briefing is only "sufficient" at or above this verification score.
SUFFICIENCY_MIN_SCORE = 0.8
# Categories where a diagnosis needs log evidence before the briefing can be trusted.
LOG_REQUIRED_CATEGORIES = frozenset(
    {
        InquiryCategory.SYNC,
        InquiryCategory.PERFORMANCE,
        InquiryCategory.API,
        InquiryCategory.PERMISSION,
    }
)
_MAX_EVIDENCE_LINES = 5

AnalyzeFn = Callable[[str], InquiryResult]
DraftFn = Callable[[str, InquiryResult], DraftResponse]
LogFn = Callable[[str], LogInsight]


def _default_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class BriefingBuilder:
    def __init__(
        self,
        analyze: AnalyzeFn,
        draft: DraftFn,
        analyze_logs: LogFn | None,
        kb_index: KnowledgeIndex,
        policy: Policy,
        verifier: Verifier | None = None,
        id_factory: Callable[[], str] = _default_id,
        clock: Callable[[], str] = _now,
    ):
        self._analyze = analyze
        self._draft = draft
        self._analyze_logs = analyze_logs
        self._kb_index = kb_index
        self._engine = PolicyEngine(policy)
        self._verifier = verifier or Verifier()
        self._id_factory = id_factory
        self._clock = clock

    def build(
        self,
        inquiry_text: str,
        customer: Customer,
        log_text: str = "",
        briefing_id: str | None = None,
    ) -> Briefing:
        briefing_id = briefing_id or self._id_factory()
        try:
            analysis = self._analyze(inquiry_text)
            draft = self._draft(inquiry_text, analysis)
        except Exception as exc:  # deliberate: any analyzer/drafter failure must not lose a ticket
            logger.error("briefing pipeline failed", exc_info=True)
            return self._failed(briefing_id, inquiry_text, customer, exc)

        insight, log_problem = self._run_log_analysis(log_text)

        inp = TrustInput(
            inquiry_text=inquiry_text,
            analysis=analysis,
            draft=draft,
            kb_index=self._kb_index,
            customer=customer,
            log_text=log_text,
        )
        report = self._verifier.verify(inp)
        decision = self._engine.route(inp, report)

        sufficiency, reasons = self._assess(
            analysis, draft, insight, log_problem, bool(log_text.strip()), report.score
        )
        return Briefing(
            id=briefing_id,
            created_at=self._clock(),
            inquiry_text=inquiry_text,
            customer_plan=customer.plan,
            summary=analysis.summary,
            category=analysis.category,
            model_severity=analysis.severity,
            effective_severity=report.effective_severity,
            hypotheses=self._hypotheses(analysis, insight),
            citations=tuple(Citation(c.doc_id, c.title) for c in draft.citations),
            checks=tuple(CheckView(c.name, c.passed, c.detail) for c in report.checks),
            verification_score=report.score,
            verification_passed=report.passed,
            autonomy=decision.level,
            autonomy_reasons=decision.reasons,
            simulated=decision.simulated,
            # Human-only tickets get a briefing, never a customer-facing draft.
            draft_body=None if decision.level is AutonomyLevel.HUMAN_ONLY else draft.body,
            sufficiency=sufficiency,
            sufficiency_reasons=reasons,
        )

    def _run_log_analysis(self, log_text: str) -> tuple[LogInsight | None, str | None]:
        if not log_text.strip():
            return None, None
        if self._analyze_logs is None:
            return None, "log analysis is not configured"
        try:
            return self._analyze_logs(log_text), None
        except Exception as exc:  # deliberate: a log failure degrades the briefing, not the ticket
            logger.error("log analysis failed", exc_info=True)
            return None, f"log analysis failed: {exc}"

    @staticmethod
    def _hypotheses(analysis: InquiryResult, insight: LogInsight | None) -> tuple[Hypothesis, ...]:
        kb_titles = tuple(a.title for a in analysis.relevant_articles[:3])
        found: list[Hypothesis] = []
        if insight is not None:
            events = insight.errors or insight.slow_operations
            lines = tuple(
                f"{e.timestamp} {e.level} {e.message}" for e in events[:_MAX_EVIDENCE_LINES]
            )
            found.append(Hypothesis(insight.root_cause_hypothesis, lines, kb_titles))
        if analysis.relevant_articles:
            top = analysis.relevant_articles[0].title
            found.append(Hypothesis(f"Most relevant guidance: {top}", (), kb_titles))
        return tuple(found)

    @staticmethod
    def _assess(
        analysis: InquiryResult,
        draft: DraftResponse,
        insight: LogInsight | None,
        log_problem: str | None,
        logs_attached: bool,
        score: float,
    ) -> tuple[Sufficiency, tuple[str, ...]]:
        problems: list[str] = []
        if not draft.citations:
            problems.append("No knowledge base citation backs the draft")
        if analysis.category in LOG_REQUIRED_CATEGORIES:
            has_log_evidence = insight is not None and bool(
                insight.errors or insight.slow_operations
            )
            if log_problem:
                problems.append(f"No log evidence: {log_problem}")
            elif not logs_attached:
                problems.append("No log evidence: ask the customer for logs")
            elif not has_log_evidence:
                problems.append(
                    "No log evidence: the attached logs show no errors or slow operations"
                )
        if score < SUFFICIENCY_MIN_SCORE:
            problems.append(f"Verification score {score:.2f} below {SUFFICIENCY_MIN_SCORE:.2f}")
        if problems:
            return Sufficiency.INSUFFICIENT, tuple(problems)
        return Sufficiency.SUFFICIENT, ("Evidence and citations found; verification passed",)

    def _failed(
        self, briefing_id: str, inquiry_text: str, customer: Customer, exc: Exception
    ) -> Briefing:
        """Never lose a ticket: a pipeline failure becomes a visible, human-only briefing."""
        return Briefing(
            id=briefing_id,
            created_at=self._clock(),
            inquiry_text=inquiry_text,
            customer_plan=customer.plan,
            summary=f"Automatic analysis failed: {exc}",
            category=InquiryCategory.UNKNOWN,
            model_severity=Severity.HIGH,
            effective_severity=Severity.HIGH,  # unknown severity is treated as high
            hypotheses=(),
            citations=(),
            checks=(),
            verification_score=0.0,
            verification_passed=False,
            autonomy=AutonomyLevel.HUMAN_ONLY,
            autonomy_reasons=("Fail-safe: analysis pipeline error",),
            simulated=False,
            draft_body=None,
            sufficiency=Sufficiency.INSUFFICIENT,
            sufficiency_reasons=(f"Pipeline error: {exc}",),
        )
