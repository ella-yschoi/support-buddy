"""Tests for the folder-drop inbox trigger."""

from __future__ import annotations

import itertools
from pathlib import Path

from src.core.briefing.inbox import process_inbox
from src.core.briefing.store import BriefingStore
from tests.unit.core.briefing.test_builder import feature_analysis, make_builder
from tests.unit.core.briefing.test_builder import policy as policy  # noqa: F401

EMAIL = (
    "From: jane@acme.com\n"
    "To: support@cloudsync.io\n"
    "Subject: How do I enable auto-backup?\n"
    "Date: Sat, 04 Oct 2026 08:00:00 +0000\n"
    "\n"
    "Hi, how do I set up auto-backup for my documents folder?\n"
)


def counter_ids():
    counter = itertools.count(1)
    return lambda: f"b-{next(counter)}"


def _setup(tmp_path: Path):
    inbox = tmp_path / "inbox"
    done = tmp_path / "done"
    inbox.mkdir()
    return inbox, done, BriefingStore(tmp_path / "b.db")


def test_eml_files_become_briefings_and_move_to_processed(tmp_path, kb_index, policy):
    inbox, done, store = _setup(tmp_path)
    (inbox / "ticket1.eml").write_text(EMAIL)
    builder = make_builder(kb_index, policy, analysis=feature_analysis(), id_factory=counter_ids())

    ids = process_inbox(builder, store, inbox, done, default_plan="pro")

    assert len(ids) == 1
    assert store.get(ids[0]).customer_plan == "pro"
    assert "auto-backup" in store.get(ids[0]).inquiry_text
    assert not (inbox / "ticket1.eml").exists()
    assert (done / "ticket1.eml").exists()


def test_empty_inbox_returns_no_ids(tmp_path, kb_index, policy):
    inbox, done, store = _setup(tmp_path)
    assert (
        process_inbox(make_builder(kb_index, policy, id_factory=counter_ids()), store, inbox, done)
        == []
    )


def test_non_eml_files_are_left_alone(tmp_path, kb_index, policy):
    inbox, done, store = _setup(tmp_path)
    (inbox / "notes.txt").write_text("hello")
    process_inbox(make_builder(kb_index, policy, id_factory=counter_ids()), store, inbox, done)
    assert (inbox / "notes.txt").exists()


def test_sidecar_log_file_is_attached(tmp_path, kb_index, policy):
    inbox, done, store = _setup(tmp_path)
    (inbox / "t.eml").write_text(EMAIL)
    (inbox / "t.log").write_text("2026-10-04T08:00:00 ERROR SYNC-002 upload failed")
    seen: dict[str, str] = {}

    def spy_logs(raw: str):
        seen["raw"] = raw
        from tests.unit.core.briefing.test_builder import log_insight

        return log_insight()

    builder = make_builder(kb_index, policy, analysis=feature_analysis(), id_factory=counter_ids())
    builder._analyze_logs = spy_logs  # noqa: SLF001
    process_inbox(builder, store, inbox, done)

    assert "SYNC-002" in seen["raw"]
    assert (done / "t.log").exists()


def test_undecodable_email_still_gets_a_briefing_and_does_not_abort_batch(
    tmp_path, kb_index, policy
):
    inbox, done, store = _setup(tmp_path)
    (inbox / "bad.eml").write_bytes(b"\xff\xfe\x00 not utf-8 \xff")
    (inbox / "good.eml").write_text(EMAIL)
    builder = make_builder(kb_index, policy, analysis=feature_analysis(), id_factory=counter_ids())

    ids = process_inbox(builder, store, inbox, done)
    assert len(ids) == 2
    assert not list(inbox.glob("*.eml"))


def test_redropped_email_is_not_processed_twice(tmp_path, kb_index, policy):
    inbox, done, store = _setup(tmp_path)
    builder = make_builder(kb_index, policy, analysis=feature_analysis(), id_factory=counter_ids())
    (inbox / "t.eml").write_text(EMAIL)
    first = process_inbox(builder, store, inbox, done)

    (inbox / "t.eml").write_text(EMAIL)  # e.g. a failed move left the file behind
    second = process_inbox(builder, store, inbox, done)

    assert len(first) == 1
    assert second == []
    assert len(store.list_queue()) == 1
    assert not list(inbox.glob("*.eml"))
