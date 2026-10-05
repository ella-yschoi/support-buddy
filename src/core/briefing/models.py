"""Briefing: everything a TSE needs, prepared before they open the ticket."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.core.models import InquiryCategory, Severity
from src.core.policy.models import AutonomyLevel


class Sufficiency(str, Enum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"  # TSE should start from the raw logs


@dataclass(frozen=True)
class Hypothesis:
    statement: str
    log_evidence: tuple[str, ...]
    kb_evidence: tuple[str, ...]


@dataclass(frozen=True)
class Citation:
    doc_id: str
    title: str


@dataclass(frozen=True)
class CheckView:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class Briefing:
    id: str
    created_at: str
    inquiry_text: str
    customer_plan: str
    summary: str
    category: InquiryCategory
    model_severity: Severity
    effective_severity: Severity
    hypotheses: tuple[Hypothesis, ...]
    citations: tuple[Citation, ...]
    checks: tuple[CheckView, ...]
    verification_score: float
    verification_passed: bool
    autonomy: AutonomyLevel
    autonomy_reasons: tuple[str, ...]
    simulated: bool
    draft_body: str | None
    sufficiency: Sufficiency
    sufficiency_reasons: tuple[str, ...]
    status: str = "ready"  # ready | approved
    approved_body: str | None = None
    edit_ratio: float | None = None  # 0.0 = sent as drafted, 1.0 = fully rewritten

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "inquiry_text": self.inquiry_text,
            "customer_plan": self.customer_plan,
            "summary": self.summary,
            "category": self.category.value,
            "model_severity": self.model_severity.value,
            "effective_severity": self.effective_severity.value,
            "hypotheses": [
                {
                    "statement": h.statement,
                    "log_evidence": list(h.log_evidence),
                    "kb_evidence": list(h.kb_evidence),
                }
                for h in self.hypotheses
            ],
            "citations": [{"doc_id": c.doc_id, "title": c.title} for c in self.citations],
            "checks": [
                {"name": c.name, "passed": c.passed, "detail": c.detail} for c in self.checks
            ],
            "verification_score": self.verification_score,
            "verification_passed": self.verification_passed,
            "autonomy": self.autonomy.value,
            "autonomy_reasons": list(self.autonomy_reasons),
            "simulated": self.simulated,
            "draft_body": self.draft_body,
            "sufficiency": self.sufficiency.value,
            "sufficiency_reasons": list(self.sufficiency_reasons),
            "status": self.status,
            "approved_body": self.approved_body,
            "edit_ratio": self.edit_ratio,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Briefing:
        return cls(
            id=d["id"],
            created_at=d["created_at"],
            inquiry_text=d["inquiry_text"],
            customer_plan=d["customer_plan"],
            summary=d["summary"],
            category=InquiryCategory(d["category"]),
            model_severity=Severity(d["model_severity"]),
            effective_severity=Severity(d["effective_severity"]),
            hypotheses=tuple(
                Hypothesis(h["statement"], tuple(h["log_evidence"]), tuple(h["kb_evidence"]))
                for h in d["hypotheses"]
            ),
            citations=tuple(Citation(c["doc_id"], c["title"]) for c in d["citations"]),
            checks=tuple(CheckView(c["name"], c["passed"], c["detail"]) for c in d["checks"]),
            verification_score=d["verification_score"],
            verification_passed=d["verification_passed"],
            autonomy=AutonomyLevel(d["autonomy"]),
            autonomy_reasons=tuple(d["autonomy_reasons"]),
            simulated=d["simulated"],
            draft_body=d["draft_body"],
            sufficiency=Sufficiency(d["sufficiency"]),
            sufficiency_reasons=tuple(d["sufficiency_reasons"]),
            status=d["status"],
            approved_body=d["approved_body"],
            edit_ratio=d["edit_ratio"],
        )
