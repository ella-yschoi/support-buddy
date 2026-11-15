"""Intercom adapter: shared contract plus Intercom-specific behaviour (HTTP faked).

The fake mirrors the Intercom REST shapes as documented (version 2.x). It has not been checked
against a live workspace yet.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest

from src.core.exceptions import TicketNotFound, TicketSourceError
from src.integrations.intercom.client import IntercomClient
from src.integrations.tickets.intercom import IntercomTicketSource
from src.integrations.tickets.models import Ticket
from tests.unit.integrations.tickets.contract import TicketSourceContract, contract_tickets


def to_unix(iso: str) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def to_html(body: str) -> str:
    """How a message with a pasted log block arrives: prose in <p>, logs in <pre>."""
    parts = re.split(r"```[^\n]*\n(.*?)\n?```", body, flags=re.DOTALL)
    html = ""
    for i, part in enumerate(parts):
        if i % 2:
            html += f"<pre>{part}</pre>"
        elif part.strip():
            html += "<p>" + part.strip().replace("\n", "<br/>") + "</p>"
    return html


def to_conversation(ticket: Ticket) -> dict[str, Any]:
    """The conversation object Intercom would return for a ticket."""
    return {
        "type": "conversation",
        "id": ticket.external_id,
        "created_at": to_unix(ticket.created_at),
        "updated_at": to_unix(ticket.updated_at),
        "state": "open" if ticket.is_open else "closed",
        "title": ticket.title,
        "source": {"type": "conversation", "body": to_html(ticket.body), "subject": ""},
        "tags": {"type": "tag.list", "tags": [{"type": "tag", "name": n} for n in ticket.labels]},
        "priority": "not_priority",
    }


class FakeIntercom:
    """Answers the search and get calls the adapter makes, like Intercom would."""

    def __init__(self, tickets: list[Ticket]):
        self.tickets = tickets
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def __call__(
        self, method: str, path: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        self.calls.append((method, path, body))
        if method == "GET" and path.startswith("/conversations/"):
            wanted = path.rsplit("/", 1)[1]
            match = [t for t in self.tickets if t.external_id == wanted]
            if not match:
                raise httpx.HTTPStatusError(
                    "not found",
                    request=httpx.Request(method, path),
                    response=httpx.Response(404, request=httpx.Request(method, path)),
                )
            return to_conversation(match[0])

        assert method == "POST" and path == "/conversations/search"
        assert body is not None
        found = sorted(self.tickets, key=lambda t: t.updated_at, reverse=True)
        query = body["query"]
        filters = query["value"] if query.get("operator") == "AND" else [query]
        for f in filters:
            if f["field"] == "updated_at":
                found = [t for t in found if to_unix(t.updated_at) > f["value"]]
        pagination = body.get("pagination", {})
        start = int(pagination.get("starting_after") or 0)
        size = pagination.get("per_page", 20)
        page = found[start : start + size]
        more = start + size < len(found)
        result: dict[str, Any] = {
            "type": "conversation.list",
            "conversations": [to_conversation(t) for t in page],
            "pages": {"type": "pages"},
        }
        if more:
            result["pages"]["next"] = {"starting_after": str(start + size)}
        return result


def make_source(tickets: list[Ticket], **kwargs: Any) -> tuple[IntercomTicketSource, FakeIntercom]:
    client = IntercomClient(access_token="test-token")
    fake = FakeIntercom(tickets)
    client._request = fake  # type: ignore[method-assign]
    return IntercomTicketSource(client, **kwargs), fake


class TestIntercomContract(TicketSourceContract):
    source_name = "intercom"

    def build(self, tickets):
        return make_source(tickets)[0]

    def test_get_returns_the_same_normalised_ticket(self, source, tickets):
        expected = next(t for t in tickets if t.external_id == "id-2")
        got = source.get("id-2")
        # Intercom has no readable key, so the conversation id stands in for it.
        assert got.key == expected.external_id
        assert (got.external_id, got.title, got.labels, got.state) == (
            expected.external_id, expected.title, expected.labels, "open"
        )


class TestIntercomSpecifics:
    def conversation(self, **over: Any) -> dict[str, Any]:
        base = {
            "id": "777",
            "created_at": 1_788_000_000,
            "updated_at": 1_788_000_600,
            "state": "open",
            "title": None,
            "source": {
                "body": "<p>Sync is stuck.</p><p>Error&nbsp;API-004<br/>on retry</p>",
                "subject": "",
            },
            "tags": {"tags": [{"name": "ai-triage"}, {"name": "plan:pro"}]},
            "priority": "not_priority",
        }
        base.update(over)
        return base

    def source_for(self, conversation: dict[str, Any]) -> IntercomTicketSource:
        client = IntercomClient(access_token="t")
        client._request = lambda m, p, b=None: conversation  # type: ignore[method-assign]
        return IntercomTicketSource(client, app_url="https://app.intercom.com/a/inbox/abc")

    def test_html_is_stripped_and_entities_decoded(self):
        ticket = self.source_for(self.conversation()).get("777")
        assert "<p>" not in ticket.body and "<br" not in ticket.body
        assert "Sync is stuck." in ticket.body
        assert "Error API-004" in ticket.body.replace("\xa0", " ")

    def test_title_comes_from_the_subject_then_the_conversation_title_then_the_first_line(self):
        with_subject = self.conversation(source={"body": "<p>body</p>", "subject": "Subject line"})
        assert self.source_for(with_subject).get("777").title == "Subject line"

        with_title = self.conversation(title="Named in Intercom")
        assert self.source_for(with_title).get("777").title == "Named in Intercom"

        assert self.source_for(self.conversation()).get("777").title == "Sync is stuck."

    def test_long_first_line_makes_a_short_title(self):
        long_line = "word " * 80
        conv = self.conversation(source={"body": f"<p>{long_line}</p>", "subject": ""})
        title = self.source_for(conv).get("777").title
        assert len(title) <= 100

    def test_key_is_the_conversation_id_and_url_points_into_the_inbox(self):
        ticket = self.source_for(self.conversation()).get("777")
        assert ticket.key == "777"
        assert ticket.url.endswith("/conversation/777")

    def test_tags_become_labels_and_plan_comes_from_a_plan_tag(self):
        ticket = self.source_for(self.conversation()).get("777")
        assert ticket.labels == ("ai-triage", "plan:pro")
        assert ticket.plan == "pro"
        assert ticket.has_label("AI-Triage")

    def test_state_maps_to_open_or_closed(self):
        assert self.source_for(self.conversation(state="open")).get("777").is_open
        assert self.source_for(self.conversation(state="snoozed")).get("777").is_open
        assert not self.source_for(self.conversation(state="closed")).get("777").is_open

    def test_timestamps_are_iso_8601_utc(self):
        ticket = self.source_for(self.conversation()).get("777")
        assert ticket.updated_at == datetime.fromtimestamp(1_788_000_600, timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z"
        )

    def test_a_conversation_without_a_body_still_normalises(self):
        conv = self.conversation(source={"body": None, "subject": None}, title=None)
        ticket = self.source_for(conv).get("777")
        assert ticket.title  # never empty: the pipeline needs a subject
        assert ticket.body == ""

    def test_priority_is_zero_when_intercom_does_not_flag_it(self):
        assert self.source_for(self.conversation()).get("777").priority == 0
        assert self.source_for(self.conversation(priority="priority")).get("777").priority == 2


class TestIntercomRequests:
    def test_search_filters_on_updated_at_in_unix_seconds(self):
        source, fake = make_source(contract_tickets("intercom"))
        source.fetch_updated("2026-10-05T02:00:00.000Z")
        _, _, body = fake.calls[0]
        assert body is not None
        query = body["query"]
        filters = query["value"] if query.get("operator") == "AND" else [query]
        updated = next(f for f in filters if f["field"] == "updated_at")
        assert updated["operator"] == ">"
        assert updated["value"] == to_unix("2026-10-05T02:00:00.000Z")

    def test_pages_are_followed_until_the_cursor_runs_out(self):
        source, fake = make_source(contract_tickets("intercom"), page_size=2)
        assert len(source.fetch_updated(None)) == 3
        assert len(fake.calls) == 2

    def test_http_failure_becomes_ticket_source_error(self):
        client = IntercomClient(access_token="t")

        def boom(*a: Any, **k: Any) -> dict[str, Any]:
            raise httpx.ConnectError("down")

        client._request = boom  # type: ignore[method-assign]
        with pytest.raises(TicketSourceError):
            IntercomTicketSource(client).fetch_updated(None)

    def test_unknown_conversation_raises_ticket_not_found(self):
        source, _ = make_source([])
        with pytest.raises(TicketNotFound):
            source.get("nope")

    def test_client_requires_a_token(self, monkeypatch):
        monkeypatch.delenv("INTERCOM_ACCESS_TOKEN", raising=False)
        with pytest.raises(ValueError, match="INTERCOM_ACCESS_TOKEN"):
            IntercomClient()

    def test_client_sends_bearer_auth_and_a_pinned_api_version(self):
        client = IntercomClient(access_token="secret-token")
        assert client.headers["Authorization"] == "Bearer secret-token"
        assert client.headers["Intercom-Version"]
        assert "secret-token" not in repr(client)
