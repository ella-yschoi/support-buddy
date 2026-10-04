"""Data models for the deterministic trust layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from src.core.models import DraftResponse, InquiryResult, Severity
from src.core.trust.kb_index import KnowledgeIndex


class FailEffect(str, Enum):
    """What a failed check does to routing. Interpreted by the policy engine."""

    NONE = "none"
    RAISE_SEVERITY = "raise_severity"
    BLOCK_AUTO = "block_auto"
    FORCE_CONFIRM = "force_confirm"
    FORCE_HUMAN_ONLY = "force_human_only"


@dataclass(frozen=True)
class Customer:
    plan: str = "unknown"  # free | pro | enterprise | unknown
    name: str = ""


@dataclass(frozen=True)
class ProcessState:
    """Recorded position in a multi-step flow vs. the step the draft claims."""

    flow: str
    recorded_step: int
    claimed_step: int


@dataclass(frozen=True)
class TrustInput:
    inquiry_text: str
    analysis: InquiryResult
    draft: DraftResponse | None
    kb_index: KnowledgeIndex
    customer: Customer = field(default_factory=Customer)
    log_text: str = ""
    process_state: ProcessState | None = None


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    weight: float
    detail: str = ""
    on_fail: FailEffect = FailEffect.NONE
    floor: Severity | None = None  # only set by severity_floor


@dataclass(frozen=True)
class VerificationReport:
    checks: tuple[Check, ...]
    passed: bool
    score: float
    effects: frozenset[FailEffect]
    severity_floor: Severity | None
    effective_severity: Severity
