"""The watcher's daily cap on Claude-built briefings."""

from __future__ import annotations

from src.core.briefing.budget import DailyAiBudget


def test_allows_calls_up_to_the_limit_then_refuses(tmp_path):
    budget = DailyAiBudget(tmp_path / "b.db", limit=2, today=lambda: "2026-11-06")
    assert [budget.try_take() for _ in range(3)] == [True, True, False]


def test_a_new_day_starts_again(tmp_path):
    day = ["2026-11-06"]
    budget = DailyAiBudget(tmp_path / "b.db", limit=1, today=lambda: day[0])
    assert budget.try_take() is True
    assert budget.try_take() is False
    day[0] = "2026-11-07"
    assert budget.try_take() is True


def test_the_count_survives_a_restart(tmp_path):
    path = tmp_path / "b.db"
    DailyAiBudget(path, limit=1, today=lambda: "2026-11-06").try_take()
    after_restart = DailyAiBudget(path, limit=1, today=lambda: "2026-11-06")
    assert after_restart.try_take() is False


def test_a_limit_of_zero_turns_ai_off(tmp_path):
    budget = DailyAiBudget(tmp_path / "b.db", limit=0, today=lambda: "2026-11-06")
    assert budget.try_take() is False


def test_used_today_counts_only_granted_calls(tmp_path):
    budget = DailyAiBudget(tmp_path / "b.db", limit=1, today=lambda: "2026-11-06")
    budget.try_take()
    budget.try_take()
    assert budget.used_today() == 1
