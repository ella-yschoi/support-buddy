"""Result types produced by the eval runner."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.models import InquiryCategory, Severity
from src.core.policy.models import AutonomyLevel
from src.eval.cases import Expected


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    cost_usd: float = 0.0


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    expected: Expected
    predicted_category: InquiryCategory
    model_severity: Severity
    effective_severity: Severity
    autonomy: AutonomyLevel
    verification_passed: bool
    verification_score: float
    failed_checks: tuple[str, ...]
    cited_titles: tuple[str, ...]
    citations_valid: bool
    has_draft: bool
    draft_body: str
    usage: Usage
    error: str | None = None
