"""Intercom conversations as a ticket source."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from html import unescape
from typing import Any

import httpx

from src.core.exceptions import TicketNotFound, TicketSourceError
from src.integrations.intercom.client import IntercomClient
from src.integrations.tickets.models import Ticket

DEFAULT_APP_URL = "https://app.intercom.com/a/inbox"
_MAX_TITLE = 100
_PRE = re.compile(r"<pre[^>]*>(.*?)</pre>", re.IGNORECASE | re.DOTALL)
_BREAK = re.compile(r"<\s*(?:br\s*/?|/p|/div|/li)\s*>", re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")
_BLANK_RUNS = re.compile(r"\n{3,}")


def html_to_text(html: str | None) -> str:
    """Plain text from a message. Pre-formatted blocks become fenced blocks, i.e. logs."""
    if not html:
        return ""
    text = _PRE.sub(lambda m: f"\n```\n{_TAG.sub('', m.group(1)).strip()}\n```\n", html)
    text = _BREAK.sub("\n", text)
    text = unescape(_TAG.sub("", text)).replace("\xa0", " ")
    return _BLANK_RUNS.sub("\n\n", text).strip()


def _iso(unix: int) -> str:
    return datetime.fromtimestamp(unix, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _unix(iso: str) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def _title(conversation: dict[str, Any], body: str) -> str:
    source = conversation.get("source") or {}
    chosen = (source.get("subject") or "").strip() or (conversation.get("title") or "").strip()
    if not chosen:
        lines = (ln.strip() for ln in body.splitlines())
        prose = next((ln for ln in lines if ln and ln != "```"), "")
        chosen = prose or "(no subject)"
    return chosen if len(chosen) <= _MAX_TITLE else chosen[: _MAX_TITLE - 1].rstrip() + "…"


class IntercomTicketSource:
    name = "intercom"

    def __init__(self, client: IntercomClient, app_url: str = DEFAULT_APP_URL, page_size: int = 50):
        self._client = client
        self._app_url = app_url.rstrip("/")
        self._page_size = page_size

    def fetch_updated(self, since: str | None) -> list[Ticket]:
        since_unix = _unix(since) if since else None
        found: list[dict[str, Any]] = []
        cursor: str | None = None
        try:
            while True:
                page, cursor = self._client.search_conversations(
                    since_unix, per_page=self._page_size, starting_after=cursor
                )
                found.extend(page)
                if not cursor:
                    break
        except httpx.HTTPError as exc:
            raise TicketSourceError(f"Intercom request failed: {exc}") from exc
        return sorted((self._to_ticket(c) for c in found), key=lambda t: t.updated_at)

    def get(self, external_id: str) -> Ticket:
        try:
            conversation = self._client.get_conversation(external_id)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise TicketNotFound(f"no Intercom conversation {external_id}") from exc
            raise TicketSourceError(f"Intercom request failed: {exc}") from exc
        except httpx.HTTPError as exc:
            raise TicketSourceError(f"Intercom request failed: {exc}") from exc
        return self._to_ticket(conversation)

    def _to_ticket(self, conversation: dict[str, Any]) -> Ticket:
        body = html_to_text((conversation.get("source") or {}).get("body"))
        tags = (conversation.get("tags") or {}).get("tags") or []
        conversation_id = str(conversation["id"])
        state = conversation.get("state") or "open"
        return Ticket(
            source="intercom",
            external_id=conversation_id,
            key=conversation_id,
            title=_title(conversation, body),
            body=body,
            url=f"{self._app_url}/conversation/{conversation_id}",
            created_at=_iso(conversation["created_at"]),
            updated_at=_iso(conversation["updated_at"]),
            state=state,
            is_open=state != "closed",
            labels=tuple(t["name"] for t in tags if t.get("name")),
            priority=2 if conversation.get("priority") == "priority" else 0,
        )
