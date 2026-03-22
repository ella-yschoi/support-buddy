"""Tests for AI-powered inquiry analyzer (mocked API)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.analyzer.ai_inquiry import AIInquiryAnalyzer
from src.core.knowledge.engine import KnowledgeEngine
from src.core.models import InquiryCategory, Severity


@pytest.fixture
def knowledge_engine(tmp_path: Path, sample_knowledge_dir: Path) -> KnowledgeEngine:
    engine = KnowledgeEngine(persist_dir=str(tmp_path / "chroma"))
    engine.ingest_directory(sample_knowledge_dir)
    return engine


class TestAIInquiryAnalyzer:
    @patch("src.core.ai.client.anthropic")
    def test_falls_back_on_api_error(
        self, mock_anthropic, knowledge_engine: KnowledgeEngine
    ):
        """When AI fails, should fall back to keyword-based analyzer."""
        mock_anthropic.Anthropic.return_value.messages.create.side_effect = Exception("API error")

        analyzer = AIInquiryAnalyzer(knowledge_engine, api_key="test-key")
        result = analyzer.analyze("My files are not syncing")

        # Should still return a result via fallback
        assert result.category == InquiryCategory.SYNC
        assert len(result.checklist) > 0

    @patch("src.core.ai.client.anthropic")
    def test_builds_result_from_valid_ai_response(
        self, mock_anthropic, knowledge_engine: KnowledgeEngine
    ):
        """When AI returns valid JSON, should build InquiryResult from it."""
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = (
            '{"category": "sync", "severity": "high", '
            '"summary": "File sync failure", '
            '"checklist": ["Check sync agent", "Verify network"], '
            '"follow_up_questions": ["Which devices?", "When did it start?"], '
            '"confidence": 0.85}'
        )
        mock_response.content = [mock_block]
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

        analyzer = AIInquiryAnalyzer(knowledge_engine, api_key="test-key")
        result = analyzer.analyze("My files stopped syncing")

        assert result.category == InquiryCategory.SYNC
        assert result.severity == Severity.HIGH
        assert result.confidence == 0.85
        assert "Check sync agent" in result.checklist
        assert "Which devices?" in result.follow_up_questions

    @patch("src.core.ai.client.anthropic")
    def test_handles_parse_error_response(
        self, mock_anthropic, knowledge_engine: KnowledgeEngine
    ):
        """When AI returns unparseable text, should fall back."""
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "I cannot analyze this properly."
        mock_response.content = [mock_block]
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

        analyzer = AIInquiryAnalyzer(knowledge_engine, api_key="test-key")
        result = analyzer.analyze("sync issue")

        # Should fall back to keyword-based
        assert result.category == InquiryCategory.SYNC
        assert len(result.checklist) > 0

    @patch("src.core.ai.client.anthropic")
    def test_parse_category_unknown(
        self, mock_anthropic, knowledge_engine: KnowledgeEngine
    ):
        """Invalid category from AI should map to UNKNOWN."""
        analyzer = AIInquiryAnalyzer(knowledge_engine, api_key="test-key")
        assert analyzer._parse_category("invalid") == InquiryCategory.UNKNOWN

    @patch("src.core.ai.client.anthropic")
    def test_confidence_clamped(
        self, mock_anthropic, knowledge_engine: KnowledgeEngine
    ):
        """Confidence should be clamped to [0, 1]."""
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = (
            '{"category": "sync", "severity": "low", '
            '"summary": "test", "checklist": [], '
            '"follow_up_questions": [], "confidence": 1.5}'
        )
        mock_response.content = [mock_block]
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

        analyzer = AIInquiryAnalyzer(knowledge_engine, api_key="test-key")
        result = analyzer.analyze("test")
        assert result.confidence <= 1.0
