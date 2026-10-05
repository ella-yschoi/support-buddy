"""Models for the autonomy policy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.core.models import InquiryCategory, Severity


class AutonomyLevel(str, Enum):
    AUTO = "auto"
    CONFIRM = "confirm"
    HUMAN_ONLY = "human_only"


@dataclass(frozen=True)
class Policy:
    human_only_keywords: tuple[str, ...]
    human_only_categories: tuple[InquiryCategory, ...]
    human_only_min_severity: Severity
    human_only_score_below: float
    confirm_plans: tuple[str, ...]
    confirm_min_severity: Severity
    auto_categories: tuple[InquiryCategory, ...]
    auto_max_severity: Severity
    auto_min_score: float
    auto_send_enabled: bool = False


@dataclass(frozen=True)
class Decision:
    level: AutonomyLevel
    reasons: tuple[str, ...]
    simulated: bool = False  # AUTO but nothing is actually sent
