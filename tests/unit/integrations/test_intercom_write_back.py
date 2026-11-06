"""Intercom write-back: a private note, never a reply to the customer."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.integrations.intercom.client import IntercomClient
from src.integrations.intercom.write_back import IntercomWriteBack
from tests.unit.integrations.test_write_back import _make_briefing


def conversation_with_notes(*bodies: str) -> dict:
    return {
        "id": "777",
        "conversation_parts": {
            "conversation_parts": [{"part_type": "note", "body": b} for b in bodies]
        },
    }


def make(parts: dict | None = None) -> tuple[IntercomWriteBack, MagicMock]:
    client = MagicMock(spec=IntercomClient)
    client.get_conversation.return_value = parts or conversation_with_notes()
    client.add_note.return_value = {"id": "note-1"}
    return IntercomWriteBack(client, admin_id="admin-9"), client


class TestPrivateNote:
    def test_dry_run_is_the_default_and_writes_nothing(self):
        wb, client = make()
        result = wb.post_briefing_note("777", _make_briefing())
        assert result.dry_run and result.preview
        client.add_note.assert_not_called()

    def test_live_posts_one_note_as_the_configured_admin(self):
        wb, client = make()
        result = wb.post_briefing_note("777", _make_briefing(), dry_run=False)
        client.add_note.assert_called_once()
        conversation_id, admin_id, body = client.add_note.call_args.args
        assert (conversation_id, admin_id) == ("777", "admin-9")
        assert result.note_id == "note-1" and not result.dry_run
        assert "Hello, here is the fix." in body

    def test_note_names_the_routing_and_the_kb_references(self):
        wb, _ = make()
        preview = wb.post_briefing_note("777", _make_briefing()).preview
        assert "Files Not Syncing" in preview
        assert "confirm" in preview.lower()

    def test_already_posted_briefing_is_skipped(self):
        briefing = _make_briefing()
        wb, client = make(conversation_with_notes(f"old note Support Buddy briefing {briefing.id}"))
        result = wb.post_briefing_note("777", briefing, dry_run=False)
        assert result.already_posted
        client.add_note.assert_not_called()

    def test_text_from_the_customer_cannot_inject_html_into_the_note(self):
        briefing = _make_briefing(draft_body="<script>alert(1)</script> & done")
        wb, _ = make()
        preview = wb.post_briefing_note("777", briefing).preview
        assert "<script>" not in preview
        assert "&lt;script&gt;" in preview

    def test_an_admin_id_is_required(self):
        with pytest.raises(ValueError, match="INTERCOM_ADMIN_ID"):
            IntercomWriteBack(MagicMock(spec=IntercomClient), admin_id="")


class TestNeverMessagesTheCustomer:
    def test_the_client_only_ever_posts_notes(self):
        client = IntercomClient(access_token="t")
        sent: list[tuple] = []
        client._request = lambda m, p, b=None: sent.append((m, p, b)) or {}  # type: ignore[method-assign]
        client.add_note("777", "admin-9", "<p>hi</p>")
        method, path, body = sent[0]
        assert (method, path) == ("POST", "/conversations/777/reply")
        assert body["message_type"] == "note"

    def test_the_client_has_no_public_reply_method(self):
        public = [n for n in dir(IntercomClient) if n.startswith(("reply", "send", "comment"))]
        assert public == []
