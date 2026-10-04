"""Tests for eval pipelines."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.ai.registry import ModelRegistry
from src.core.knowledge.engine import KnowledgeEngine
from src.core.models import InquiryCategory
from src.eval.pipeline import ClaudePipeline, LocalPipeline
from src.eval.pricing import estimate_cost
from tests.unit.eval.conftest import golden_case


@pytest.fixture
def knowledge_engine(tmp_path: Path, sample_knowledge_dir: Path) -> KnowledgeEngine:
    engine = KnowledgeEngine(persist_dir=str(tmp_path / "chroma"))
    engine.ingest_directory(sample_knowledge_dir)
    return engine


def test_local_pipeline_classifies_and_drafts_without_ai(knowledge_engine):
    case = golden_case(inquiry="My files are not syncing and I see SYNC-002")
    out = LocalPipeline(knowledge_engine).run(case)
    assert out.analysis.category is InquiryCategory.SYNC
    assert out.draft is not None
    assert out.usage.input_tokens == 0
    assert out.usage.cost_usd == 0.0


def _text_response(text: str, input_tokens: int, output_tokens: int) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [block]
    response.usage.input_tokens = input_tokens
    response.usage.output_tokens = output_tokens
    return response


@patch("src.core.ai.client.anthropic")
def test_claude_pipeline_uses_registry_models_and_reports_usage(mock_anthropic, knowledge_engine):
    create = mock_anthropic.Anthropic.return_value.messages.create
    create.side_effect = [
        _text_response('{"category": "sync", "severity": "high", "summary": "s"}', 1000, 100),
        _text_response(
            '{"body": "hello", "confidence": 0.9, "needs_escalation": false}', 2000, 300
        ),
    ]
    registry = ModelRegistry("t", "claude-haiku-4-5-20251001", "claude-sonnet-5-5", "c", "a")
    pipeline = ClaudePipeline(knowledge_engine, registry, api_key="k")

    out = pipeline.run(golden_case(inquiry="files not syncing"))

    models_used = [c.kwargs["model"] for c in create.call_args_list]
    assert models_used == ["claude-haiku-4-5-20251001", "claude-sonnet-5-5"]
    assert out.usage.input_tokens == 3000
    assert out.usage.output_tokens == 400
    expected = estimate_cost("claude-haiku-4-5-20251001", 1000, 100) + estimate_cost(
        "claude-sonnet-5-5", 2000, 300
    )
    assert out.usage.cost_usd == pytest.approx(expected)
    assert out.analysis.severity.value == "high"
    assert out.draft is not None and out.draft.body == "hello"
