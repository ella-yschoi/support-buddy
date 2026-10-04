"""Tests for pre-computed demo briefings."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from src.cli import app
from src.core.briefing.models import Briefing
from src.core.policy.models import AutonomyLevel
from src.eval.demo import DEMO_CASE_IDS, generate_demo_briefings, write_demo_file


@pytest.fixture(scope="module")
def briefings() -> list[Briefing]:
    return generate_demo_briefings()


def test_one_briefing_per_demo_case_with_stable_ids(briefings):
    assert sorted(b.id for b in briefings) == sorted(f"demo-{c}" for c in DEMO_CASE_IDS)
    assert len(briefings) == len(DEMO_CASE_IDS)
    assert all(b.id.startswith("demo-") for b in briefings)


def test_demo_set_shows_every_autonomy_level_and_both_sufficiency_verdicts(briefings):
    assert {b.autonomy for b in briefings} == set(AutonomyLevel)
    assert {b.sufficiency.value for b in briefings} == {"sufficient", "insufficient"}


def test_demo_queue_is_ordered_most_severe_first(briefings):
    order = ["low", "medium", "high", "critical"]
    ranks = [order.index(b.effective_severity.value) for b in briefings]
    assert ranks == sorted(ranks, reverse=True)


def test_human_only_demo_briefings_have_no_draft(briefings):
    human = [b for b in briefings if b.autonomy is AutonomyLevel.HUMAN_ONLY]
    assert human and all(b.draft_body is None for b in human)


def test_generation_is_deterministic(briefings):
    again = generate_demo_briefings()
    assert [b.to_dict() for b in again] == [b.to_dict() for b in briefings]


def test_written_file_round_trips(tmp_path: Path, briefings):
    path = write_demo_file(briefings, tmp_path / "briefings.json")
    data = json.loads(path.read_text())
    assert data["pipeline"] == "local"
    assert data["briefings"][0]["id"] == briefings[0].id
    assert [Briefing.from_dict(d) for d in data["briefings"]] == briefings


def test_cli_demo_data_writes_the_file(tmp_path: Path):
    out = tmp_path / "demo.json"
    result = CliRunner().invoke(app, ["demo-data", "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert json.loads(out.read_text())["briefings"]
