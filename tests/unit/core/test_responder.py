"""Tests for response drafter (mocked API)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.analyzer.inquiry import InquiryAnalyzer
from src.core.knowledge.engine import KnowledgeEngine
from src.core.models import InquiryResult
from src.core.responder.drafter import ResponseDrafter


@pytest.fixture
def knowledge_engine(tmp_path: Path, sample_knowledge_dir: Path) -> KnowledgeEngine:
    engine = KnowledgeEngine(persist_dir=str(tmp_path / "chroma"))
    engine.ingest_directory(sample_knowledge_dir)
    return engine


@pytest.fixture
def sample_analysis(knowledge_engine: KnowledgeEngine) -> InquiryResult:
    analyzer = InquiryAnalyzer(knowledge_engine)
    return analyzer.classify("My files are not syncing and I see SYNC-002 error")


class TestResponseDrafter:
    @patch("src.core.ai.client.anthropic")
    def test_draft_with_ai_success(
        self, mock_anthropic, knowledge_engine: KnowledgeEngine, sample_analysis: InquiryResult
    ):
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = (
            '{"body": "Thank you for reaching out. I understand your files are not syncing '
            'and you are seeing a SYNC-002 error, which indicates a storage quota issue. '
            'Please check your storage usage under Dashboard > Account > Storage.", '
            '"confidence": 0.85, '
            '"needs_escalation": false, '
            '"internal_note": "Customer likely exceeded quota. Check account storage."}'
        )
        mock_response.content = [mock_block]
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

        drafter = ResponseDrafter(knowledge_engine, api_key="test-key")
        response = drafter.draft("My files are not syncing, SYNC-002 error", sample_analysis)

        assert "SYNC-002" in response.body or "sync" in response.body.lower()
        assert response.confidence > 0.5
        assert response.needs_escalation is False
        assert len(response.citations) > 0

    @patch("src.core.ai.client.anthropic")
    def test_fallback_on_api_error(
        self, mock_anthropic, knowledge_engine: KnowledgeEngine, sample_analysis: InquiryResult
    ):
        mock_anthropic.Anthropic.return_value.messages.create.side_effect = Exception("fail")

        drafter = ResponseDrafter(knowledge_engine, api_key="test-key")
        response = drafter.draft("My files are not syncing", sample_analysis)

        # Fallback should produce a reasonable response
        assert "CloudSync Support" in response.body
        assert "Thank you" in response.body
        assert response.confidence > 0
        assert len(response.citations) > 0

    @patch("src.core.ai.client.anthropic")
    def test_fallback_includes_checklist(
        self, mock_anthropic, knowledge_engine: KnowledgeEngine, sample_analysis: InquiryResult
    ):
        mock_anthropic.Anthropic.return_value.messages.create.side_effect = Exception("fail")

        drafter = ResponseDrafter(knowledge_engine, api_key="test-key")
        response = drafter.draft("Sync issue", sample_analysis)

        # Fallback should include checklist items from analysis
        assert "sync agent" in response.body.lower() or "network" in response.body.lower()

    @patch("src.core.ai.client.anthropic")
    def test_escalation_flag_on_parse_error(
        self, mock_anthropic, knowledge_engine: KnowledgeEngine, sample_analysis: InquiryResult
    ):
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "This is not valid JSON at all"
        mock_response.content = [mock_block]
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

        drafter = ResponseDrafter(knowledge_engine, api_key="test-key")
        response = drafter.draft("help", sample_analysis)

        assert response.needs_escalation is True
        assert response.confidence <= 0.5
