"""End-to-end integration tests for Support Buddy core pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.analyzer.inquiry import InquiryAnalyzer
from src.core.analyzer.log_parser import LogParser
from src.core.knowledge.engine import KnowledgeEngine
from src.core.models import InquiryCategory


@pytest.fixture
def engine_with_data(tmp_path: Path) -> KnowledgeEngine:
    """Engine loaded with the actual virtual company knowledge data."""
    kb_dir = Path(__file__).parent.parent.parent / "data" / "knowledge"
    engine = KnowledgeEngine(persist_dir=str(tmp_path / "chroma"))
    engine.ingest_directory(kb_dir)
    return engine


@pytest.fixture
def analyzer(engine_with_data: KnowledgeEngine) -> InquiryAnalyzer:
    return InquiryAnalyzer(engine_with_data)


class TestInquiryPipeline:
    """Test 10 sample inquiries against the full knowledge base."""

    SAMPLE_INQUIRIES = [
        ("My files stopped syncing this morning on my Mac", InquiryCategory.SYNC),
        ("Getting SYNC-002 error when uploading large files", InquiryCategory.SYNC),
        ("I can't access the shared folder my manager sent me", InquiryCategory.PERMISSION),
        ("The web dashboard is extremely slow to load", InquiryCategory.PERFORMANCE),
        ("Our webhook endpoint isn't receiving any events", InquiryCategory.API),
        ("How do I set up auto-backup for my project folder?", InquiryCategory.FEATURE),
        ("I need to add 5 new team members but the invite button doesn't work", InquiryCategory.ACCOUNT),
        ("Getting AUTH-002 permission denied when trying to delete files", InquiryCategory.PERMISSION),
        ("API rate limit exceeded, we're getting 429 errors", InquiryCategory.API),
        ("How do I enable delta sync for large files?", InquiryCategory.FEATURE),
    ]

    @pytest.mark.parametrize("inquiry,expected_category", SAMPLE_INQUIRIES)
    def test_classifies_correctly(
        self, analyzer: InquiryAnalyzer, inquiry: str, expected_category: InquiryCategory
    ):
        result = analyzer.classify(inquiry)
        assert result.category == expected_category, (
            f"Expected {expected_category.value} for: '{inquiry}', "
            f"got {result.category.value}"
        )

    @pytest.mark.parametrize("inquiry,expected_category", SAMPLE_INQUIRIES)
    def test_returns_relevant_articles(
        self, analyzer: InquiryAnalyzer, inquiry: str, expected_category: InquiryCategory
    ):
        result = analyzer.classify(inquiry)
        assert len(result.relevant_articles) > 0, f"No articles for: '{inquiry}'"

    @pytest.mark.parametrize("inquiry,expected_category", SAMPLE_INQUIRIES)
    def test_returns_checklist(
        self, analyzer: InquiryAnalyzer, inquiry: str, expected_category: InquiryCategory
    ):
        result = analyzer.classify(inquiry)
        assert len(result.checklist) >= 2, f"Too few checklist items for: '{inquiry}'"

    @pytest.mark.parametrize("inquiry,expected_category", SAMPLE_INQUIRIES)
    def test_confidence_above_threshold(
        self, analyzer: InquiryAnalyzer, inquiry: str, expected_category: InquiryCategory
    ):
        result = analyzer.classify(inquiry)
        assert result.confidence >= 0.5, (
            f"Low confidence {result.confidence:.0%} for: '{inquiry}'"
        )


class TestLogPipeline:
    def test_full_log_analysis_pipeline(self, engine_with_data: KnowledgeEngine):
        log_file = Path(__file__).parent.parent.parent / "data" / "sample_logs" / "sync_error.json"
        raw_logs = log_file.read_text()

        parser = LogParser()
        events = parser.parse(raw_logs)

        assert len(events) == 12

        errors = parser.extract_errors(events)
        assert len(errors) == 4

        slow_ops = parser.extract_slow_operations(events, threshold_ms=10000)
        assert len(slow_ops) >= 1

        error_codes = parser.extract_error_codes(events)
        assert "SYNC-002" in error_codes

        summary = parser.generate_text_summary(events)
        assert "SYNC-002" in summary
        assert "ERROR" in summary

    def test_log_error_codes_found_in_knowledge_base(
        self, engine_with_data: KnowledgeEngine
    ):
        log_file = Path(__file__).parent.parent.parent / "data" / "sample_logs" / "sync_error.json"
        raw_logs = log_file.read_text()

        parser = LogParser()
        events = parser.parse(raw_logs)
        error_codes = parser.extract_error_codes(events)

        for code in error_codes:
            results = engine_with_data.search(code, top_k=3, category="error_code")
            assert len(results) > 0, f"Error code {code} not found in knowledge base"
