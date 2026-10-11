"""Tests for LinearWriteBack (mocked LinearClient)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, call

import pytest

from src.core.briefing.models import (
    Briefing,
    CheckView,
    Citation,
    Hypothesis,
    Origin,
    Sufficiency,
)
from src.core.models import InquiryCategory, Severity
from src.core.policy.models import AutonomyLevel
from src.integrations.linear.write_back import LinearWriteBack, WriteBackResult


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_briefing(**kwargs) -> Briefing:
    defaults = dict(
        id="brief-1",
        created_at="2026-10-11T10:00:00Z",
        inquiry_text="Files not syncing",
        customer_plan="pro",
        summary="Sync issue on Pro",
        category=InquiryCategory.SYNC,
        model_severity=Severity.HIGH,
        effective_severity=Severity.HIGH,
        hypotheses=(Hypothesis("Network issue", ("log line",), ("KB ref",)),),
        citations=(Citation("doc-1", "Files Not Syncing"),),
        checks=(CheckView("citations_exist", True, "ok"),),
        verification_score=1.0,
        verification_passed=True,
        autonomy=AutonomyLevel.CONFIRM,
        autonomy_reasons=("Pro customer",),
        simulated=True,
        draft_body="Hello, here is the fix.",
        sufficiency=Sufficiency.SUFFICIENT,
        sufficiency_reasons=("KB hit",),
        origin=Origin("linear", "issue-42", "SUP-7", "https://linear.app/sup-7"),
    )
    defaults.update(kwargs)
    return Briefing(**defaults)


def _mock_client(
    viewer_id: str = "bot-user",
    comments: list[dict] | None = None,
    labels: list[dict] | None = None,
) -> MagicMock:
    client = MagicMock()
    client.get_viewer.return_value = {"id": viewer_id, "name": "Support Buddy Bot"}
    client.get_comments.return_value = comments or []
    client.list_labels.return_value = labels or []
    client.add_comment.return_value = "new-comment-id"
    client.create_label.return_value = "new-label-id"
    return client


# ── dry_run ───────────────────────────────────────────────────────────────────

class TestDryRun:
    def test_dry_run_does_not_call_add_comment(self):
        client = _mock_client()
        wb = LinearWriteBack(client)
        result = wb.post_briefing_note("issue-42", _make_briefing(), dry_run=True)
        client.add_comment.assert_not_called()
        assert result.dry_run is True
        assert result.comment_id is None

    def test_dry_run_returns_formatted_body(self):
        wb = LinearWriteBack(_mock_client())
        result = wb.post_briefing_note("issue-42", _make_briefing(), dry_run=True)
        assert result.preview is not None
        assert "Sync issue on Pro" in result.preview

    def test_live_run_calls_add_comment(self):
        client = _mock_client()
        wb = LinearWriteBack(client)
        result = wb.post_briefing_note("issue-42", _make_briefing(), dry_run=False)
        client.add_comment.assert_called_once()
        assert result.comment_id == "new-comment-id"
        assert result.dry_run is False


# ── loop prevention ───────────────────────────────────────────────────────────

class TestLoopPrevention:
    def test_skips_if_already_posted(self):
        marker = "<!-- support-buddy briefing:brief-1 -->"
        client = _mock_client(comments=[
            {"id": "c1", "body": f"AI Note\n{marker}", "created_at": "2026-10-11T09:00:00Z",
             "user_id": "bot-user", "user_name": "Bot"},
        ])
        wb = LinearWriteBack(client)
        result = wb.post_briefing_note("issue-42", _make_briefing(), dry_run=False)
        client.add_comment.assert_not_called()
        assert result.already_posted is True

    def test_does_not_skip_if_marker_is_for_different_briefing(self):
        client = _mock_client(comments=[
            {"id": "c1", "body": "<!-- support-buddy briefing:OTHER-ID -->",
             "created_at": "2026-10-11T09:00:00Z", "user_id": "bot-user", "user_name": "Bot"},
        ])
        wb = LinearWriteBack(client)
        result = wb.post_briefing_note("issue-42", _make_briefing(), dry_run=False)
        client.add_comment.assert_called_once()
        assert result.already_posted is False


# ── note format ───────────────────────────────────────────────────────────────

class TestNoteFormat:
    def _preview(self, **kwargs) -> str:
        wb = LinearWriteBack(_mock_client())
        result = wb.post_briefing_note("i", _make_briefing(**kwargs), dry_run=True)
        assert result.preview is not None
        return result.preview

    def test_note_contains_summary_and_severity(self):
        body = self._preview()
        assert "Sync issue on Pro" in body
        assert "high" in body.lower()

    def test_note_contains_autonomy(self):
        body = self._preview()
        assert "confirm" in body.lower()

    def test_note_contains_draft_preview(self):
        body = self._preview()
        assert "Hello, here is the fix." in body

    def test_note_contains_machine_readable_marker(self):
        body = self._preview()
        assert "<!-- support-buddy briefing:brief-1 -->" in body

    def test_note_omits_draft_when_none(self):
        body = self._preview(draft_body=None)
        assert "draft" not in body.lower() or "no draft" in body.lower()


# ── ensure_label ──────────────────────────────────────────────────────────────

class TestEnsureLabel:
    def test_uses_existing_label_without_creating(self):
        client = _mock_client(labels=[{"id": "lab-1", "name": "ai-briefed"}])
        wb = LinearWriteBack(client)
        result = wb.ensure_label("issue-42", "team-1", label_name="ai-briefed", dry_run=False)
        client.create_label.assert_not_called()
        client.add_label_to_issue.assert_called_once_with("issue-42", "lab-1")
        assert result.label_applied is True

    def test_creates_label_when_missing(self):
        client = _mock_client(labels=[])
        wb = LinearWriteBack(client)
        wb.ensure_label("issue-42", "team-1", label_name="ai-briefed", dry_run=False)
        client.create_label.assert_called_once()
        client.add_label_to_issue.assert_called_once_with("issue-42", "new-label-id")

    def test_dry_run_does_not_apply_label(self):
        client = _mock_client(labels=[{"id": "lab-1", "name": "ai-briefed"}])
        wb = LinearWriteBack(client)
        result = wb.ensure_label("issue-42", "team-1", dry_run=True)
        client.add_label_to_issue.assert_not_called()
        assert result.label_applied is False
        assert result.dry_run is True


# ── fetch_sent_reply ──────────────────────────────────────────────────────────

class TestFetchSentReply:
    def test_returns_latest_non_bot_comment(self):
        client = _mock_client(
            viewer_id="bot-99",
            comments=[
                {"id": "c1", "body": "AI note <!-- support-buddy -->",
                 "created_at": "2026-10-11T10:00:00Z", "user_id": "bot-99", "user_name": "Bot"},
                {"id": "c2", "body": "TSE reply here",
                 "created_at": "2026-10-11T11:00:00Z", "user_id": "tse-1", "user_name": "Alice"},
            ],
        )
        wb = LinearWriteBack(client)
        reply = wb.fetch_sent_reply("issue-42")
        assert reply is not None
        assert reply["body"] == "TSE reply here"

    def test_returns_none_when_only_bot_comments(self):
        client = _mock_client(
            viewer_id="bot-99",
            comments=[
                {"id": "c1", "body": "AI note",
                 "created_at": "2026-10-11T10:00:00Z", "user_id": "bot-99", "user_name": "Bot"},
            ],
        )
        wb = LinearWriteBack(client)
        assert wb.fetch_sent_reply("issue-42") is None

    def test_returns_none_when_no_comments(self):
        wb = LinearWriteBack(_mock_client())
        assert wb.fetch_sent_reply("issue-42") is None
