"""The interface every ticket tool adapter implements."""

from __future__ import annotations

from typing import Protocol

from src.integrations.tickets.models import Ticket


class TicketSource(Protocol):
    name: str

    def fetch_updated(self, since: str | None) -> list[Ticket]:
        """Tickets changed strictly after `since` (ISO 8601), oldest change first.

        `None` means everything. Only normalised `Ticket`s are returned; never raw tool data.
        """
        ...

    def get(self, external_id: str) -> Ticket:
        """One ticket by the tool's id. Raises TicketNotFound when it does not exist."""
        ...
