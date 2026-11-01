"""start.sh must not point the watcher at a whole workspace."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]

STUB = """#!/bin/bash
echo "$(basename "$0") $*" >> "$STUB_LOG"
"""


@pytest.fixture
def run_start(tmp_path):
    root = tmp_path / "app"
    bin_dir = root / ".venv" / "bin"
    bin_dir.mkdir(parents=True)
    for name in ("support-buddy", "uvicorn"):
        stub = bin_dir / name
        stub.write_text(STUB)
        stub.chmod(0o755)
    shutil.copy(REPO / "start.sh", root / "start.sh")
    log = tmp_path / "calls.log"

    def run(**env: str) -> list[str]:
        full = {"PATH": os.environ["PATH"], "STUB_LOG": str(log), "HOME": str(tmp_path)}
        full.update(env)
        subprocess.run(["bash", "start.sh"], cwd=root, env=full, check=True, timeout=20)
        time.sleep(0.3)  # the watcher runs in the background
        return log.read_text().splitlines() if log.exists() else []

    return run


def watcher_calls(calls: list[str]) -> list[str]:
    return [c for c in calls if c.startswith("support-buddy")]


def test_without_a_scope_the_watcher_does_not_start(run_start):
    calls = run_start(LINEAR_API_KEY="k")
    assert watcher_calls(calls) == []
    assert any(c.startswith("uvicorn") for c in calls)


def test_without_a_linear_key_the_watcher_does_not_start(run_start):
    assert watcher_calls(run_start(WATCH_TEAM="SUP", WATCH_LABEL="ai-triage")) == []


def test_team_and_label_are_passed_to_the_watcher(run_start):
    calls = watcher_calls(
        run_start(LINEAR_API_KEY="k", WATCH_TEAM="SUP", WATCH_LABEL="ai-triage")
    )
    assert len(calls) == 1
    assert "--team SUP" in calls[0]
    assert "--label ai-triage" in calls[0]


def test_a_label_alone_is_enough(run_start):
    calls = watcher_calls(run_start(LINEAR_API_KEY="k", WATCH_LABEL="ai-triage"))
    assert len(calls) == 1
    assert "--label ai-triage" in calls[0]
    assert "--team" not in calls[0]


def test_a_team_alone_is_not_enough(run_start):
    """A whole team can still hold real tickets, so a label is required too."""
    assert watcher_calls(run_start(LINEAR_API_KEY="k", WATCH_TEAM="SUP")) == []
