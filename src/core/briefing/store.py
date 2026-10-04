"""SQLite storage for briefings and the Overnight Queue ordering."""

from __future__ import annotations

import dataclasses
import json
import sqlite3
from contextlib import closing
from difflib import SequenceMatcher
from pathlib import Path

from src.core.briefing.models import Briefing
from src.core.exceptions import BriefingError, BriefingStateError
from src.core.trust.rules import SEVERITY_ORDER

_SCHEMA = """
CREATE TABLE IF NOT EXISTS briefings (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL,
    severity_rank INTEGER NOT NULL,
    payload TEXT NOT NULL
)
"""


class BriefingStore:
    def __init__(self, path: Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def add(self, briefing: Briefing) -> None:
        try:
            with closing(self._connect()) as conn, conn:
                conn.execute(
                    "INSERT INTO briefings (id, created_at, status, severity_rank, payload) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        briefing.id,
                        briefing.created_at,
                        briefing.status,
                        SEVERITY_ORDER.index(briefing.effective_severity),
                        json.dumps(briefing.to_dict()),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise BriefingError(f"briefing {briefing.id} already exists") from exc

    def exists(self, briefing_id: str) -> bool:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT 1 FROM briefings WHERE id = ?", (briefing_id,)).fetchone()
        return row is not None

    def get(self, briefing_id: str) -> Briefing:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT payload FROM briefings WHERE id = ?", (briefing_id,)
            ).fetchone()
        if row is None:
            raise BriefingError(f"briefing {briefing_id} not found")
        return Briefing.from_dict(json.loads(row[0]))

    def list_queue(self) -> list[Briefing]:
        """Ready briefings, most severe first, oldest first within a severity."""
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT payload FROM briefings WHERE status = 'ready' "
                "ORDER BY severity_rank DESC, created_at ASC"
            ).fetchall()
        return [Briefing.from_dict(json.loads(r[0])) for r in rows]

    def approve(self, briefing_id: str, final_body: str) -> Briefing:
        """Record what the TSE actually sent and how far it moved from the draft."""
        current = self.get(briefing_id)
        if current.status != "ready":
            raise BriefingStateError(f"briefing {briefing_id} is already {current.status}")
        ratio: float | None = None
        if current.draft_body is not None:
            ratio = 1.0 - SequenceMatcher(None, current.draft_body, final_body).ratio()
        updated = dataclasses.replace(
            current, status="approved", approved_body=final_body, edit_ratio=ratio
        )
        with closing(self._connect()) as conn, conn:
            cursor = conn.execute(
                "UPDATE briefings SET status = ?, payload = ? WHERE id = ? AND status = 'ready'",
                (updated.status, json.dumps(updated.to_dict()), briefing_id),
            )
            if cursor.rowcount != 1:  # lost a race with another approval
                raise BriefingStateError(f"briefing {briefing_id} is no longer ready")
        return updated
