"""Tests for ticket ingestion (in-memory source, fake analyzers, real trust layer)."""

from __future__ import annotations

import itertools

import pytest

from src.core.briefing.ingest import ingest_tickets
from src.core.briefing.store import BriefingStore
from src.core.exceptions import TicketSourceError
from src.core.policy.models import AutonomyLevel
from src.integrations.tickets.cursors import CursorStore
from src.integrations.tickets.memory import InMemoryTicketSource
from src.integrations.tickets.models import Ticket
from tests.unit.core.briefing.test_builder import feature_analysis, make_builder
from tests.unit.core.briefing.test_builder import policy as policy  # noqa: F401


def ticket(n: int, **overrides) -> Ticket:
    base = dict(
        source="memory",
        external_id=f"id-{n}",
        key=f"SUP-{n}",
        title=f"How do I enable auto-backup {n}?",
        body="Please explain.",
        url=f"https://example.test/SUP-{n}",
        created_at=f"2026-10-05T0{n}:00:00.000Z",
        updated_at=f"2026-10-05T0{n}:00:00.000Z",
        state="Todo",
        is_open=True,
        labels=("seed", "plan:pro"),
    )
    base.update(overrides)
    return Ticket(**base)


@pytest.fixture
def env(tmp_path, kb_index, policy):  # noqa: F811
    db = tmp_path / "b.db"
    counter = itertools.count(1)
    builder = make_builder(
        kb_index, policy, analysis=feature_analysis(), id_factory=lambda: f"gen-{next(counter)}"
    )
    return builder, BriefingStore(db), CursorStore(db)


def run(env, tickets, **kwargs):
    builder, store, cursors = env
    source = InMemoryTicketSource(tickets)
    kwargs.setdefault("cursor_key", "memory:test")
    return ingest_tickets(source, builder, store, cursors, **kwargs), source


def test_open_ticket_becomes_a_briefing_with_a_stable_id_and_origin(env):
    result, _ = run(env, [ticket(1)])
    assert result.created == ["memory-id-1"]
    briefing = env[1].get("memory-id-1")
    assert briefing.origin.source == "memory"
    assert briefing.origin.key == "SUP-1"
    assert briefing.origin.url == "https://example.test/SUP-1"
    assert briefing.customer_plan == "pro"
    assert briefing.inquiry_text.startswith("Subject: How do I enable auto-backup 1?")


def test_fenced_logs_in_the_ticket_reach_the_log_analyzer(env):
    seen = {}

    def spy(raw):
        seen["raw"] = raw
        from tests.unit.core.briefing.test_builder import log_insight

        return log_insight()

    env[0]._analyze_logs = spy  # noqa: SLF001
    run(env, [ticket(1, body="Fails.\n```\nERROR SYNC-002 boom\n```")])
    assert "SYNC-002 boom" in seen["raw"]


def test_closed_tickets_are_skipped_by_default(env):
    result, _ = run(env, [ticket(1, is_open=False, state="Done"), ticket(2)])
    assert result.created == ["memory-id-2"]
    assert result.skipped_closed == 1


def test_closed_tickets_can_be_included(env):
    result, _ = run(env, [ticket(1, is_open=False, state="Done")], include_closed=True)
    assert result.created == ["memory-id-1"]


def test_label_filter_keeps_unrelated_issues_out(env):
    result, _ = run(env, [ticket(1, labels=()), ticket(2)], label="seed")
    assert result.created == ["memory-id-2"]
    assert result.skipped_label == 1


def test_running_twice_never_briefs_a_ticket_twice(env):
    first, _ = run(env, [ticket(1), ticket(2)])
    second, _ = run(env, [ticket(1), ticket(2)])
    assert len(first.created) == 2
    assert second.created == []
    # Only the ticket inside the 60 s overlap window is read again; it is recognised.
    assert (second.fetched, second.skipped_existing) == (1, 1)
    assert len(env[1].list_queue()) == 2


def test_with_no_cursor_a_rerun_recognises_every_existing_ticket(env):
    builder, store, cursors = env
    run(env, [ticket(1), ticket(2)])
    cursors.set("memory:test", "2000-01-01T00:00:00.000Z")  # as if the cursor were lost
    again, _ = run(env, [ticket(1), ticket(2)])
    assert again.created == []
    assert again.skipped_existing == 2


def test_cursor_moves_to_the_newest_change_seen(env):
    run(env, [ticket(1), ticket(3), ticket(2)])
    assert env[2].get("memory:test") == "2026-10-05T03:00:00.000Z"


def test_cursor_advances_past_filtered_tickets_too(env):
    run(env, [ticket(1, labels=())], label="seed")
    assert env[2].get("memory:test") == "2026-10-05T01:00:00.000Z"


def test_next_run_asks_only_for_changes_since_the_cursor_with_a_safety_overlap(env):
    run(env, [ticket(2)])
    _, source = run(env, [ticket(2)])
    asked = []
    original = source.fetch_updated
    source.fetch_updated = lambda since: asked.append(since) or original(since)  # type: ignore[method-assign]
    ingest_tickets(source, env[0], env[1], env[2], cursor_key="memory:test")
    # cursor 02:00:00 minus the 60 s overlap
    assert asked == ["2026-10-05T01:59:00.000Z"]


def test_a_ticket_inside_the_overlap_window_is_still_picked_up(env):
    run(env, [ticket(2)])  # cursor = 02:00:00
    late = ticket(5, updated_at="2026-10-05T01:59:30.000Z", created_at="2026-10-05T01:59:30.000Z")
    result, _ = run(env, [late])
    assert result.created == ["memory-id-5"]


def test_dry_run_creates_nothing_and_keeps_the_cursor(env):
    result, _ = run(env, [ticket(1)], dry_run=True)
    assert result.would_create == ["memory-id-1"]
    assert result.created == []
    assert env[1].list_queue() == []
    assert env[2].get("memory:test") is None


def test_tickets_are_processed_oldest_first(env):
    result, _ = run(env, [ticket(3), ticket(1), ticket(2)])
    assert result.created == ["memory-id-1", "memory-id-2", "memory-id-3"]


def test_source_failure_propagates_and_leaves_the_cursor_alone(env):
    class Broken:
        name = "memory"

        def fetch_updated(self, since):
            raise TicketSourceError("down")

        def get(self, external_id):
            raise TicketSourceError("down")

    builder, store, cursors = env
    cursors.set("memory:test", "2026-10-05T01:00:00.000Z")
    with pytest.raises(TicketSourceError):
        ingest_tickets(Broken(), builder, store, cursors, cursor_key="memory:test")
    assert cursors.get("memory:test") == "2026-10-05T01:00:00.000Z"


def test_sensitive_tickets_still_get_a_briefing_but_no_draft(env):
    result, _ = run(env, [ticket(1, title="We suspect a data breach", body="Unauthorized logins.")])
    briefing = env[1].get(result.created[0])
    assert briefing.autonomy is AutonomyLevel.HUMAN_ONLY
    assert briefing.draft_body is None


def test_result_counts_add_up(env):
    result, _ = run(
        env,
        [ticket(1, is_open=False), ticket(2, labels=()), ticket(3)],
        label="seed",
    )
    assert result.fetched == 3
    assert len(result.created) + result.skipped_closed + result.skipped_label == 3
