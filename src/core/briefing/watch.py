"""Run ingestion repeatedly, the way a TSE's overnight queue stays filled."""

from __future__ import annotations

import time
from collections.abc import Callable

from src.core.briefing.builder import BriefingBuilder
from src.core.briefing.ingest import IngestResult, ingest_tickets
from src.core.briefing.store import BriefingStore
from src.core.exceptions import TicketSourceError
from src.integrations.tickets.base import TicketSource
from src.integrations.tickets.cursors import CursorStore


def _summary(result: IngestResult, dry_run: bool) -> str:
    if dry_run:
        ids = ", ".join(result.would_create) or "nothing"
        return f"dry run: would create {len(result.would_create)} ({ids}); {result.fetched} changed"
    parts = [
        f"{len(result.created)} new",
        f"{result.skipped_closed} closed",
        f"{result.skipped_label} filtered out",
        f"{result.skipped_existing} already briefed",
    ]
    line = ", ".join(parts) + f" (of {result.fetched} changed)"
    if result.errors:
        line += f"; errors: {'; '.join(result.errors)}"
    return line


def run_watch(
    source: TicketSource,
    builder: BriefingBuilder,
    store: BriefingStore,
    cursors: CursorStore,
    *,
    interval: float,
    once: bool,
    cursor_key: str | None = None,
    label: str | None = None,
    include_closed: bool = False,
    dry_run: bool = False,
    sleep: Callable[[float], object] = time.sleep,
    max_cycles: int | None = None,
    report: Callable[[str], object] = print,
) -> int:
    """Poll the source. Returns the number of cycles run.

    In loop mode a temporary source outage is reported and retried next cycle. With `once`
    the failure propagates so a scheduler or the CLI can exit non-zero. Ctrl-C stops cleanly.
    """
    cycles = 0
    try:
        while True:
            try:
                result = ingest_tickets(
                    source,
                    builder,
                    store,
                    cursors,
                    cursor_key=cursor_key,
                    label=label,
                    include_closed=include_closed,
                    dry_run=dry_run,
                )
            except TicketSourceError as exc:
                if once:
                    raise
                report(f"source error: {exc}; retrying in {interval:g}s")
            else:
                report(_summary(result, dry_run))
            cycles += 1
            if once or (max_cycles is not None and cycles >= max_cycles):
                return cycles
            sleep(interval)
    except KeyboardInterrupt:
        report("stopped")
        return cycles
