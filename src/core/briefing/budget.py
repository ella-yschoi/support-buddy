"""A daily cap on Claude-built briefings that survives a restart."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = "CREATE TABLE IF NOT EXISTS ai_usage (day TEXT PRIMARY KEY, calls INTEGER NOT NULL)"


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class DailyAiBudget:
    """Counts briefings built with Claude per UTC day, in the same SQLite file as the queue."""

    def __init__(
        self, path: Path, limit: int, today: Callable[[], str] = _utc_today
    ):
        self._path = Path(path)
        self._limit = limit
        self._today = today
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.execute(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def try_take(self) -> bool:
        """Count one briefing, or refuse it because today's limit is used up."""
        day = self._today()
        with closing(self._connect()) as conn, conn:
            conn.execute("INSERT OR IGNORE INTO ai_usage (day, calls) VALUES (?, 0)", (day,))
            taken = conn.execute(
                "UPDATE ai_usage SET calls = calls + 1 WHERE day = ? AND calls < ?",
                (day, self._limit),
            ).rowcount
        return taken == 1

    def used_today(self) -> int:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT calls FROM ai_usage WHERE day = ?", (self._today(),)
            ).fetchone()
        return row[0] if row else 0
