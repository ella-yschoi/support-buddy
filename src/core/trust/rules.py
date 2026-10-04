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

# Plan-gated feature -> minimum plan, mirrors data/knowledge/plan_matrix.md.
FEATURE_MIN_PLAN: dict[str, str] = {
    "sso": "enterprise",
    "saml": "enterprise",
    "audit log": "pro",
    "webhook": "pro",
    "team space": "pro",
    "delta sync": "pro",
}
# Whole-word matchers, so "association" or "lesson" never counts as "sso".
FEATURE_PATTERNS: dict[str, re.Pattern[str]] = {
    "sso": re.compile(r"\bsso\b", re.IGNORECASE),
    "saml": re.compile(r"\bsaml\b", re.IGNORECASE),
    "audit log": re.compile(r"\baudit logs?\b", re.IGNORECASE),
    "webhook": re.compile(r"\bwebhooks?\b", re.IGNORECASE),
    "team space": re.compile(r"\bteam spaces?\b", re.IGNORECASE),
    "delta sync": re.compile(r"\bdelta sync\b", re.IGNORECASE),
}

# Error-code prefixes the product defines, checked even if the KB lacks a doc for them.
PRODUCT_ERROR_PREFIXES: frozenset[str] = frozenset({"SYNC", "AUTH", "PERF", "API", "ACCT"})
ERROR_CODE_TOKEN_RE = re.compile(r"\b([A-Z]{2,5})-(\d{3,4})\b")

COMMITMENT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\brefund(?:s|ed|ing)?\b",
        r"\breimburs\w*",
        r"\bcompensat\w*",
        r"\bservice credits?\b",
        r"\bguarantee[sd]?\b",
        # A time promise needs a first-person subject; "exports expire within 7 days"
        # is a fact about the product, not a commitment.
        r"\b(?:we|i|our (?:team|engineers?)|engineering|support)\b[^.!?\n]{0,80}?"
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
