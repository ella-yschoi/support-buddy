"""Access control, abuse limits and path safety for the public-facing API."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import src.api.server as srv
from src import config
from src.api import security
from src.api.security import Access, DailyBudget, SlidingWindowLimiter, check_access, client_ip
from src.api.server import app
from src.core.models import DraftResponse
from tests.unit.core.conftest import make_analysis

SECRET = "s3cret-value-for-tests"
GOOD = {"Authorization": f"Bearer {SECRET}"}


class TestCheckAccess:
    def call(self, **kw):
        base = dict(
            secret=SECRET,
            app_env="production",
            method="GET",
            path="/api/v1/briefings",
            auth_header="",
        )
        base.update(kw)
        return check_access(**base)

    def test_correct_bearer_is_allowed(self):
        assert self.call(auth_header=f"Bearer {SECRET}") is Access.ALLOWED

    @pytest.mark.parametrize(
        "header", ["", "Bearer wrong", SECRET, f"bearer {SECRET}", f"Bearer {SECRET} "]
    )
    def test_anything_else_is_unauthorized(self, header):
        assert self.call(auth_header=header) is Access.UNAUTHORIZED

    def test_health_is_always_public(self):
        assert self.call(path="/api/v1/health") is Access.ALLOWED

    def test_cors_preflight_needs_no_credentials(self):
        assert self.call(method="OPTIONS") is Access.ALLOWED

    def test_no_secret_is_fine_for_local_development(self):
        assert self.call(secret="", app_env="development") is Access.ALLOWED

    def test_no_secret_in_production_is_a_misconfiguration_not_open_access(self):
        assert self.call(secret="", app_env="production") is Access.MISCONFIGURED

    def test_health_stays_reachable_when_misconfigured(self):
        assert self.call(secret="", app_env="production", path="/api/v1/health") is Access.ALLOWED


class TestSlidingWindowLimiter:
    def test_blocks_once_the_limit_is_reached_within_the_window(self):
        now = [0.0]
        limiter = SlidingWindowLimiter(limit=3, window_s=60, clock=lambda: now[0])
        for _ in range(3):
            assert not limiter.blocked("ip")
            limiter.record("ip")
        assert limiter.blocked("ip")

    def test_old_events_expire(self):
        now = [0.0]
        limiter = SlidingWindowLimiter(limit=2, window_s=60, clock=lambda: now[0])
        limiter.record("ip")
        limiter.record("ip")
        assert limiter.blocked("ip")
        now[0] = 61.0
        assert not limiter.blocked("ip")

    def test_keys_are_independent(self):
        limiter = SlidingWindowLimiter(limit=1, window_s=60, clock=lambda: 0.0)
        limiter.record("a")
        assert limiter.blocked("a") and not limiter.blocked("b")

    def test_memory_is_bounded_by_dropping_idle_keys(self):
        now = [0.0]
        limiter = SlidingWindowLimiter(limit=5, window_s=10, clock=lambda: now[0])
        for i in range(100):
            limiter.record(f"ip-{i}")
        now[0] = 100.0
        limiter.blocked("anything")
        assert limiter.tracked_keys() == 0


class TestDailyBudget:
    def test_allows_up_to_the_limit_then_refuses(self):
        budget = DailyBudget(limit=2, today=lambda: date(2026, 10, 6))
        assert budget.try_take() and budget.try_take()
        assert not budget.try_take()
        assert budget.remaining == 0

    def test_resets_on_a_new_day(self):
        day = [date(2026, 10, 6)]
        budget = DailyBudget(limit=1, today=lambda: day[0])
        assert budget.try_take() and not budget.try_take()
        day[0] = date(2026, 10, 7)
        assert budget.try_take()

    def test_zero_limit_disables_the_feature(self):
        assert not DailyBudget(limit=0, today=lambda: date(2026, 10, 6)).try_take()


class TestClientIp:
    def request(self, headers, host="10.0.0.1"):
        return SimpleNamespace(headers=headers, client=SimpleNamespace(host=host))

    def test_prefers_the_ip_fly_reports(self):
        assert client_ip(self.request({"Fly-Client-IP": "203.0.113.7"})) == "203.0.113.7"

    def test_ignores_a_spoofable_forwarded_for_header(self):
        assert client_ip(self.request({"X-Forwarded-For": "1.2.3.4"})) == "10.0.0.1"

    def test_falls_back_to_the_socket_address(self):
        assert client_ip(self.request({})) == "10.0.0.1"

    def test_unknown_when_there_is_no_client(self):
        assert client_ip(SimpleNamespace(headers={}, client=None)) == "unknown"


# ── Through the real app ─────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    security.reset_state()
    monkeypatch.setattr(srv, "_engine", SimpleNamespace(doc_count=lambda: 3))
    yield
    security.reset_state()


def configure(monkeypatch, *, secret=SECRET, env="production", ai_limit=100, anthropic="key"):
    monkeypatch.setattr(config, "API_SECRET_KEY", secret)
    monkeypatch.setattr(config, "APP_ENV", env)
    monkeypatch.setattr(config, "AI_DAILY_LIMIT", ai_limit)
    monkeypatch.setattr(srv, "ANTHROPIC_API_KEY", anthropic)


@pytest.fixture
def client():
    return TestClient(app)


class TestMiddleware:
    def test_requests_without_the_key_are_rejected(self, client, monkeypatch):
        configure(monkeypatch)
        assert client.get("/api/v1/policy").status_code == 401

    def test_a_wrong_key_is_rejected_without_revealing_the_right_one(self, client, monkeypatch):
        configure(monkeypatch)
        response = client.get("/api/v1/policy", headers={"Authorization": "Bearer nope"})
        assert response.status_code == 401
        assert SECRET not in response.text

    def test_the_right_key_is_accepted(self, client, monkeypatch):
        configure(monkeypatch)
        assert client.get("/api/v1/policy", headers=GOOD).status_code == 200

    def test_health_needs_no_key(self, client, monkeypatch):
        configure(monkeypatch)
        assert client.get("/api/v1/health").status_code == 200

    def test_browser_preflight_passes_without_a_key(self, client, monkeypatch):
        configure(monkeypatch)
        response = client.options(
            "/api/v1/briefings",
            headers={
                "Origin": "https://support-buddy.pages.dev",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        assert response.status_code == 200

    def test_production_without_a_secret_refuses_to_serve_data(self, client, monkeypatch):
        configure(monkeypatch, secret="", env="production")
        assert client.get("/api/v1/policy").status_code == 503
        assert client.get("/api/v1/health").status_code == 200

    def test_local_development_without_a_secret_stays_open(self, client, monkeypatch):
        configure(monkeypatch, secret="", env="development")
        assert client.get("/api/v1/policy").status_code == 200

    def test_repeated_wrong_keys_lock_the_address_out_even_for_the_right_key(
        self, client, monkeypatch
    ):
        configure(monkeypatch)
        for _ in range(security.FAILED_AUTH_LIMIT):
            assert (
                client.get("/api/v1/policy", headers={"Authorization": "Bearer guess"}).status_code
                == 401
            )
        assert client.get("/api/v1/policy", headers=GOOD).status_code == 429

    def test_a_lockout_does_not_affect_another_address(self, client, monkeypatch):
        configure(monkeypatch)
        for _ in range(security.FAILED_AUTH_LIMIT):
            client.get(
                "/api/v1/policy",
                headers={"Authorization": "Bearer guess", "Fly-Client-IP": "198.51.100.1"},
            )
        other = client.get("/api/v1/policy", headers={**GOOD, "Fly-Client-IP": "198.51.100.2"})
        assert other.status_code == 200

    def test_successful_requests_never_count_toward_the_lockout(self, client, monkeypatch):
        configure(monkeypatch)
        for _ in range(security.FAILED_AUTH_LIMIT + 5):
            assert client.get("/api/v1/policy", headers=GOOD).status_code == 200


class FakeAnalyzer:
    def __init__(self, *args, **kwargs):
        pass

    def analyze(self, text):
        return make_analysis()


class FakeDrafter:
    def __init__(self, *args, **kwargs):
        pass

    def draft(self, text, analysis):
        return DraftResponse(
            body="b",
            citations=[],
            confidence=0.5,
            needs_escalation=False,
            suggested_internal_note="",
        )


@pytest.fixture
def fake_ai(monkeypatch):
    monkeypatch.setattr("src.core.analyzer.ai_inquiry.AIInquiryAnalyzer", FakeAnalyzer)
    monkeypatch.setattr("src.core.responder.drafter.ResponseDrafter", FakeDrafter)


class TestAiBudget:
    def draft(self, client):
        return client.post("/api/v1/draft-response", json={"inquiry": "help"}, headers=GOOD)

    def test_ai_calls_stop_at_the_daily_limit(self, client, monkeypatch, fake_ai):
        configure(monkeypatch, ai_limit=2)
        assert self.draft(client).status_code == 200
        assert self.draft(client).status_code == 200
        blocked = self.draft(client)
        assert blocked.status_code == 429
        assert "daily" in blocked.json()["detail"].lower()

    def test_a_zero_limit_turns_ai_off(self, client, monkeypatch, fake_ai):
        configure(monkeypatch, ai_limit=0)
        assert self.draft(client).status_code == 429

    def test_ai_analysis_is_counted_too(self, client, monkeypatch, fake_ai):
        configure(monkeypatch, ai_limit=1)
        first = client.post(
            "/api/v1/analyze", json={"inquiry": "sync broken", "use_ai": True}, headers=GOOD
        )
        second = client.post(
            "/api/v1/analyze", json={"inquiry": "sync broken", "use_ai": True}, headers=GOOD
        )
        assert (first.status_code, second.status_code) == (200, 429)

    def test_free_keyword_analysis_never_touches_the_budget(self, client, monkeypatch, fake_ai):
        configure(monkeypatch, ai_limit=1)
        monkeypatch.setattr(
            srv,
            "InquiryAnalyzer",
            lambda engine: SimpleNamespace(classify=lambda text: make_analysis()),
        )
        for _ in range(3):
            response = client.post(
                "/api/v1/analyze", json={"inquiry": "sync broken", "use_ai": False}, headers=GOOD
            )
            assert response.status_code == 200
        assert self.draft(client).status_code == 200

    def test_a_missing_anthropic_key_fails_before_spending_budget(
        self, client, monkeypatch, fake_ai
    ):
        configure(monkeypatch, ai_limit=1, anthropic="")
        assert self.draft(client).status_code == 400
        monkeypatch.setattr(srv, "ANTHROPIC_API_KEY", "key")
        assert self.draft(client).status_code == 200


class TestIngestPathSafety:
    @pytest.fixture
    def ingest_env(self, tmp_path, monkeypatch):
        kb = tmp_path / "kb"
        kb.mkdir()
        (kb / "doc.md").write_text("# Doc")
        secret_file = tmp_path / "outside.md"
        secret_file.write_text("do not read me")
        calls = []
        engine = SimpleNamespace(
            doc_count=lambda: 1,
            ingest_file=lambda p: calls.append(("file", str(p))) or 1,
            ingest_directory=lambda p: calls.append(("dir", str(p))) or 1,
        )
        monkeypatch.setattr(srv, "_engine", engine)
        monkeypatch.setattr(srv, "KNOWLEDGE_DIR", kb)
        return kb, secret_file, calls

    def post(self, client, path):
        return client.post("/api/v1/knowledge/ingest", json={"path": str(path)}, headers=GOOD)

    def test_files_inside_the_knowledge_directory_are_allowed(
        self, client, monkeypatch, ingest_env
    ):
        configure(monkeypatch)
        kb, _, calls = ingest_env
        assert self.post(client, kb / "doc.md").status_code == 200
        assert calls == [("file", str(kb / "doc.md"))]

    def test_the_knowledge_directory_itself_is_allowed(self, client, monkeypatch, ingest_env):
        configure(monkeypatch)
        kb, _, _ = ingest_env
        assert self.post(client, kb).status_code == 200

    def test_paths_outside_it_are_refused_and_nothing_is_read(
        self, client, monkeypatch, ingest_env
    ):
        configure(monkeypatch)
        _, outside, calls = ingest_env
        assert self.post(client, outside).status_code == 403
        assert calls == []

    def test_dot_dot_traversal_is_refused(self, client, monkeypatch, ingest_env):
        configure(monkeypatch)
        kb, _, calls = ingest_env
        assert self.post(client, kb / ".." / "outside.md").status_code == 403
        assert calls == []

    def test_a_symlink_pointing_outside_is_refused(self, client, monkeypatch, ingest_env):
        configure(monkeypatch)
        kb, outside, calls = ingest_env
        (kb / "link.md").symlink_to(outside)
        assert self.post(client, kb / "link.md").status_code == 403
        assert calls == []

    def test_a_missing_path_inside_the_directory_is_a_404(self, client, monkeypatch, ingest_env):
        configure(monkeypatch)
        kb, _, _ = ingest_env
        assert self.post(client, kb / "missing.md").status_code == 404
