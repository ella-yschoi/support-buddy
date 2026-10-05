"""Tool-independent ticket model. Every adapter normalises its tool's data into this."""

from __future__ import annotations

import re
from dataclasses import dataclass

VALID_PLANS = ("free", "pro", "enterprise")

_FENCE = re.compile(r"```[^\n]*\n(.*?)\n?```", re.DOTALL)
_BLANK_RUNS = re.compile(r"\n{3,}")


def plan_from_labels(labels: tuple[str, ...]) -> str:
    """Customer plan from a `plan:<name>` label; `unknown` when absent or not a known plan."""
    for label in labels:
        key, _, value = label.partition(":")
        if key.strip().lower() == "plan" and value.strip().lower() in VALID_PLANS:
            return value.strip().lower()
    return "unknown"


def split_body(body: str) -> tuple[str, str]:
    """Separate prose from fenced code blocks. Fenced blocks are treated as logs."""
    logs = [m.group(1) for m in _FENCE.finditer(body)]
    text = _BLANK_RUNS.sub("\n\n", _FENCE.sub("", body)).strip()
    return text, "\n".join(logs)


@dataclass(frozen=True)
class Ticket:
    source: str  # which tool: "linear", "zendesk", ...
    external_id: str  # the tool's stable id
    key: str  # what people say out loud, e.g. "SUP-7"
    title: str
    body: str
    url: str
    created_at: str  # ISO 8601
    updated_at: str  # ISO 8601
    state: str  # the tool's display name for the state
    is_open: bool
    labels: tuple[str, ...] = ()
    priority: int = 0

    @property
    def plan(self) -> str:
        return plan_from_labels(self.labels)

    @property
    def inquiry_text(self) -> str:
        """What the pipeline reads: the title as a subject line, then the prose of the body."""
        text, _ = split_body(self.body)
        subject = f"Subject: {self.title}"
        return f"{subject}\n\n{text}" if text else subject

    @property
    def log_text(self) -> str:
        return split_body(self.body)[1]

    def has_label(self, name: str) -> bool:
        return name.strip().lower() in {label.strip().lower() for label in self.labels}
