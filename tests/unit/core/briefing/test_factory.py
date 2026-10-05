"""Tests for local briefing wiring and log insight."""

from __future__ import annotations

import pytest

from src.config import SAMPLE_LOGS_DIR
from src.core.briefing.factory import build_local_builder, local_log_insight
from src.core.briefing.models import Sufficiency
from src.core.knowledge.engine import KnowledgeEngine
from src.core.policy.models import AutonomyLevel
from src.core.trust.models import Customer


def test_local_log_insight_extracts_errors_and_codes():
    raw = (SAMPLE_LOGS_DIR / "sync_error.json").read_text()
    insight = local_log_insight(raw)
    assert insight.errors
    assert "SYNC" in insight.root_cause_hypothesis


def test_local_log_insight_handles_empty_and_unparseable_input():
    assert local_log_insight("").errors == []
    garbage = local_log_insight("\x00\x01 not a log at all")
    assert garbage.errors == []
    assert garbage.root_cause_hypothesis


@pytest.fixture(scope="module")
def builder(tmp_path_factory):
    from src.config import KNOWLEDGE_DIR

    tmp = tmp_path_factory.mktemp("kb")
    engine = KnowledgeEngine(persist_dir=str(tmp))
    engine.ingest_directory(KNOWLEDGE_DIR)
    return build_local_builder(engine)


def test_local_builder_produces_sufficient_briefing_for_sync_case_with_logs(builder):
    raw = (SAMPLE_LOGS_DIR / "sync_error.json").read_text()
    b = builder.build(
        "My files are not syncing and I see SYNC-002", Customer(plan="free"), log_text=raw
    )
    assert b.sufficiency is Sufficiency.SUFFICIENT
    assert b.hypotheses[0].log_evidence
    assert b.autonomy is AutonomyLevel.CONFIRM


def test_local_builder_breach_is_human_only(builder):
    b = builder.build("We think there was a data breach", Customer(plan="enterprise"))
    assert b.autonomy is AutonomyLevel.HUMAN_ONLY
    assert b.draft_body is None
