"""Tests for the SQLite briefing store."""

from __future__ import annotations

import dataclasses

import pytest

from src.core.briefing.models import Briefing, CheckView, Citation, Hypothesis, Sufficiency
from src.core.briefing.store import BriefingStore
from src.core.exceptions import BriefingError, BriefingStateError
from src.core.models import InquiryCategory, Severity
from src.core.policy.models import AutonomyLevel


def make_briefing(
    id_: str = "b1",
    severity: Severity = Severity.MEDIUM,
    created_at: str = "2026-10-04T09:00:00",
    draft: str | None = "Hello there, please check your storage quota.",
) -> Briefing:
    return Briefing(
        id=id_,
        created_at=created_at,
        inquiry_text="Uploads fail",
        customer_plan="pro",
        summary="Uploads failing",
        category=InquiryCategory.SYNC,
        model_severity=severity,
        effective_severity=severity,
        hypotheses=(Hypothesis("Quota exceeded", ("ERROR SYNC-002",), ("SYNC-002",)),),
        citations=(Citation("doc-1", "SYNC-002: Upload Failed"),),
        checks=(CheckView("citations_exist", True, "1 sources found"),),
        verification_score=1.0,
        verification_passed=True,
        autonomy=AutonomyLevel.CONFIRM,
        autonomy_reasons=("Category 'sync' is not auto-eligible",),
        simulated=False,
        draft_body=draft,
        sufficiency=Sufficiency.SUFFICIENT,
        sufficiency_reasons=("Evidence found",),
    )


@pytest.fixture
def store(tmp_path):
    return BriefingStore(tmp_path / "briefings.db")


def test_add_then_get_round_trips_every_field(store):
    original = make_briefing()
    store.add(original)
    assert store.get("b1") == original


def test_get_unknown_id_raises(store):
    with pytest.raises(BriefingError):
        store.get("nope")


def test_queue_orders_by_severity_then_oldest_first(store):
    store.add(make_briefing("low-old", Severity.LOW, "2026-10-04T01:00:00"))
    store.add(make_briefing("crit", Severity.CRITICAL, "2026-10-04T05:00:00"))
    store.add(make_briefing("high-new", Severity.HIGH, "2026-10-04T08:00:00"))
    store.add(make_briefing("high-old", Severity.HIGH, "2026-10-04T02:00:00"))
    assert [b.id for b in store.list_queue()] == ["crit", "high-old", "high-new", "low-old"]


def test_queue_uses_effective_severity(store):
    base = make_briefing("floored", Severity.LOW)
    store.add(dataclasses.replace(base, effective_severity=Severity.CRITICAL))
    store.add(make_briefing("plain", Severity.HIGH))
    assert [b.id for b in store.list_queue()] == ["floored", "plain"]


def test_approve_records_final_text_and_edit_ratio(store):
    store.add(make_briefing())
    approved = store.approve("b1", "Hello there, please check your storage quota and plan.")
    assert approved.status == "approved"
    assert approved.approved_body.endswith("and plan.")
    assert 0.0 < approved.edit_ratio < 0.5
    assert store.get("b1").status == "approved"


def test_approving_unchanged_draft_has_zero_edit_ratio(store):
    briefing = make_briefing()
    store.add(briefing)
    assert store.approve("b1", briefing.draft_body).edit_ratio == 0.0


def test_approved_briefings_leave_the_queue(store):
    store.add(make_briefing("a"))
    store.add(make_briefing("b"))
    store.approve("a", "final")
    assert [b.id for b in store.list_queue()] == ["b"]


def test_approve_without_draft_stores_text_and_no_ratio(store):
    store.add(make_briefing(draft=None))
    approved = store.approve("b1", "Handled by phone")
    assert approved.approved_body == "Handled by phone"
    assert approved.edit_ratio is None


def test_approve_unknown_id_raises(store):
    with pytest.raises(BriefingError):
        store.approve("nope", "x")


def test_data_persists_across_store_instances(tmp_path):
    path = tmp_path / "b.db"
    BriefingStore(path).add(make_briefing())
    assert BriefingStore(path).get("b1").summary == "Uploads failing"


def test_adding_duplicate_id_raises(store):
    store.add(make_briefing())
    with pytest.raises(BriefingError):
        store.add(make_briefing())


def test_approving_twice_is_rejected_and_keeps_the_first_approval(store):
    store.add(make_briefing())
    store.approve("b1", "first")
    with pytest.raises(BriefingStateError):
        store.approve("b1", "second")
    assert store.get("b1").approved_body == "first"
