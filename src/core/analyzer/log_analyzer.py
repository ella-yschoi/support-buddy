"""AI-powered log analyzer using Claude for natural language insights."""

from __future__ import annotations

from typing import Any

from src.core.ai.client import AIClient
from src.core.analyzer.log_parser import LogParser
from src.core.i18n import Language
from src.core.knowledge.engine import KnowledgeEngine
from src.core.models import LogEvent, LogInsight


class AILogAnalyzer:
    """Analyze parsed logs with Claude AI for root cause and insights."""

    def __init__(self, knowledge_engine: KnowledgeEngine, api_key: str | None = None):
        self._knowledge = knowledge_engine
        self._ai_client = AIClient(knowledge_engine, api_key=api_key)
        self._parser = LogParser()

    def analyze(self, raw_logs: str, lang: Language = Language.EN) -> LogInsight:
        """Parse logs, then use AI to generate insights."""
        events = self._parser.parse(raw_logs)
        if not events:
            return LogInsight(
                summary=_FALLBACK[lang]["no_events"],
                errors=[],
                slow_operations=[],
                anomalies=[],
                timeline=[],
                root_cause_hypothesis=_FALLBACK[lang]["no_data"],
            )

        errors = self._parser.extract_errors(events)
        slow_ops = self._parser.extract_slow_operations(events)
        error_codes = self._parser.extract_error_codes(events)

        # Build a text summary for Claude
        text_summary = self._parser.generate_text_summary(events, lang=lang)

        # Get AI insights
        try:
            ai_result = self._ai_client.analyze_logs(text_summary)
            return self._build_insight(ai_result, events, errors, slow_ops)
        except Exception:
            # Fallback to parser-only insights
            return self._fallback_insight(events, errors, slow_ops, error_codes, lang=lang)

    def analyze_from_events(
        self, events: list[LogEvent], lang: Language = Language.EN
    ) -> LogInsight:
        """Analyze pre-parsed log events with AI."""
        if not events:
            return LogInsight(
                summary=_FALLBACK[lang]["no_events"],
                errors=[],
                slow_operations=[],
                anomalies=[],
                timeline=[],
                root_cause_hypothesis=_FALLBACK[lang]["no_data"],
            )

        errors = self._parser.extract_errors(events)
        slow_ops = self._parser.extract_slow_operations(events)
        error_codes = self._parser.extract_error_codes(events)
        text_summary = self._parser.generate_text_summary(events, lang=lang)

        try:
            ai_result = self._ai_client.analyze_logs(text_summary)
            return self._build_insight(ai_result, events, errors, slow_ops)
        except Exception:
            return self._fallback_insight(events, errors, slow_ops, error_codes, lang=lang)

    def _build_insight(
        self,
        ai_result: dict[str, Any],
        events: list[LogEvent],
        errors: list[LogEvent],
        slow_ops: list[LogEvent],
    ) -> LogInsight:
        """Build LogInsight from AI response + parsed data."""
        if ai_result.get("parse_error"):
            raw = ai_result.get("raw_response", "")
            return LogInsight(
                summary=raw[:500] if raw else "AI analysis returned unstructured text.",
                errors=errors,
                slow_operations=slow_ops,
                anomalies=[],
                timeline=events,
                root_cause_hypothesis="See summary for details.",
            )

        anomalies = ai_result.get("anomalies", [])
        if not isinstance(anomalies, list):
            anomalies = [str(anomalies)]

        return LogInsight(
            summary=str(ai_result.get("summary", "No summary generated.")),
            errors=errors,
            slow_operations=slow_ops,
            anomalies=[str(a) for a in anomalies],
            timeline=events,
            root_cause_hypothesis=str(
                ai_result.get("root_cause_hypothesis", "Unable to determine.")
            ),
        )

    def _fallback_insight(
        self,
        events: list[LogEvent],
        errors: list[LogEvent],
        slow_ops: list[LogEvent],
        error_codes: list[str],
        lang: Language = Language.EN,
    ) -> LogInsight:
        """Generate insight without AI (parser-only fallback)."""
        fb = _FALLBACK[lang]
        summary = self._parser.generate_text_summary(events, lang=lang)

        anomalies = []
        if errors:
            anomalies.append(fb["errors_detected"].format(count=len(errors)))
        if slow_ops:
            anomalies.append(fb["slow_ops_detected"].format(count=len(slow_ops)))

        hypothesis = fb["no_root_cause"]
        if error_codes:
            hypothesis = fb["error_code_hypothesis"].format(
                codes=", ".join(error_codes)
            )

        return LogInsight(
            summary=summary,
            errors=errors,
            slow_operations=slow_ops,
            anomalies=anomalies,
            timeline=events,
            root_cause_hypothesis=hypothesis,
        )


_FALLBACK: dict[Language, dict[str, str]] = {
    Language.EN: {
        "no_events": "No log events found to analyze.",
        "no_data": "No data available for analysis.",
        "no_root_cause": "Unable to determine root cause without AI analysis.",
        "errors_detected": "{count} error(s) detected",
        "slow_ops_detected": "{count} slow operation(s) detected",
        "error_code_hypothesis": (
            "Errors related to code(s): {codes}. "
            "Check the knowledge base for resolution steps."
        ),
    },
    Language.KO: {
        "no_events": "분석할 로그 이벤트를 찾을 수 없습니다.",
        "no_data": "분석에 사용할 데이터가 없습니다.",
        "no_root_cause": "AI 분석 없이는 근본 원인을 판단할 수 없습니다.",
        "errors_detected": "{count}개의 오류가 감지되었습니다",
        "slow_ops_detected": "{count}개의 느린 작업이 감지되었습니다",
        "error_code_hypothesis": (
            "오류 코드 {codes} 관련 문제입니다. "
            "지식 베이스에서 해결 방법을 확인하세요."
        ),
    },
}
