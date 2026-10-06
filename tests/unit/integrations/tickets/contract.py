"""Contract every TicketSource adapter must satisfy.

A concrete test class subclasses `TicketSourceContract` and implements `build(tickets)`, which
returns an adapter whose underlying tool contains exactly those tickets (for a real adapter:
a faked HTTP layer; for the in-memory source: the list itself).
"""

from __future__ import annotations

import re

import pytest

from src.core.exceptions import TicketNotFound
from src.integrations.tickets.base import TicketSource
from src.integrations.tickets.models import VALID_PLANS, Ticket

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def contract_tickets(source: str) -> list[Ticket]:
    """Three tickets, deliberately given out of order, one of them closed."""
    return [
        Ticket(
            source=source,
            external_id="id-2",
            key="SUP-2",
            title="Webhook deliveries time out",
            body="Our endpoint times out.\n```\n02:58 ERROR API-002 timeout\n```",
            url="https://example.test/SUP-2",
            created_at="2026-10-05T01:00:00.000Z",
            updated_at="2026-10-05T03:00:00.000Z",
            state="In Progress",
            is_open=True,
            labels=("plan:enterprise", "seed"),
            priority=2,
        ),
        Ticket(
            source=source,
            external_id="id-1",
            key="SUP-1",
            title="How do I enable 2FA?",
            body="Steps please.",
            url="https://example.test/SUP-1",
            created_at="2026-10-05T00:30:00.000Z",
            updated_at="2026-10-05T01:00:00.000Z",
            state="Todo",
            is_open=True,
            labels=("plan:free",),
            priority=0,
        ),
        Ticket(
            source=source,
            external_id="id-3",
            key="SUP-3",
            title="Old resolved question",
            body="Resolved already.",
            url="https://example.test/SUP-3",
            created_at="2026-10-04T08:00:00.000Z",
            updated_at="2026-10-05T02:00:00.000Z",
            state="Done",
            is_open=False,
            labels=(),
            priority=0,
        ),
    ]


class TicketSourceContract:
    source_name = "contract"

    def build(self, tickets: list[Ticket]) -> TicketSource:  # pragma: no cover - overridden
        raise NotImplementedError

    @pytest.fixture
    def tickets(self) -> list[Ticket]:
        return contract_tickets(self.source_name)

    @pytest.fixture
    def source(self, tickets: list[Ticket]) -> TicketSource:
        return self.build(tickets)

    def test_fetch_without_cursor_returns_everything_oldest_change_first(self, source):
        result = source.fetch_updated(None)
        assert [t.external_id for t in result] == ["id-1", "id-3", "id-2"]

    def test_fetch_returns_only_normalised_tickets(self, source):
        assert all(isinstance(t, Ticket) for t in source.fetch_updated(None))

    def test_cursor_is_exclusive(self, source):
        result = source.fetch_updated("2026-10-05T02:00:00.000Z")
        assert [t.external_id for t in result] == ["id-2"]

    def test_cursor_after_the_newest_change_returns_nothing(self, source):
        assert source.fetch_updated("2026-10-06T00:00:00.000Z") == []

    def test_closed_tickets_are_reported_as_closed_not_hidden(self, source):
        closed = [t for t in source.fetch_updated(None) if not t.is_open]
        assert [t.external_id for t in closed] == ["id-3"]

    def test_get_returns_the_same_normalised_ticket(self, source, tickets):
        expected = next(t for t in tickets if t.external_id == "id-2")
        assert source.get("id-2") == expected

    def test_get_unknown_raises_ticket_not_found(self, source):
        with pytest.raises(TicketNotFound):
            source.get("does-not-exist")

    def test_every_ticket_has_the_fields_the_pipeline_needs(self, source):
        for ticket in source.fetch_updated(None):
            assert ticket.source == self.source_name
            assert ticket.external_id and ticket.key and ticket.title and ticket.url
            assert ISO.match(ticket.created_at) and ISO.match(ticket.updated_at)
            assert isinstance(ticket.labels, tuple)
            assert ticket.plan in (*VALID_PLANS, "unknown")

    def test_plan_is_derived_from_labels(self, source):
        plans = {t.external_id: t.plan for t in source.fetch_updated(None)}
        assert plans == {"id-1": "free", "id-2": "enterprise", "id-3": "unknown"}

    def test_log_blocks_survive_normalisation(self, source):
        assert "API-002" in source.get("id-2").log_text

    def test_the_adapter_names_itself(self, source):
        assert source.name == self.source_name
