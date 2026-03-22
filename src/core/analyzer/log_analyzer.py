"""AI-powered log analyzer using Claude for natural language insights."""

from __future__ import annotations

from typing import Any

from src.core.ai.client import AIClient
from src.core.analyzer.log_parser import LogParser
from src.core.knowledge.engine import KnowledgeEngine
from src.core.models import LogEvent, LogInsight


class AILogAnalyzer:
    """Analyze parsed logs with Claude AI for root cause and insights."""

    def __init__(self, knowledge_engine: KnowledgeEngine, api_key: str | None = None):
        self._knowledge = knowledge_engine
        self._ai_client = AIClient(knowledge_engine, api_key=api_key)
        self._parser = LogParser()

    def analyze(self, raw_logs: str) -> LogInsight:
        """Parse logs, then use AI to generate insights."""
        events = self._parser.parse(raw_logs)
        if not events:
            return LogInsight(
                summary="No log events found to analyze.",
                errors=[],
                slow_operations=[],
                anomalies=[],
                timeline=[],
                root_cause_hypothesis="No data available for analysis.",
            )

        errors = self._parser.extract_errors(events)
        slow_ops = self._parser.extract_slow_operations(events)
        error_codes = self._parser.extract_error_codes(events)

        # Build a text summary for Claude
        text_summary = self._parser.generate_text_summary(events)

        # Get AI insights
        try:
            ai_result = self._ai_client.analyze_logs(text_summary)
            return self._build_insight(ai_result, events, errors, slow_ops)
        except Exception:
            # Fallback to parser-only insights
            return self._fallback_insight(events, errors, slow_ops, error_codes)

    def analyze_from_events(self, events: list[LogEvent]) -> LogInsight:
        """Analyze pre-parsed log events with AI."""
        if not events:
            return LogInsight(
                summary="No log events to analyze.",
                errors=[],
                slow_operations=[],
                anomalies=[],
                timeline=[],
                root_cause_hypothesis="No data available.",
            )

        errors = self._parser.extract_errors(events)
        slow_ops = self._parser.extract_slow_operations(events)
        error_codes = self._parser.extract_error_codes(events)
        text_summary = self._parser.generate_text_summary(events)

        try:
            ai_result = self._ai_client.analyze_logs(text_summary)
            return self._build_insight(ai_result, events, errors, slow_ops)
        except Exception:
            return self._fallback_insight(events, errors, slow_ops, error_codes)

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
    ) -> LogInsight:
        """Generate insight without AI (parser-only fallback)."""
        summary = self._parser.generate_text_summary(events)

        anomalies = []
        if errors:
            anomalies.append(f"{len(errors)} error(s) detected")
        if slow_ops:
            anomalies.append(f"{len(slow_ops)} slow operation(s) detected")

        hypothesis = "Unable to determine root cause without AI analysis."
        if error_codes:
            hypothesis = (
                f"Errors related to code(s): {', '.join(error_codes)}. "
                "Check the knowledge base for resolution steps."
            )

        return LogInsight(
            summary=summary,
            errors=errors,
            slow_operations=slow_ops,
            anomalies=anomalies,
            timeline=events,
            root_cause_hypothesis=hypothesis,
        )
