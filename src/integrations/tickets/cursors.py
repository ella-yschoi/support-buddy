"""Remembers how far each ticket source has been read."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

_SCHEMA = "CREATE TABLE IF NOT EXISTS sync_cursors (key TEXT PRIMARY KEY, cursor TEXT NOT NULL)"


class CursorStore:
    """One cursor (an ISO timestamp) per key such as `linear:SUP`. May share the briefing DB."""

    def __init__(self, path: Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.execute(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def get(self, key: str) -> str | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT cursor FROM sync_cursors WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def set(self, key: str, cursor: str) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT INTO sync_cursors (key, cursor) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET cursor = excluded.cursor",
                (key, cursor),
            )
