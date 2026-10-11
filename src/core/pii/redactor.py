"""Deterministic PII redaction - runs before any text is sent to a model.

Replaces PII with stable, numbered placeholders and provides a reverse map
so the original text can be reconstructed locally (never logged or sent).

Covered patterns (order matters - most specific first):
  API keys  : Anthropic (sk-ant-*), Linear (lin_api_*), Bearer tokens, long hex
  Emails    : RFC-5321-ish local-part @ domain
  IPs       : IPv4, octets 0-255 only (avoids version numbers)
  Phones    : US/international formats
"""

from __future__ import annotations

import re
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

# Ordered list: more specific patterns first
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("API_KEY", _PAT_ANTHROPIC_KEY),
    ("API_KEY", _PAT_LINEAR_KEY),
    ("API_KEY", _PAT_BEARER),
    ("API_KEY", _PAT_HEX_TOKEN),
    ("EMAIL",   _PAT_EMAIL),
    ("IP",      _PAT_IP),
    ("PHONE",   _PAT_PHONE),
]


class PIIRedactor:
    """Stateless PII redactor. Each call to redact() is independent."""

    def redact(self, text: str) -> RedactedText:
        counters: dict[str, int] = {}
        seen: dict[str, str] = {}   # original → placeholder (dedup same value)
        result = text

        for label, pattern in _PATTERNS:
            def _replace(m: re.Match[str], _label: str = label) -> str:
                original = m.group(0)
                if original in seen:
                    return seen[original]
                counters[_label] = counters.get(_label, 0) + 1
                placeholder = f"[{_label}_{counters[_label]}]"
                seen[original] = placeholder
                return placeholder

            result = pattern.sub(_replace, result)

        reverse_map = {placeholder: original for original, placeholder in seen.items()}
        return RedactedText(text=result, reverse_map=reverse_map)
