"""Deterministic PII redaction - runs before any text is sent to a model.

Replaces PII with stable, numbered placeholders and provides a reverse map
so the original text can be reconstructed locally (never logged or sent).

Covered patterns (order matters - most specific first):
  API keys  : Anthropic (sk-ant-*), Linear (lin_api_*), AWS (AKIA*), GitHub (gh?_*),
              sk-* keys, JWTs, Bearer and Basic credentials, long hex
  Emails    : RFC-5321-ish local-part @ domain
  IPs       : IPv4, octets 0-255 only (avoids version numbers)
  Cards     : 13-19 digits that pass the Luhn check
  SSNs      : US format 123-45-6789
  Secrets   : the value after password=, token:, api_key= and similar (the key stays)
  Phones    : US/international formats

Not covered, because no deterministic rule finds them: names and street addresses.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class RedactedText:
    text: str
    reverse_map: dict[str, str]

    def restore(self) -> str:
        result = self.text
        for placeholder, original in self.reverse_map.items():
            result = result.replace(placeholder, original)
        return result


# ---------------------------------------------------------------------------
# Patterns - compiled once at module level
# ---------------------------------------------------------------------------

# Anthropic key: sk-ant-<suffix> where suffix contains alphanumeric/-/_
_PAT_ANTHROPIC_KEY = re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}")

# Linear personal API key
_PAT_LINEAR_KEY = re.compile(r"lin_api_[A-Za-z0-9_\-]{8,}")

# Bearer token (the token part after "Bearer ")
_PAT_BEARER = re.compile(r"(?<=Bearer\s)[A-Za-z0-9\-_\.~\+/]+=*")

# Long hex string ≥ 32 chars (API secrets, session tokens, etc.)
_PAT_HEX_TOKEN = re.compile(r"\b[0-9a-f]{32,}\b")

# Email address
_PAT_EMAIL = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# IPv4: each octet 0-255
_OCTET = r"(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)"
_PAT_IP = re.compile(rf"\b{_OCTET}\.{_OCTET}\.{_OCTET}\.{_OCTET}\b")

# Phone numbers: US (+1) and bare 10-digit formats with separators
_PAT_PHONE = re.compile(
    r"(?:\+?1[\s\-.]?)?"          # optional country code
    r"(?:\(\d{3}\)|\d{3})"        # area code (with or without parens)
    r"[\s\-.]"                    # separator
    r"\d{3}"                      # exchange
    r"[\s\-.]"                    # separator
    r"\d{4}"                      # subscriber
)

# AWS access key id
_PAT_AWS_KEY = re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")

# GitHub token: ghp_, gho_, ghu_, ghs_, ghr_
_PAT_GITHUB_TOKEN = re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")

# Other sk-... keys (Anthropic's sk-ant-... is matched first)
_PAT_SK_KEY = re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}")

# JSON web token: three base64url segments, the first two start with "eyJ"
_PAT_JWT = re.compile(r"\beyJ[A-Za-z0-9_\-]{5,}\.eyJ[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{5,}")

# Basic auth credentials (the base64 part after "Basic ")
_PAT_BASIC = re.compile(r"(?<=Basic\s)[A-Za-z0-9+/]{8,}=*")

# Card numbers: grouped 4-4-4-4, Amex 4-6-5, or a plain 13-19 digit run. Luhn-checked below.
_PAT_CARD = re.compile(
    r"\b\d{4}[ \-]\d{4}[ \-]\d{4}[ \-]\d{4}\b"
    r"|\b\d{4}[ \-]\d{6}[ \-]\d{5}\b"
    r"|\b\d{13,19}\b"
)

# US social security number
_PAT_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# password=..., "api_key": "...", ?token=...  Only the value (group "secret") is replaced.
_PAT_SECRET_VALUE = re.compile(
    r"(?:password|passwd|pwd|secret|token|access[_-]?token|api[_-]?key|apikey)"
    r"[\"']?\s*[:=]\s*[\"']?(?P<secret>[^\s&\"',;\[]{4,})",
    re.IGNORECASE,
)


def _luhn_valid(candidate: str) -> bool:
    digits = [int(c) for c in candidate if c.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


# Ordered list: more specific patterns first. The third item, when set, must accept the
# matched text or the match is left alone.
_PATTERNS: list[tuple[str, re.Pattern[str], Callable[[str], bool] | None]] = [
    ("API_KEY", _PAT_ANTHROPIC_KEY, None),
    ("API_KEY", _PAT_LINEAR_KEY, None),
    ("API_KEY", _PAT_AWS_KEY, None),
    ("API_KEY", _PAT_GITHUB_TOKEN, None),
    ("API_KEY", _PAT_SK_KEY, None),
    ("API_KEY", _PAT_BEARER, None),
    ("API_KEY", _PAT_BASIC, None),
    ("API_KEY", _PAT_JWT, None),
    ("API_KEY", _PAT_HEX_TOKEN, None),
    ("EMAIL",   _PAT_EMAIL, None),
    ("IP",      _PAT_IP, None),
    ("CARD",    _PAT_CARD, _luhn_valid),
    ("SSN",     _PAT_SSN, None),
    ("SECRET",  _PAT_SECRET_VALUE, None),
    ("PHONE",   _PAT_PHONE, None),
]


class PIIRedactor:
    """Stateless PII redactor. Each call to redact() is independent."""

    def redact(self, text: str) -> RedactedText:
        counters: dict[str, int] = {}
        seen: dict[str, str] = {}   # original → placeholder (dedup same value)
        result = text

        for label, pattern, accepts in _PATTERNS:
            def _replace(
                m: re.Match[str],
                _label: str = label,
                _accepts: Callable[[str], bool] | None = accepts,
            ) -> str:
                # Patterns with a "secret" group replace only that part of the match.
                has_group = "secret" in pattern.groupindex
                original = m.group("secret") if has_group else m.group(0)
                if _accepts is not None and not _accepts(original):
                    return m.group(0)
                if original in seen:
                    placeholder = seen[original]
                else:
                    counters[_label] = counters.get(_label, 0) + 1
                    placeholder = f"[{_label}_{counters[_label]}]"
                    seen[original] = placeholder
                if not has_group:
                    return placeholder
                start, end = m.span("secret")
                return m.group(0)[: start - m.start()] + placeholder + m.group(0)[end - m.start():]

            result = pattern.sub(_replace, result)

        reverse_map = {placeholder: original for original, placeholder in seen.items()}
        return RedactedText(text=result, reverse_map=reverse_map)
