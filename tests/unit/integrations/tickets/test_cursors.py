"""Tests for per-source sync cursors."""

from __future__ import annotations

from src.integrations.tickets.cursors import CursorStore


def test_unknown_key_has_no_cursor(tmp_path):
    assert CursorStore(tmp_path / "c.db").get("linear:SUP") is None


def test_set_then_get(tmp_path):
    store = CursorStore(tmp_path / "c.db")
    store.set("linear:SUP", "2026-10-05T02:00:00Z")
    assert store.get("linear:SUP") == "2026-10-05T02:00:00Z"


def test_set_overwrites(tmp_path):
    store = CursorStore(tmp_path / "c.db")
    store.set("k", "a")
    store.set("k", "b")
    assert store.get("k") == "b"


def test_keys_are_independent(tmp_path):
    store = CursorStore(tmp_path / "c.db")
    store.set("linear:SUP", "x")
    store.set("zendesk:main", "y")
    assert (store.get("linear:SUP"), store.get("zendesk:main")) == ("x", "y")


def test_persists_across_instances(tmp_path):
    path = tmp_path / "c.db"
    CursorStore(path).set("k", "v")
    assert CursorStore(path).get("k") == "v"


def test_shares_a_database_file_with_the_briefing_store(tmp_path):
    from src.core.briefing.store import BriefingStore

    path = tmp_path / "shared.db"
    BriefingStore(path)
    CursorStore(path).set("k", "v")
    assert BriefingStore(path).list_queue() == []
    assert CursorStore(path).get("k") == "v"
