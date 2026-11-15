"""Intercom REST client. Only the calls Support Buddy needs, and no call that messages a customer.

API shapes follow Intercom's public documentation and have not been verified against a live
workspace yet. The API version and the regional base URL are configurable for that reason.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://api.intercom.io"  # EU: https://api.eu.intercom.io, AU: .au.
DEFAULT_API_VERSION = "2.14"


class IntercomClient:
    def __init__(
        self,
        access_token: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
    ) -> None:
        self._token = access_token or os.getenv("INTERCOM_ACCESS_TOKEN", "")
        if not self._token:
            raise ValueError("INTERCOM_ACCESS_TOKEN is not set")
        base = base_url or os.getenv("INTERCOM_API_BASE") or DEFAULT_BASE_URL
        self._base_url = base.rstrip("/")
        self._version = api_version or os.getenv("INTERCOM_API_VERSION") or DEFAULT_API_VERSION

    def __repr__(self) -> str:
        return f"IntercomClient(base_url={self._base_url!r}, version={self._version!r})"

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Intercom-Version": self._version,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _request(
        self, method: str, path: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        with httpx.Client() as client:
            response = client.request(
                method, self._base_url + path, headers=self.headers, json=body, timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    def search_conversations(
        self,
        updated_after: int | None,
        per_page: int = 50,
        starting_after: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Conversations updated after a unix time, newest first, plus the next page cursor."""
        query = {"field": "updated_at", "operator": ">", "value": updated_after or 0}
        pagination: dict[str, Any] = {"per_page": per_page}
        if starting_after:
            pagination["starting_after"] = starting_after
        data = self._request(
            "POST",
            "/conversations/search",
            {
                "query": {"operator": "AND", "value": [query]},
                "sort": {"field": "updated_at", "order": "descending"},
                "pagination": pagination,
            },
        )
        next_page = (data.get("pages") or {}).get("next") or {}
        return data.get("conversations", []), next_page.get("starting_after")

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        return self._request("GET", f"/conversations/{conversation_id}")

    def add_note(self, conversation_id: str, admin_id: str, html_body: str) -> dict[str, Any]:
        """Add a private note. Notes are internal; the customer never sees them.

        This is the only write the client offers. There is deliberately no method for a public
        reply: a human sends every customer-facing message.
        """
        return self._request(
            "POST",
            f"/conversations/{conversation_id}/reply",
            {
                "message_type": "note",
                "type": "admin",
                "admin_id": admin_id,
                "body": html_body,
            },
        )
