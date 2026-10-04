"""Render eval results as Markdown and JSON."""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable
from dataclasses import dataclass

from src.core.policy.models import AutonomyLevel
from src.eval.metrics import Metrics
from src.eval.models import CaseResult


@dataclass(frozen=True)
class ConfigRun:
    name: str
    models: str
    results: list[CaseResult]
    metrics: Metrics


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _usd(value: float) -> str:
    return f"${value:.4f}"


# label, getter, formatter, higher_is_better (None = informational, no highlight)
_ROWS: list[tuple[str, Callable[[Metrics], float], Callable[[float], str], bool | None]] = [
    ("**Auto-resolvable rate (all cases)**", lambda m: m.auto_resolvable_rate, _pct, True),
    (
        "Auto-resolvable rate (in-scope cases)",
        lambda m: m.auto_resolvable_in_scope_rate,
        _pct,
        True,
    ),
    ("Unsafe-pass rate (target 0%)", lambda m: m.unsafe_pass_rate, _pct, False),
    ("Category accuracy", lambda m: m.category_accuracy, _pct, True),
    ("Severity under-triage (model)", lambda m: m.severity_under_triage_rate, _pct, False),
    (
        "Severity under-triage (after trust layer)",
        lambda m: m.effective_under_triage_rate,
        _pct,
        False,
    ),
    ("Citation validity", lambda m: m.citation_validity, _pct, True),
    ("Required citations present", lambda m: m.must_cite_rate, _pct, True),
    ("Forbidden phrases in draft", lambda m: m.must_not_say_violation_rate, _pct, False),
    ("Routing agreement", lambda m: m.routing_agreement, _pct, True),
    ("Errors (count)", lambda m: float(m.error_count), lambda v: str(int(v)), False),
    ("Total cost", lambda m: m.total_cost_usd, _usd, None),
    ("Mean latency (s)", lambda m: m.mean_latency_s, lambda v: f"{v:.2f}", None),
]


def render_markdown(runs: list[ConfigRun], measured_on: str) -> str:
    n = runs[0].metrics.n if runs else 0
    lines = [
        "# Support Buddy Eval Report",
        "",
        f"Measured on {measured_on} | golden set n = {n} | configs: "
        + ", ".join(r.name for r in runs),
        "",
        "## Summary",
        "",
        "| Metric | " + " | ".join(r.name for r in runs) + " |",
        "|---|" + "---|" * len(runs),
        "| Models | " + " | ".join(r.models for r in runs) + " |",
    ]
    for label, getter, fmt, higher_better in _ROWS:
        values = [getter(r.metrics) for r in runs]
        best = None
        if higher_better is not None and len(set(values)) > 1:
            best = max(values) if higher_better else min(values)
        cells = [f"**{fmt(v)}**" if best is not None and v == best else fmt(v) for v in values]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    for run in runs:
        lines += _unsafe_section(run)
    for run in runs:
        lines += _mismatch_section(run)
    return "\n".join(lines) + "\n"


def _unsafe_section(run: ConfigRun) -> list[str]:
    unsafe = [
        r
        for r in run.results
        if r.expected.autonomy is AutonomyLevel.HUMAN_ONLY and r.autonomy is not r.expected.autonomy
    ]
    if not unsafe:
        return []
    lines = ["", f"## UNSAFE passes: {run.name}", ""]
    lines += [f"- `{r.case_id}` routed to {r.autonomy.value} (expected human_only)" for r in unsafe]
    return lines


def _mismatch_section(run: ConfigRun) -> list[str]:
    wrong = [r for r in run.results if r.autonomy is not r.expected.autonomy]
    if not wrong:
        return ["", f"## Routing mismatches: {run.name}", "", "None."]
    lines = [
        "",
        f"## Routing mismatches: {run.name}",
        "",
        "| Case | Outcome | Failed checks |",
        "|---|---|---|",
    ]
    for r in wrong:
        failed = ", ".join(r.failed_checks) or "none"
        lines.append(
            f"| `{r.case_id}` | expected {r.expected.autonomy.value}, got {r.autonomy.value} "
            f"| {failed} |"
        )
    return lines


def render_json(runs: list[ConfigRun], measured_on: str) -> str:
    payload = {
        "measured_on": measured_on,
        "configs": [
            {
                "name": r.name,
                "models": r.models,
                "metrics": dataclasses.asdict(r.metrics),
                "cases": [dataclasses.asdict(c) for c in r.results],
            }
            for r in runs
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)
