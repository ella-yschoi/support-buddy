"""Tests for log parser."""

from __future__ import annotations

import pytest

from src.core.analyzer.log_parser import LogParser
from src.core.i18n import Language
from src.core.models import LogEvent


class TestLogParser:
    def test_parse_json_logs(self, sample_json_logs: str):
        parser = LogParser()
        events = parser.parse(sample_json_logs)

        assert len(events) == 6
        assert events[0].level == "INFO"
        assert events[0].message == "Sync started"

    def test_parse_text_logs(self, sample_text_logs: str):
        parser = LogParser()
        events = parser.parse(sample_text_logs)

        assert len(events) == 6
        assert events[0].level == "INFO"
        assert "Sync started" in events[0].message

    def test_extract_errors(self, sample_json_logs: str):
        parser = LogParser()
        events = parser.parse(sample_json_logs)
        errors = parser.extract_errors(events)

        assert len(errors) > 0
        assert all(e.level == "ERROR" for e in errors)

    def test_extract_slow_operations(self, sample_json_logs: str):
        parser = LogParser()
        events = parser.parse(sample_json_logs)
        slow_ops = parser.extract_slow_operations(events, threshold_ms=10000)

        assert len(slow_ops) > 0
        assert any("25" in str(op.metadata.get("duration_ms", "")) for op in slow_ops)

    def test_extract_error_codes(self, sample_json_logs: str):
        parser = LogParser()
        events = parser.parse(sample_json_logs)
        codes = parser.extract_error_codes(events)

        assert "SYNC-002" in codes

    def test_generate_summary(self, sample_json_logs: str):
        parser = LogParser()
        events = parser.parse(sample_json_logs)
        summary = parser.generate_text_summary(events)

        assert "error" in summary.lower() or "ERROR" in summary
        assert len(summary) > 0

    def test_parse_empty_input(self):
        parser = LogParser()
        events = parser.parse("")
        assert events == []

    def test_parse_invalid_json_falls_back_to_text(self):
        parser = LogParser()
        events = parser.parse("{invalid json")
        # Should try text parsing and return whatever it can
        assert isinstance(events, list)

    def test_detect_format_json(self, sample_json_logs: str):
        parser = LogParser()
        assert parser.detect_format(sample_json_logs) == "json"

    def test_detect_format_text(self, sample_text_logs: str):
        parser = LogParser()
        assert parser.detect_format(sample_text_logs) == "text"


class TestLogParserKorean:
    def test_generate_summary_korean_labels(self, sample_json_logs: str):
        parser = LogParser()
        events = parser.parse(sample_json_logs)
        summary = parser.generate_text_summary(events, lang=Language.KO)

        assert "로그 요약" in summary
        assert "시간 범위" in summary
        assert "레벨" in summary

    def test_generate_summary_korean_errors(self, sample_json_logs: str):
        parser = LogParser()
        events = parser.parse(sample_json_logs)
        summary = parser.generate_text_summary(events, lang=Language.KO)

        assert "오류 발견" in summary

    def test_generate_summary_korean_empty(self):
        parser = LogParser()
        summary = parser.generate_text_summary([], lang=Language.KO)
        assert "요약할 로그 이벤트가 없습니다" in summary

    def test_generate_summary_english_default(self, sample_json_logs: str):
        parser = LogParser()
        events = parser.parse(sample_json_logs)
        summary = parser.generate_text_summary(events)

        assert "Log Summary" in summary
