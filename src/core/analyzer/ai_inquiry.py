"""AI-powered inquiry analyzer using Claude with tool use."""

from __future__ import annotations

from typing import Any

from src.core.ai.client import AIClient
from src.core.analyzer.inquiry import InquiryAnalyzer
from src.core.i18n import Language, detect_language
from src.core.knowledge.engine import KnowledgeEngine
from src.core.models import InquiryCategory, InquiryResult, Severity


class AIInquiryAnalyzer:
    """Analyze customer inquiries using Claude AI with knowledge base tool use.

    Falls back to the keyword-based InquiryAnalyzer if the AI call fails.
    """

    def __init__(self, knowledge_engine: KnowledgeEngine, api_key: str | None = None):
        self._knowledge = knowledge_engine
        self._ai_client = AIClient(knowledge_engine, api_key=api_key)
        self._fallback = InquiryAnalyzer(knowledge_engine)

    def analyze(
        self, inquiry_text: str, lang: Language | None = None
    ) -> InquiryResult:
        """Analyze inquiry with Claude AI, falling back to keyword-based on failure."""
        if lang is None:
            lang = detect_language(inquiry_text)
        try:
            raw = self._ai_client.analyze_inquiry(inquiry_text, lang=lang)
            if raw.get("parse_error"):
                return self._fallback.classify(inquiry_text, lang=lang)
            return self._build_result(raw, inquiry_text)
        except Exception:
            return self._fallback.classify(inquiry_text, lang=lang)

    def _build_result(self, raw: dict[str, Any], inquiry_text: str) -> InquiryResult:
        """Convert Claude's JSON response into an InquiryResult."""
        category = self._parse_category(raw.get("category", "unknown"))
        severity = self._parse_severity(raw.get("severity", "medium"))

        checklist = raw.get("checklist", [])
        if not isinstance(checklist, list):
            checklist = [str(checklist)]

        follow_ups = raw.get("follow_up_questions", [])
        if not isinstance(follow_ups, list):
            follow_ups = [str(follow_ups)]

        confidence = raw.get("confidence", 0.5)
        if not isinstance(confidence, (int, float)):
            confidence = 0.5
        confidence = max(0.0, min(1.0, float(confidence)))

        summary = raw.get("summary", f"{category.value} issue: {inquiry_text[:100]}")

        # Also do a KB search so we have articles to show
        relevant_articles = self._knowledge.search(inquiry_text, top_k=5)

        return InquiryResult(
            category=category,
            severity=severity,
            summary=str(summary),
            checklist=[str(c) for c in checklist],
            follow_up_questions=[str(q) for q in follow_ups],
            relevant_articles=relevant_articles,
            confidence=confidence,
        )

    def _parse_category(self, value: str) -> InquiryCategory:
        try:
            return InquiryCategory(value.lower().strip())
        except ValueError:
            return InquiryCategory.UNKNOWN

    def _parse_severity(self, value: str) -> Severity:
        try:
            return Severity(value.lower().strip())
        except ValueError:
            return Severity.MEDIUM
