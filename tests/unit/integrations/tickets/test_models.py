"""Tests for the normalised Ticket model."""

from __future__ import annotations

from src.integrations.tickets.models import Ticket, plan_from_labels, split_body


def make_ticket(**overrides) -> Ticket:
    base = dict(
        source="linear",
        external_id="abc-123",
        key="SUP-7",
        title="Files stopped syncing",
        body="Since yesterday nothing syncs. SYNC-002.",
        url="https://linear.app/x/issue/SUP-7",
        created_at="2026-10-05T01:00:00.000Z",
        updated_at="2026-10-05T02:00:00.000Z",
        state="Todo",
        is_open=True,
        labels=("seed", "plan:pro"),
    )
    base.update(overrides)
    return Ticket(**base)


class TestPlanFromLabels:
    def test_reads_plan_label(self):
        assert plan_from_labels(("bug", "plan:enterprise")) == "enterprise"

    def test_is_case_insensitive_and_trims(self):
        assert plan_from_labels((" Plan: Pro ",)) == "pro"

    def test_unknown_when_missing_or_invalid(self):
        assert plan_from_labels(()) == "unknown"
        assert plan_from_labels(("plan:platinum",)) == "unknown"
        assert plan_from_labels(("pro",)) == "unknown"

    def test_first_valid_plan_wins(self):
        assert plan_from_labels(("plan:free", "plan:pro")) == "free"


class TestSplitBody:
    def test_no_fences_means_no_logs(self):
        assert split_body("Just text.") == ("Just text.", "")

    def test_fenced_block_becomes_logs_and_is_removed_from_text(self):
        body = "Sync fails.\n\n```\n2026-10-05 ERROR SYNC-002 upload failed\n```\n\nThanks"
        text, logs = split_body(body)
        assert "ERROR SYNC-002" in logs
        assert "```" not in text
        assert "Sync fails." in text and "Thanks" in text

    def test_language_tag_is_dropped(self):
        _, logs = split_body('```json\n[{"level": "ERROR"}]\n```')
        assert logs == '[{"level": "ERROR"}]'

    def test_multiple_blocks_are_joined_in_order(self):
        body = "a\n```\nfirst\n```\nb\n```\nsecond\n```"
        _, logs = split_body(body)
        assert logs == "first\nsecond"

    def test_unclosed_fence_is_left_as_text(self):
        text, logs = split_body("Look:\n```\nnever closed")
        assert logs == ""
        assert "never closed" in text

    def test_empty_body(self):
        assert split_body("") == ("", "")


class TestTicketProperties:
    def test_plan_comes_from_labels(self):
        assert make_ticket().plan == "pro"

    def test_inquiry_text_leads_with_the_title_as_a_subject_line(self):
        ticket = make_ticket(body="Body text here.")
        assert ticket.inquiry_text == "Subject: Files stopped syncing\n\nBody text here."

    def test_inquiry_text_excludes_log_blocks(self):
        ticket = make_ticket(body="Problem.\n```\nERROR boom\n```")
        assert "boom" not in ticket.inquiry_text
        assert ticket.log_text == "ERROR boom"

    def test_inquiry_text_without_body_is_just_the_subject(self):
        assert make_ticket(body="").inquiry_text == "Subject: Files stopped syncing"

    def test_has_label_is_case_insensitive(self):
        assert make_ticket().has_label("SEED")
        assert not make_ticket().has_label("other")
