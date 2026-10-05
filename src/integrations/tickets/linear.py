"""Linear as a ticket source."""

from __future__ import annotations

import httpx

from src.core.exceptions import TicketNotFound, TicketSourceError
from src.integrations.linear.client import LinearClient, LinearIssue
from src.integrations.tickets.models import Ticket

_CLOSED_STATE_TYPES = frozenset({"completed", "canceled"})


class LinearTicketSource:
    name = "linear"

    def __init__(self, client: LinearClient, team_key: str | None = None, page_size: int = 50):
        self._client = client
        self._team_key = team_key
        self._page_size = page_size

    def fetch_updated(self, since: str | None) -> list[Ticket]:
        try:
            issues = self._client.list_issues(
                updated_after=since, team_key=self._team_key, page_size=self._page_size
            )
        except (RuntimeError, httpx.HTTPError) as exc:
            raise TicketSourceError(f"Linear request failed: {exc}") from exc
        # Linear returns newest first; the cursor logic needs oldest change first.
        return sorted((self._to_ticket(i) for i in issues), key=lambda t: t.updated_at)

    def get(self, external_id: str) -> Ticket:
        try:
            issue = self._client.get_issue(external_id)
        except RuntimeError as exc:
            if "not found" in str(exc).lower():
                raise TicketNotFound(f"no Linear issue {external_id}") from exc
            raise TicketSourceError(f"Linear request failed: {exc}") from exc
        except httpx.HTTPError as exc:
            raise TicketSourceError(f"Linear request failed: {exc}") from exc
        return self._to_ticket(issue)

    @staticmethod
    def _to_ticket(issue: LinearIssue) -> Ticket:
        return Ticket(
            source="linear",
            external_id=issue.id,
            key=issue.identifier,
            title=issue.title,
            body=issue.description or "",
            url=issue.url,
            created_at=issue.created_at,
            updated_at=issue.updated_at,
            state=issue.state,
            is_open=issue.state_type not in _CLOSED_STATE_TYPES,
            labels=tuple(issue.labels),
            priority=issue.priority,
        )
