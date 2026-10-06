"""Turn tickets from a ticket tool into briefings, safely and repeatably."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from src.core.briefing.builder import BriefingBuilder
from src.core.briefing.models import Origin
from src.core.briefing.store import BriefingStore
from src.core.exceptions import BriefingError
from src.core.trust.models import Customer
from src.integrations.tickets.base import TicketSource
from src.integrations.tickets.cursors import CursorStore
from src.integrations.tickets.models import Ticket

logger = logging.getLogger(__name__)

# Re-read a little before the cursor. Tools stamp changes with second precision, so a
# change landing at the exact cursor second after we polled would otherwise be missed.
# Briefing ids are derived from the ticket, so re-reading never duplicates work.
OVERLAP_SECONDS = 60


@dataclass
class IngestResult:
    fetched: int = 0
    created: list[str] = field(default_factory=list)
    would_create: list[str] = field(default_factory=list)  # dry run only
    skipped_closed: int = 0
    skipped_label: int = 0
    skipped_existing: int = 0
    errors: list[str] = field(default_factory=list)


def briefing_id_for(ticket: Ticket) -> str:
    return f"{ticket.source}-{ticket.external_id}"


def _iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _with_overlap(cursor: str | None) -> str | None:
    if cursor is None:
        return None
    try:
        parsed = datetime.fromisoformat(cursor.replace("Z", "+00:00"))
    except ValueError:
        return None  # an unreadable cursor means "read everything again", which is safe
    return _iso(parsed - timedelta(seconds=OVERLAP_SECONDS))


def ingest_tickets(
    source: TicketSource,
    builder: BriefingBuilder,
    store: BriefingStore,
    cursors: CursorStore,
    *,
    cursor_key: str | None = None,
    label: str | None = None,
    include_closed: bool = False,
    dry_run: bool = False,
) -> IngestResult:
    """Read what changed since the last run and brief each open ticket once.

    Reading never writes to the ticket tool. A source failure propagates and leaves the
    cursor where it was, so the next run retries.
    """
    key = cursor_key or source.name
    tickets = source.fetch_updated(_with_overlap(cursors.get(key)))
    result = IngestResult(fetched=len(tickets))
    newest: str | None = None

    for ticket in tickets:  # oldest change first
        newest = ticket.updated_at
        if label and not ticket.has_label(label):
            result.skipped_label += 1
            continue
        if not ticket.is_open and not include_closed:
            result.skipped_closed += 1
            continue

        briefing_id = briefing_id_for(ticket)
        if store.exists(briefing_id):
            result.skipped_existing += 1
            continue
        if dry_run:
            result.would_create.append(briefing_id)
            continue

        try:
            briefing = builder.build(
                ticket.inquiry_text,
                Customer(plan=ticket.plan),
                ticket.log_text,
                briefing_id=briefing_id,
                origin=Origin(ticket.source, ticket.external_id, ticket.key, ticket.url),
            )
            store.add(briefing)
        except BriefingError as exc:
            logger.error("could not store briefing for %s", ticket.key, exc_info=True)
            result.errors.append(f"{ticket.key}: {exc}")
            continue
        result.created.append(briefing_id)

    if newest is not None and not dry_run:
        cursors.set(key, newest)
    return result
