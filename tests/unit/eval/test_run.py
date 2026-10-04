"""Tests for eval orchestration and the `eval` CLI command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from src.cli import app
from src.core.exceptions import ConfigError
from src.eval.run import run_local_eval

runner = CliRunner()


def test_run_local_eval_returns_single_baseline_run_over_golden_set():
    runs = run_local_eval()
    assert len(runs) == 1
    assert runs[0].name == "local-baseline"
    assert runs[0].metrics.n >= 40
    assert runs[0].metrics.total_cost_usd == 0.0


def test_local_baseline_never_routes_a_human_only_case_below_human_only():
    # The deterministic policy keywords, not the model, guard sensitive topics.
    (run,) = run_local_eval()
    assert run.metrics.unsafe_pass_count == 0


def test_cli_eval_local_writes_markdown_and_json(tmp_path: Path):
    result = runner.invoke(app, ["eval", "--pipeline", "local", "--out", str(tmp_path)])
    assert result.exit_code == 0, result.output
    md = (tmp_path / "eval-report.md").read_text()
    data = json.loads((tmp_path / "eval-report.json").read_text())
    assert "Auto-resolvable rate" in md
    assert data["configs"][0]["metrics"]["n"] >= 40


def test_cli_eval_claude_without_api_key_exits_nonzero(tmp_path: Path):
    with patch("src.cli.ANTHROPIC_API_KEY", ""):
        result = runner.invoke(
            app, ["eval", "--pipeline", "claude", "--out", str(tmp_path), "--yes"]
        )
    assert result.exit_code == 1
    assert "ANTHROPIC_API_KEY" in result.output


def test_cli_eval_claude_declined_confirmation_makes_no_api_calls(tmp_path: Path):
    with (
        patch("src.cli.ANTHROPIC_API_KEY", "test-key"),
        patch("src.cli.run_claude_eval") as run_claude,
    ):
        result = runner.invoke(
            app, ["eval", "--pipeline", "claude", "--out", str(tmp_path)], input="n\n"
        )
    assert result.exit_code == 1
    run_claude.assert_not_called()
    assert not (tmp_path / "eval-report.md").exists()


def test_cli_eval_unknown_config_name_reports_error(tmp_path: Path):
    with patch("src.cli.ANTHROPIC_API_KEY", "test-key"):
        result = runner.invoke(
            app,
            ["eval", "--pipeline", "claude", "--names", "nope", "--out", str(tmp_path), "--yes"],
        )
    assert result.exit_code == 1
    assert "nope" in result.output


def test_select_registries_rejects_unknown_names():
    from src.eval.run import select_registries

    try:
        select_registries(None, ["nope"])
    except ConfigError as exc:
        assert "nope" in str(exc)
    else:
        raise AssertionError("expected ConfigError")
