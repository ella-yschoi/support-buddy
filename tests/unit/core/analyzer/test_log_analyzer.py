"""Tests for AI-powered log analyzer (mocked API)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.analyzer.log_analyzer import AILogAnalyzer
from src.core.knowledge.engine import KnowledgeEngine


@pytest.fixture
def knowledge_engine(tmp_path: Path, sample_knowledge_dir: Path) -> KnowledgeEngine:
    engine = KnowledgeEngine(persist_dir=str(tmp_path / "chroma"))
    engine.ingest_directory(sample_knowledge_dir)
    return engine


class TestAILogAnalyzer:
    @patch("src.core.ai.client.anthropic")
    def test_analyze_with_ai_success(
        self, mock_anthropic, knowledge_engine: KnowledgeEngine, sample_json_logs: str
    ):
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = (
            '{"summary": "Sync session with upload failures due to storage quota", '
            '"root_cause_hypothesis": "Storage quota exceeded for user-123", '
            '"anomalies": ["3 repeated SYNC-002 errors", "25s slow upload"], '
            '"next_steps": ["Check storage quota", "Review file sizes"]}'
        )
        mock_response.content = [mock_block]
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

        analyzer = AILogAnalyzer(knowledge_engine, api_key="test-key")
        insight = analyzer.analyze(sample_json_logs)

        assert "quota" in insight.summary.lower()
        assert "SYNC-002" in insight.root_cause_hypothesis or "quota" in insight.root_cause_hypothesis.lower()
        assert len(insight.anomalies) > 0
        assert len(insight.errors) > 0

    @patch("src.core.ai.client.anthropic")
    def test_falls_back_on_api_error(
        self, mock_anthropic, knowledge_engine: KnowledgeEngine, sample_json_logs: str
    ):
        mock_anthropic.Anthropic.return_value.messages.create.side_effect = Exception("fail")

        analyzer = AILogAnalyzer(knowledge_engine, api_key="test-key")
        insight = analyzer.analyze(sample_json_logs)

        # Fallback should still extract errors
        assert len(insight.errors) > 0
        assert "SYNC-002" in insight.root_cause_hypothesis

    def test_analyze_empty_logs(self, knowledge_engine: KnowledgeEngine):
        with patch("src.core.ai.client.anthropic"):
            analyzer = AILogAnalyzer(knowledge_engine, api_key="test-key")
            insight = analyzer.analyze("")

            assert "No log events" in insight.summary
            assert insight.errors == []

    @patch("src.core.ai.client.anthropic")
    def test_analyze_from_events(
        self, mock_anthropic, knowledge_engine: KnowledgeEngine, sample_json_logs: str
    ):
        from src.core.analyzer.log_parser import LogParser
        parser = LogParser()
        events = parser.parse(sample_json_logs)

        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = (
            '{"summary": "Upload errors", "root_cause_hypothesis": "Quota issue", '
            '"anomalies": ["errors"], "next_steps": ["check quota"]}'
        )
        mock_response.content = [mock_block]
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_response

        analyzer = AILogAnalyzer(knowledge_engine, api_key="test-key")
        insight = analyzer.analyze_from_events(events)

        assert len(insight.timeline) == len(events)
        assert len(insight.errors) > 0
