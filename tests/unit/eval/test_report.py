"""Tests for eval report rendering."""

from __future__ import annotations

import json

from src.core.models import InquiryCategory, Severity
from src.core.policy.models import AutonomyLevel
from src.eval.metrics import compute_metrics
from src.eval.report import ConfigRun, render_json, render_markdown
from tests.unit.eval.test_metrics import result


def make_run(name: str, **kwargs) -> ConfigRun:
    results = [result(case_id="ok"), result(case_id="bad", **kwargs)]
    return ConfigRun(
        name=name, models="m-a / m-b", results=results, metrics=compute_metrics(results)
    )


def test_markdown_contains_headline_metric_and_set_size():
    md = render_markdown([make_run("fast")], measured_on="2026-10-03")
    assert "Auto-resolvable rate" in md
    assert "n = 2" in md
    assert "2026-10-03" in md
    assert "fast" in md


def test_markdown_compares_configs_side_by_side():
    md = render_markdown(
        [make_run("fast"), make_run("premium", category=InquiryCategory.API)],
        measured_on="2026-10-03",
    )
    header = next(line for line in md.splitlines() if line.startswith("| Metric"))
    assert "fast" in header and "premium" in header


def test_markdown_lists_routing_mismatches():
    run = make_run("fast", autonomy=AutonomyLevel.AUTO, exp_autonomy=AutonomyLevel.CONFIRM)
    md = render_markdown([run], measured_on="2026-10-03")
    assert "bad" in md
    assert "expected confirm" in md.lower()


def test_markdown_flags_unsafe_passes_prominently():
    run = make_run("fast", exp_autonomy=AutonomyLevel.HUMAN_ONLY, autonomy=AutonomyLevel.CONFIRM)
    md = render_markdown([run], measured_on="2026-10-03")
    assert "UNSAFE" in md


def test_json_round_trips_core_numbers():
    run = make_run("fast", exp_severity=Severity.HIGH, model_severity=Severity.LOW)
    data = json.loads(render_json([run], measured_on="2026-10-03"))
    assert data["measured_on"] == "2026-10-03"
    assert data["configs"][0]["name"] == "fast"
    assert data["configs"][0]["metrics"]["n"] == 2
    assert len(data["configs"][0]["cases"]) == 2
