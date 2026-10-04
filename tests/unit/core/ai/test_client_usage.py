"""Token usage tracking and per-role model selection (mocked API)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.ai.client import AIClient
from src.core.analyzer.ai_inquiry import AIInquiryAnalyzer
from src.core.analyzer.inquiry import InquiryAnalyzer
from src.core.knowledge.engine import KnowledgeEngine
from src.core.responder.drafter import ResponseDrafter, fallback_draft


@pytest.fixture
def knowledge_engine(tmp_path: Path, sample_knowledge_dir: Path) -> KnowledgeEngine:
    engine = KnowledgeEngine(persist_dir=str(tmp_path / "chroma"))
    engine.ingest_directory(sample_knowledge_dir)
    return engine


def _response(text: str, input_tokens: int = 100, output_tokens: int = 20) -> MagicMock:
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
def test_token_usage_accumulates_across_calls(mock_anthropic, knowledge_engine):
    create = mock_anthropic.Anthropic.return_value.messages.create
    create.side_effect = [_response('{"a": 1}', 100, 20), _response('{"a": 2}', 50, 5)]
    client = AIClient(knowledge_engine, api_key="k")
    client.analyze_inquiry("one")
    client.analyze_inquiry("two")
    assert client.token_usage == (150, 25)


@patch("src.core.ai.client.anthropic")
def test_token_usage_starts_at_zero_and_ignores_unreadable_usage(mock_anthropic, knowledge_engine):
    response = _response('{"a": 1}')
    response.usage = "not usage"
    mock_anthropic.Anthropic.return_value.messages.create.return_value = response
    client = AIClient(knowledge_engine, api_key="k")
    assert client.token_usage == (0, 0)
    client.analyze_inquiry("x")
    assert client.token_usage == (0, 0)


@patch("src.core.ai.client.anthropic")
def test_drafter_uses_requested_model(mock_anthropic, knowledge_engine):
    create = mock_anthropic.Anthropic.return_value.messages.create
    create.return_value = _response('{"body": "hi", "confidence": 0.9, "needs_escalation": false}')
    analysis = InquiryAnalyzer(knowledge_engine).classify("files not syncing")
    drafter = ResponseDrafter(knowledge_engine, api_key="k", model="my-draft-model")
    drafter.draft("files not syncing", analysis)
    assert create.call_args.kwargs["model"] == "my-draft-model"
    assert drafter.token_usage == (100, 20)


@patch("src.core.ai.client.anthropic")
def test_ai_analyzer_uses_requested_model(mock_anthropic, knowledge_engine):
    create = mock_anthropic.Anthropic.return_value.messages.create
    create.return_value = _response('{"category": "sync", "severity": "low", "summary": "s"}')
    analyzer = AIInquiryAnalyzer(knowledge_engine, api_key="k", model="my-classify-model")
    analyzer.analyze("files not syncing")
    assert create.call_args.kwargs["model"] == "my-classify-model"
    assert analyzer.token_usage == (100, 20)


def test_fallback_draft_needs_no_ai(knowledge_engine):
    analysis = InquiryAnalyzer(knowledge_engine).classify("files not syncing")
    draft = fallback_draft(analysis)
    assert "CloudSync Support" in draft.body
    assert draft.citations == analysis.relevant_articles[:3]
