"""Tests for FastAPI server endpoints."""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.server import app
from src.core.knowledge.engine import KnowledgeEngine


@pytest.fixture(autouse=True)
def setup_engine(tmp_path, sample_knowledge_dir):
    """Inject a fresh KnowledgeEngine with test data before each test."""
    import src.api.server as srv
    engine = KnowledgeEngine(persist_dir=str(tmp_path / "chroma"))
    engine.ingest_directory(sample_knowledge_dir)
    srv._engine = engine
    yield
    srv._engine = None


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["knowledge_docs"] > 0


class TestAnalyzeEndpoint:
    def test_analyze_keyword_mode(self, client):
        resp = client.post("/api/v1/analyze", json={
            "inquiry": "My files are not syncing",
            "use_ai": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "sync"
        assert len(data["checklist"]) > 0
        assert 0 <= data["confidence"] <= 1

    def test_analyze_ai_mode_without_key(self, client):
        with patch("src.api.server.ANTHROPIC_API_KEY", ""):
            resp = client.post("/api/v1/analyze", json={
                "inquiry": "test",
                "use_ai": True,
            })
            assert resp.status_code == 400


class TestLogAnalyzeEndpoint:
    def test_log_analyze_basic(self, client):
        logs = '[{"timestamp": "2024-01-15T10:00:00Z", "level": "ERROR", "message": "SYNC-002 failed"}]'
        resp = client.post("/api/v1/logs/analyze", json={"logs": logs})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["errors"]) > 0

    def test_log_analyze_empty(self, client):
        resp = client.post("/api/v1/logs/analyze", json={"logs": ""})
        assert resp.status_code == 400


class TestSearchEndpoint:
    def test_search_returns_results(self, client):
        resp = client.get("/api/v1/knowledge/search", params={"query": "sync"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0


class TestEmailEndpoint:
    def test_email_analyze(self, client):
        raw_email = (
            "From: test@example.com\n"
            "Subject: SYNC-002 error\n\n"
            "My files are not syncing, I see SYNC-002."
        )
        resp = client.post("/api/v1/email/analyze", json={"raw_email": raw_email})
        assert resp.status_code == 200
        data = resp.json()
        assert data["sender"] == "test@example.com"
        assert "SYNC-002" in data["error_codes"]
        assert data["analysis"]["category"] == "sync"
