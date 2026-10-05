"""Tests for the watch loop and the `watch` CLI command."""

from __future__ import annotations

import itertools
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from src.cli import app
from src.core.briefing.store import BriefingStore
from src.core.briefing.watch import run_watch
from src.core.exceptions import TicketSourceError
from src.integrations.tickets.cursors import CursorStore
from src.integrations.tickets.memory import InMemoryTicketSource
from tests.unit.core.briefing.test_builder import feature_analysis, make_builder
from tests.unit.core.briefing.test_builder import policy as policy  # noqa: F401
from tests.unit.core.briefing.test_ingest import ticket


@pytest.fixture
def env(tmp_path, kb_index, policy):  # noqa: F811
    db = tmp_path / "b.db"
    builder = make_builder(kb_index, policy, analysis=feature_analysis())
    return builder, BriefingStore(db), CursorStore(db)


class FlakySource(InMemoryTicketSource):
    def __init__(self, tickets, failures):
        super().__init__(tickets)
        self.failures = failures
        self.calls = 0

    def fetch_updated(self, since):
        self.calls += 1
        if self.calls <= self.failures:
            raise TicketSourceError("temporary outage")
        return super().fetch_updated(since)


def test_once_runs_a_single_cycle_without_sleeping(env):
    builder, store, cursors = env
    sleeps: list[float] = []
    cycles = run_watch(
        InMemoryTicketSource([ticket(1)]),
        builder,
        store,
        cursors,
        interval=30,
        once=True,
        sleep=sleeps.append,
    )
    assert cycles == 1
    assert sleeps == []
    assert [b.id for b in store.list_queue()] == ["memory-id-1"]


def test_loop_sleeps_between_cycles_for_the_given_interval(env):
    builder, store, cursors = env
    sleeps: list[float] = []
    cycles = run_watch(
        InMemoryTicketSource([ticket(1)]),
        builder,
        store,
        cursors,
        interval=45,
        once=False,
        sleep=sleeps.append,
        max_cycles=3,
    )
    assert cycles == 3
    assert sleeps == [45, 45]


def test_loop_survives_a_temporary_source_outage(env):
    builder, store, cursors = env
    source = FlakySource([ticket(1)], failures=1)
    reports: list[str] = []
    run_watch(
        source,
        builder,
        store,
        cursors,
        interval=1,
        once=False,
        sleep=lambda s: None,
        max_cycles=3,
        report=reports.append,
    )
    assert [b.id for b in store.list_queue()] == ["memory-id-1"]
    assert any("temporary outage" in line for line in reports)


def test_once_mode_raises_on_a_source_outage_so_the_caller_can_exit_nonzero(env):
    builder, store, cursors = env
    with pytest.raises(TicketSourceError):
        run_watch(
            FlakySource([ticket(1)], failures=5),
            builder,
            store,
            cursors,
            interval=1,
            once=True,
            sleep=lambda s: None,
        )


def test_ctrl_c_during_sleep_stops_the_loop_cleanly(env):
    builder, store, cursors = env

    def interrupt(_seconds):
        raise KeyboardInterrupt

    cycles = run_watch(
        InMemoryTicketSource([ticket(1)]),
        builder,
        store,
        cursors,
        interval=1,
        once=False,
        sleep=interrupt,
    )
    assert cycles == 1


def test_each_cycle_reports_what_it_did(env):
    builder, store, cursors = env
    reports: list[str] = []
    counter = itertools.count()
    run_watch(
        InMemoryTicketSource([ticket(1), ticket(2, is_open=False)]),
        builder,
        store,
        cursors,
        interval=1,
        once=True,
        sleep=lambda s: next(counter),
        report=reports.append,
    )
    assert any("1 new" in line and "1 closed" in line for line in reports)


def test_dry_run_reports_what_would_be_created_and_stores_nothing(env):
    builder, store, cursors = env
    reports: list[str] = []
    run_watch(
        InMemoryTicketSource([ticket(1)]),
        builder,
        store,
        cursors,
        interval=1,
        once=True,
        dry_run=True,
        sleep=lambda s: None,
        report=reports.append,
    )
    assert store.list_queue() == []
    assert any("would create" in line.lower() for line in reports)


runner = CliRunner()


def test_cli_rejects_an_unknown_source():
    result = runner.invoke(app, ["watch", "--source", "carrier-pigeon", "--once"])
    assert result.exit_code == 1
    assert "carrier-pigeon" in result.output


def test_cli_without_a_linear_key_explains_what_to_do():
    with patch("src.cli.LINEAR_API_KEY", ""):
        result = runner.invoke(app, ["watch", "--source", "linear", "--once"])
    assert result.exit_code == 1
    assert "LINEAR_API_KEY" in result.output


def test_cli_once_with_a_source_outage_exits_nonzero():
    class Down:
        name = "linear"

        def fetch_updated(self, since):
            raise TicketSourceError("linear is down")

        def get(self, external_id):
            raise TicketSourceError("linear is down")

    with (
        patch("src.cli.LINEAR_API_KEY", "test-key"),
        patch("src.cli.build_source", return_value=Down()),
    ):
        result = runner.invoke(app, ["watch", "--source", "linear", "--once"])
    assert result.exit_code == 1
    assert "linear is down" in result.output
