"""Rule data for deterministic checks. Pure data, no behavior, no LLM."""

from __future__ import annotations

import re

from src.core.models import Severity

SEVERITY_ORDER: tuple[Severity, ...] = (
    Severity.LOW,
    Severity.MEDIUM,
    Severity.HIGH,
    Severity.CRITICAL,
)

PLAN_ORDER: tuple[str, ...] = ("free", "pro", "enterprise")

# Feature keyword (lowercase) -> minimum plan, mirrors data/knowledge/plan_matrix.md.
FEATURE_MIN_PLAN: dict[str, str] = {
    "sso": "enterprise",
    "saml": "enterprise",
    "audit log": "pro",
    "webhook": "pro",
    "team space": "pro",
    "delta sync": "pro",
}

COMMITMENT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\brefund(?:s|ed|ing)?\b",
        r"\breimburs\w*",
        r"\bcompensat\w*",
        r"\bservice credits?\b",
        r"\bguarantee[sd]?\b",
        r"\bwithin \d+\s*(?:minutes?|hours?|business days?|days?)\b",
    )
)

ALL_AFFECTED_RE = re.compile(
    r"\b(?:everyone|all (?:of )?(?:our )?(?:users?|employees?|team)|"
    r"(?:entire|whole) (?:team|company|org\w*)|every (?:user|employee))\b",
    re.IGNORECASE,
)
DATA_LOSS_RE = re.compile(
    r"\b(?:data loss|lost (?:all )?(?:our )?files|files? (?:were|was|got|are) deleted|"
    r"deleted (?:all|everything)|data breach|unauthori[sz]ed access)\b",
    re.IGNORECASE,
)

SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{16,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{16,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)
SENSITIVE_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"),
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
)
