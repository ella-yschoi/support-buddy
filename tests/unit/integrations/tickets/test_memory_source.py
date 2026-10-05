"""The in-memory source is the reference implementation of the contract."""

from __future__ import annotations

from src.integrations.tickets.memory import InMemoryTicketSource
from tests.unit.integrations.tickets.contract import TicketSourceContract


class TestInMemoryTicketSource(TicketSourceContract):
    source_name = "memory"

    def build(self, tickets):
        return InMemoryTicketSource(tickets, name=self.source_name)
