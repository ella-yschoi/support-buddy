"""Tests for inquiry analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.analyzer.inquiry import InquiryAnalyzer
from src.core.knowledge.engine import KnowledgeEngine
from src.core.models import InquiryCategory, Severity


@pytest.fixture
def knowledge_engine(tmp_path: Path, sample_knowledge_dir: Path) -> KnowledgeEngine:
    engine = KnowledgeEngine(persist_dir=str(tmp_path / "chroma"))
    engine.ingest_directory(sample_knowledge_dir)
    return engine


@pytest.fixture
def analyzer(knowledge_engine: KnowledgeEngine) -> InquiryAnalyzer:
    return InquiryAnalyzer(knowledge_engine)


class TestInquiryAnalyzer:
    def test_classify_sync_inquiry(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("My files are not syncing between my laptop and desktop")
        assert result.category == InquiryCategory.SYNC

    def test_classify_permission_inquiry(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("I can't access the shared folder my colleague sent me")
        assert result.category == InquiryCategory.PERMISSION

    def test_classify_performance_inquiry(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("The dashboard is loading very slowly today")
        assert result.category == InquiryCategory.PERFORMANCE

    def test_classify_api_inquiry(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("Our webhook is not firing when files are uploaded")
        assert result.category == InquiryCategory.API

    def test_classify_account_inquiry(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("I need to add more team members but the button is greyed out")
        assert result.category == InquiryCategory.ACCOUNT

    def test_classify_returns_severity(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("My files are not syncing")
        assert result.severity in [s for s in Severity]

    def test_generate_checklist_nonempty(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("My files are not syncing")
        assert len(result.checklist) > 0

    def test_generate_follow_up_questions(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("Something is wrong with my sync")
        assert len(result.follow_up_questions) > 0

    def test_relevant_articles_returned(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("I'm getting error SYNC-002 when uploading files")
        assert len(result.relevant_articles) > 0

    def test_confidence_score_in_range(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("Files not syncing")
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_unknown_inquiry(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("asdfghjkl random noise")
        assert result.confidence < 0.8
