"""Linear adapter: shared contract plus Linear-specific behaviour (GraphQL faked)."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from src.core.exceptions import TicketNotFound, TicketSourceError
from src.integrations.linear.client import LinearClient
from src.integrations.tickets.linear import LinearTicketSource
from src.integrations.tickets.models import Ticket
from tests.unit.integrations.tickets.contract import TicketSourceContract, contract_tickets


def to_node(ticket: Ticket) -> dict[str, Any]:
    """The GraphQL node Linear would return for a ticket."""
    return {
        "id": ticket.external_id,
        "identifier": ticket.key,
        "title": ticket.title,
        "description": ticket.body,
        "createdAt": ticket.created_at,
        "updatedAt": ticket.updated_at,
        "state": {"name": ticket.state, "type": "started" if ticket.is_open else "completed"},
        "priority": ticket.priority,
        "assignee": None,
        "labels": {"nodes": [{"name": label} for label in ticket.labels]},
        "url": ticket.url,
    }


class FakeLinear:
    """Answers the two GraphQL queries the adapter makes, like Linear would."""

    def __init__(self, tickets: list[Ticket]):
        self.tickets = tickets
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        variables = variables or {}
        self.calls.append((query, variables))
        if "GetIssue" in query:
            match = [t for t in self.tickets if t.external_id == variables["id"]]
            if not match:
                raise RuntimeError("Linear API error: [{'message': 'Entity not found: Issue'}]")
            return {"issue": to_node(match[0])}

        conditions = variables.get("filter", {}).get("and", [])
        found = sorted(
            self.tickets, key=lambda t: t.updated_at, reverse=True
        )  # Linear: newest first
        for cond in conditions:
            if "updatedAt" in cond:
                found = [t for t in found if t.updated_at > cond["updatedAt"]["gt"]]
        start = int(variables.get("after") or 0)
        size = variables.get("first", 50)
        page = found[start : start + size]
        more = start + size < len(found)
        return {
            "issues": {
                "nodes": [to_node(t) for t in page],
                "pageInfo": {"hasNextPage": more, "endCursor": str(start + size) if more else None},
            }
        }


def make_source(tickets: list[Ticket], **kwargs: Any) -> tuple[LinearTicketSource, FakeLinear]:
    client = LinearClient(api_key="test-key")
    fake = FakeLinear(tickets)
    client._query = fake  # type: ignore[method-assign]
    return LinearTicketSource(client, **kwargs), fake


class TestLinearContract(TicketSourceContract):
    source_name = "linear"

    def build(self, tickets):
        return make_source(tickets)[0]


class TestLinearBehaviour:
    def test_follows_pagination_until_every_page_is_read(self):
        source, fake = make_source(contract_tickets("linear"), page_size=2)
        result = source.fetch_updated(None)
        assert len(result) == 3
        assert len([c for c in fake.calls if "ListIssues" in c[0]]) == 2

    def test_restricts_to_one_team_when_configured(self):
        source, fake = make_source(contract_tickets("linear"), team_key="SUP")
        source.fetch_updated(None)
        conditions = fake.calls[0][1]["filter"]["and"]
        assert {"team": {"key": {"eq": "SUP"}}} in conditions

    def test_sends_the_cursor_as_an_updated_at_filter(self):
        source, fake = make_source(contract_tickets("linear"))
        source.fetch_updated("2026-10-05T02:00:00.000Z")
        conditions = fake.calls[0][1]["filter"]["and"]
        assert {"updatedAt": {"gt": "2026-10-05T02:00:00.000Z"}} in conditions

    def test_no_updated_at_filter_without_a_cursor(self):
        source, fake = make_source(contract_tickets("linear"))
        source.fetch_updated(None)
        assert not any("updatedAt" in c for c in fake.calls[0][1]["filter"]["and"])

    @pytest.mark.parametrize(
        ("state_type", "expected_open"),
        [
            ("triage", True),
            ("backlog", True),
            ("unstarted", True),
            ("started", True),
            ("completed", False),
            ("canceled", False),
        ],
    )
    def test_open_means_not_completed_or_canceled(self, state_type, expected_open):
        ticket = contract_tickets("linear")[0]
        node = to_node(ticket)
        node["state"] = {"name": "Whatever", "type": state_type}
        client = LinearClient(api_key="k")
        client._query = lambda q, v=None: {"issue": node}  # type: ignore[method-assign]
        assert LinearTicketSource(client).get(ticket.external_id).is_open is expected_open

    def test_missing_description_becomes_an_empty_body(self):
        ticket = contract_tickets("linear")[0]
        node = to_node(ticket)
        node["description"] = None
        client = LinearClient(api_key="k")
        client._query = lambda q, v=None: {"issue": node}  # type: ignore[method-assign]
        assert LinearTicketSource(client).get(ticket.external_id).body == ""

    def test_api_errors_become_ticket_source_errors(self):
        client = LinearClient(api_key="k")

        def boom(query, variables=None):
            raise RuntimeError("Linear API error: [{'message': 'rate limited'}]")

        client._query = boom  # type: ignore[method-assign]
        with pytest.raises(TicketSourceError, match="rate limited"):
            LinearTicketSource(client).fetch_updated(None)

    def test_network_errors_become_ticket_source_errors(self):
        client = LinearClient(api_key="k")

        def offline(query, variables=None):
            raise httpx.ConnectError("no route")

        client._query = offline  # type: ignore[method-assign]
        with pytest.raises(TicketSourceError):
            LinearTicketSource(client).fetch_updated(None)

    def test_not_found_is_distinguished_from_other_errors(self):
        source, _ = make_source([])
        with pytest.raises(TicketNotFound):
            source.get("nope")
