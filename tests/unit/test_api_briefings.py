"""Tests for briefing and policy endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api import briefings as briefings_api
from src.api.server import app
from src.core.briefing.factory import build_local_builder
from src.core.briefing.store import BriefingStore
from src.core.knowledge.engine import KnowledgeEngine


@pytest.fixture
def client(tmp_path, sample_knowledge_dir):
    engine = KnowledgeEngine(persist_dir=str(tmp_path / "chroma"))
    engine.ingest_directory(sample_knowledge_dir)
    builder = build_local_builder(engine, knowledge_dir=sample_knowledge_dir)
    store = BriefingStore(tmp_path / "b.db")
    app.dependency_overrides[briefings_api.get_builder] = lambda: builder
    app.dependency_overrides[briefings_api.get_store] = lambda: store
    yield TestClient(app)
    app.dependency_overrides.clear()


def create(client, inquiry="How do I set up auto-backup?", plan="pro", logs=""):
    return client.post("/api/v1/briefings", json={"inquiry": inquiry, "plan": plan, "logs": logs})


def test_create_briefing_returns_full_briefing(client):
    resp = create(client)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"]
    assert data["autonomy"] in {"auto", "confirm", "human_only"}
    assert data["status"] == "ready"
    assert 0.0 <= data["verification_score"] <= 1.0
    assert isinstance(data["checks"], list) and data["checks"]
    assert data["sufficiency"] in {"sufficient", "insufficient"}


def test_sensitive_inquiry_is_human_only_without_draft(client):
    data = create(client, inquiry="We think we had a data breach").json()
    assert data["autonomy"] == "human_only"
    assert data["draft_body"] is None
    assert any("breach" in r for r in data["autonomy_reasons"])


def test_blank_inquiry_is_rejected(client):
    assert create(client, inquiry="   ").status_code == 422


def test_unknown_plan_value_is_rejected(client):
    assert create(client, plan="platinum").status_code == 422


def test_get_briefing_by_id(client):
    created = create(client).json()
    resp = client.get(f"/api/v1/briefings/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_unknown_briefing_is_404(client):
    assert client.get("/api/v1/briefings/nope").status_code == 404


def test_queue_lists_ready_briefings_most_severe_first(client):
    create(client, inquiry="How do I set up auto-backup?")
    create(client, inquiry="All of our files are gone, data loss everywhere")
    queue = client.get("/api/v1/briefings").json()
    assert len(queue) == 2
    assert queue[0]["effective_severity"] == "critical"


def test_approve_records_edit_and_removes_from_queue(client):
    created = create(client).json()
    resp = client.post(
        f"/api/v1/briefings/{created['id']}/approve", json={"final_body": "Edited reply."}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body["approved_body"] == "Edited reply."
    assert client.get("/api/v1/briefings").json() == []


def test_approve_unknown_briefing_is_404(client):
    resp = client.post("/api/v1/briefings/nope/approve", json={"final_body": "x"})
    assert resp.status_code == 404


def test_approve_requires_non_empty_text(client):
    created = create(client).json()
    resp = client.post(f"/api/v1/briefings/{created['id']}/approve", json={"final_body": " "})
    assert resp.status_code == 422


def test_policy_endpoint_exposes_rules_read_only(client):
    data = client.get("/api/v1/policy").json()
    assert data["auto_send_enabled"] is False
    assert "breach" in data["human_only_keywords"]
    assert client.post("/api/v1/policy", json={}).status_code == 405
