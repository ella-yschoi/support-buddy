"""In-memory ticket source: for tests, demos and as the reference for the adapter contract."""

from __future__ import annotations

from src.core.exceptions import TicketNotFound
from src.integrations.tickets.models import Ticket


class InMemoryTicketSource:
    def __init__(self, tickets: list[Ticket], name: str = "memory"):
        self.name = name
        self._tickets = {t.external_id: t for t in tickets}

    def fetch_updated(self, since: str | None) -> list[Ticket]:
        found = [t for t in self._tickets.values() if since is None or t.updated_at > since]
        return sorted(found, key=lambda t: t.updated_at)

    def get(self, external_id: str) -> Ticket:
        try:
            return self._tickets[external_id]
        except KeyError:
            raise TicketNotFound(f"no ticket {external_id}") from None
