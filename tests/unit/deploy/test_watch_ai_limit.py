"""The watcher's daily Claude cap must fit the Anthropic monthly spend limit.

The offline eval measured about $0.04 per briefing. The account's monthly limit
is $10, so 8 briefings a day (about $9.60 over 30 days) stays under it.
"""

import importlib
from collections.abc import Iterator
from pathlib import Path

import pytest
import tomllib

import src.config

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_DAILY_LIMIT = 8


@pytest.fixture
def fresh_config(monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    monkeypatch.delenv("WATCH_AI_DAILY_LIMIT", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)
    yield importlib.reload(src.config)
    monkeypatch.undo()
    importlib.reload(src.config)


def test_default_daily_limit(fresh_config: object) -> None:
    assert fresh_config.WATCH_AI_DAILY_LIMIT == EXPECTED_DAILY_LIMIT  # type: ignore[attr-defined]


def test_fly_daily_limit() -> None:
    fly = tomllib.loads((ROOT / "fly.toml").read_text())
    assert int(fly["env"]["WATCH_AI_DAILY_LIMIT"]) == EXPECTED_DAILY_LIMIT
