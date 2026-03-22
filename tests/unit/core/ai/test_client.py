"""Tests for AI client (mocked — does not call real API)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.ai.client import AIClient
from src.core.ai.tools import ALL_TOOLS
from src.core.knowledge.engine import KnowledgeEngine


@pytest.fixture
def knowledge_engine(tmp_path: Path, sample_knowledge_dir: Path) -> KnowledgeEngine:
    engine = KnowledgeEngine(persist_dir=str(tmp_path / "chroma"))
    engine.ingest_directory(sample_knowledge_dir)
    return engine


@pytest.fixture
def mock_anthropic():
    with patch("src.core.ai.client.anthropic") as mock:
        yield mock


class TestAIClient:
    def test_init_raises_without_api_key(self, knowledge_engine: KnowledgeEngine):
        with patch("src.core.ai.client.ANTHROPIC_API_KEY", ""):
            with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
                AIClient(knowledge_engine)

    def test_tools_are_well_formed(self):
        for tool in ALL_TOOLS:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert tool["input_schema"]["type"] == "object"

    def test_execute_tool_search_knowledge_base(
        self, knowledge_engine: KnowledgeEngine, mock_anthropic
    ):
        client = AIClient(knowledge_engine, api_key="test-key")
        result = client._execute_tool(
            "search_knowledge_base", {"query": "sync error"}
        )
        assert isinstance(result, list)
        assert len(result) > 0
        assert "title" in result[0]
        assert "content" in result[0]

    def test_execute_tool_get_error_code(
        self, knowledge_engine: KnowledgeEngine, mock_anthropic
    ):
        client = AIClient(knowledge_engine, api_key="test-key")
        result = client._execute_tool(
            "get_error_code_info", {"error_code": "SYNC-001"}
        )
        assert isinstance(result, list)
        assert len(result) > 0

    def test_execute_tool_unknown(
        self, knowledge_engine: KnowledgeEngine, mock_anthropic
    ):
        client = AIClient(knowledge_engine, api_key="test-key")
        result = client._execute_tool("nonexistent_tool", {})
        assert "error" in result

    def test_parse_json_response_plain(
        self, knowledge_engine: KnowledgeEngine, mock_anthropic
    ):
        client = AIClient(knowledge_engine, api_key="test-key")
        result = client._parse_json_response('{"category": "sync", "severity": "high"}')
        assert result["category"] == "sync"
        assert result["severity"] == "high"

    def test_parse_json_response_with_code_block(
        self, knowledge_engine: KnowledgeEngine, mock_anthropic
    ):
        client = AIClient(knowledge_engine, api_key="test-key")
        text = '```json\n{"category": "sync"}\n```'
        result = client._parse_json_response(text)
        assert result["category"] == "sync"

    def test_parse_json_response_embedded_in_text(
        self, knowledge_engine: KnowledgeEngine, mock_anthropic
    ):
        client = AIClient(knowledge_engine, api_key="test-key")
        text = 'Here is the analysis: {"category": "sync", "severity": "low"} end.'
        result = client._parse_json_response(text)
        assert result["category"] == "sync"

    def test_parse_json_response_invalid(
        self, knowledge_engine: KnowledgeEngine, mock_anthropic
    ):
        client = AIClient(knowledge_engine, api_key="test-key")
        result = client._parse_json_response("no json here")
        assert result["parse_error"] is True
