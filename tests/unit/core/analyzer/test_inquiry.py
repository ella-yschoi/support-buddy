"""Tests for inquiry analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.analyzer.inquiry import InquiryAnalyzer
from src.core.i18n import Language
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


class TestInquiryAnalyzerKorean:
    def test_classify_sync_korean(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("파일이 동기화가 안 됩니다")
        assert result.category == InquiryCategory.SYNC

    def test_classify_permission_korean(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("공유 폴더에 접근이 안 됩니다")
        assert result.category == InquiryCategory.PERMISSION

    def test_classify_performance_korean(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("대시보드가 매우 느립니다")
        assert result.category == InquiryCategory.PERFORMANCE

    def test_classify_api_korean(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("웹훅이 작동하지 않습니다")
        assert result.category == InquiryCategory.API

    def test_classify_account_korean(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("팀원을 추가하려는데 계정 업그레이드가 필요합니다")
        assert result.category == InquiryCategory.ACCOUNT

    def test_classify_feature_korean(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("이 기능은 어떻게 설정하나요?")
        assert result.category == InquiryCategory.FEATURE

    def test_korean_returns_korean_checklist(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("파일이 동기화가 안 됩니다")
        assert any("확인" in item for item in result.checklist)

    def test_korean_returns_korean_follow_ups(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("파일이 동기화가 안 됩니다")
        assert any("나요" in q or "인가요" in q for q in result.follow_up_questions)

    def test_korean_returns_korean_summary(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("파일이 동기화가 안 됩니다")
        assert "동기화" in result.summary

    def test_korean_severity_critical(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("데이터 손실이 발생했습니다")
        assert result.severity == Severity.CRITICAL

    def test_korean_severity_high(self, analyzer: InquiryAnalyzer):
        result = analyzer.classify("긴급합니다 로그인 불가 상태입니다")
        assert result.severity == Severity.HIGH

    def test_explicit_lang_override(self, analyzer: InquiryAnalyzer):
        """Even with English text, explicit lang=KO returns Korean checklist."""
        result = analyzer.classify("Files not syncing", lang=Language.KO)
        assert any("확인" in item for item in result.checklist)
