"""Inquiry analyzer — classify, generate checklist, and suggest follow-ups."""

from __future__ import annotations

import re
from typing import Optional

from src.core.knowledge.engine import KnowledgeEngine
from src.core.models import InquiryCategory, InquiryResult, SearchResult, Severity

# Keyword-based classification rules (used for local classification without AI)
_CATEGORY_KEYWORDS: dict[InquiryCategory, list[str]] = {
    InquiryCategory.SYNC: [
        "sync", "syncing", "not syncing", "file conflict", "upload failed",
        "download failed", "sync-0", "not appearing", "missing file",
    ],
    InquiryCategory.PERMISSION: [
        "permission", "access denied", "can't access", "cannot access",
        "shared folder", "auth-0", "not authorized", "forbidden", "role",
    ],
    InquiryCategory.PERFORMANCE: [
        "slow", "loading", "performance", "timeout", "perf-0", "lag",
        "takes long", "hanging", "unresponsive", "speed",
    ],
    InquiryCategory.API: [
        "api", "webhook", "endpoint", "rate limit", "api-0", "integration",
        "rest", "callback", "payload",
    ],
    InquiryCategory.ACCOUNT: [
        "account", "billing", "team member", "invite", "subscription",
        "plan", "upgrade", "acct-0", "greyed out", "grayed out",
    ],
    InquiryCategory.FEATURE: [
        "how do i", "how to", "set up", "configure", "enable", "feature",
        "what is", "can i",
    ],
}

_SEVERITY_INDICATORS: dict[Severity, list[str]] = {
    Severity.CRITICAL: [
        "data loss", "all files gone", "deleted everything", "production down",
        "entire organization", "sso failure for all",
    ],
    Severity.HIGH: [
        "can't login", "cannot access", "broken", "not working at all",
        "urgent", "critical", "blocking", "all users",
    ],
    Severity.MEDIUM: [
        "error", "failed", "not working", "issue", "problem",
    ],
    Severity.LOW: [
        "how to", "question", "wondering", "feature request", "slow",
    ],
}

# Checklist templates by category
_CHECKLISTS: dict[InquiryCategory, list[str]] = {
    InquiryCategory.SYNC: [
        "Check if the sync agent is running (tray icon status)",
        "Verify network connectivity",
        "Check for error codes in Settings > Logs",
        "Verify file size is under 5GB limit",
        "Check if the file path contains special characters",
        "Ask which devices are affected",
        "Check storage quota",
    ],
    InquiryCategory.PERMISSION: [
        "Verify the user's current workspace role",
        "Check if the folder/file share is still active",
        "Check if the user's account is suspended",
        "For SSO users, verify group membership in IdP",
        "Ask the user when they last had access",
    ],
    InquiryCategory.PERFORMANCE: [
        "Identify what is slow (sync, dashboard, API, desktop client)",
        "Check system status page for known issues",
        "Ask for specific metrics (normal vs. current speed)",
        "Check client version and OS",
        "Ask for a network speed test result",
    ],
    InquiryCategory.API: [
        "Verify the API endpoint being called",
        "Check if the API key is valid and not expired",
        "Check rate limit status",
        "Ask for the full request/response (redact auth headers)",
        "Ask if any recent changes were made (deployment, key rotation)",
    ],
    InquiryCategory.ACCOUNT: [
        "Check the customer's current plan and limits",
        "Verify the user's role (admin required for some actions)",
        "Check for any active restrictions on the account",
        "Ask which specific action is failing",
    ],
    InquiryCategory.FEATURE: [
        "Identify the specific feature being asked about",
        "Check which plan the customer is on (feature may require upgrade)",
        "Search knowledge base for feature documentation",
    ],
    InquiryCategory.UNKNOWN: [
        "Ask for more details about the issue",
        "Ask for screenshots if applicable",
        "Ask for the client version and OS",
    ],
}

_FOLLOW_UPS: dict[InquiryCategory, list[str]] = {
    InquiryCategory.SYNC: [
        "Which devices are experiencing the sync issue?",
        "When did you first notice the problem?",
        "Are all files affected or specific ones?",
        "Do you see any error messages or codes?",
    ],
    InquiryCategory.PERMISSION: [
        "What action were you trying to perform when you got the error?",
        "Were you able to access this resource before?",
        "Has your role or team membership changed recently?",
    ],
    InquiryCategory.PERFORMANCE: [
        "When did the slowness start?",
        "Is it affecting all operations or specific ones?",
        "How many files/folders are in your sync set?",
        "What is your network bandwidth?",
    ],
    InquiryCategory.API: [
        "What HTTP status code are you receiving?",
        "Can you share the API endpoint and method?",
        "Is the issue intermittent or consistent?",
        "Did anything change recently in your integration?",
    ],
    InquiryCategory.ACCOUNT: [
        "What specific action are you trying to perform?",
        "What is your current plan?",
        "Are you a workspace admin?",
    ],
    InquiryCategory.FEATURE: [
        "What plan are you currently on?",
        "What are you trying to achieve?",
    ],
    InquiryCategory.UNKNOWN: [
        "Could you describe the issue in more detail?",
        "What were you trying to do when the issue occurred?",
        "Can you share any screenshots or error messages?",
    ],
}


class InquiryAnalyzer:
    """Analyze customer inquiries using keyword classification and knowledge base search."""

    def __init__(self, knowledge_engine: KnowledgeEngine):
        self._knowledge = knowledge_engine

    def classify(self, inquiry_text: str) -> InquiryResult:
        """Classify an inquiry and generate guidance for the TSE."""
        text_lower = inquiry_text.lower()

        category = self._detect_category(text_lower)
        severity = self._detect_severity(text_lower)
        checklist = _CHECKLISTS.get(category, _CHECKLISTS[InquiryCategory.UNKNOWN])
        follow_ups = _FOLLOW_UPS.get(category, _FOLLOW_UPS[InquiryCategory.UNKNOWN])

        # Search knowledge base for relevant articles
        relevant_articles = self._knowledge.search(inquiry_text, top_k=5)

        # Extract error codes and search specifically
        error_codes = self._extract_error_codes(inquiry_text)
        for code in error_codes:
            code_results = self._knowledge.search(code, top_k=2, category="error_code")
            relevant_articles.extend(code_results)

        # Deduplicate articles by doc_id
        seen_ids: set[str] = set()
        unique_articles: list[SearchResult] = []
        for article in relevant_articles:
            if article.doc_id not in seen_ids:
                seen_ids.add(article.doc_id)
                unique_articles.append(article)

        confidence = self._calculate_confidence(category, unique_articles, text_lower)

        return InquiryResult(
            category=category,
            severity=severity,
            summary=self._generate_summary(category, inquiry_text),
            checklist=checklist,
            follow_up_questions=follow_ups,
            relevant_articles=unique_articles[:5],
            confidence=confidence,
        )

    def _detect_category(self, text: str) -> InquiryCategory:
        scores: dict[InquiryCategory, int] = {}
        for category, keywords in _CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[category] = score

        if not scores:
            return InquiryCategory.UNKNOWN

        return max(scores, key=scores.get)  # type: ignore[arg-type]

    def _detect_severity(self, text: str) -> Severity:
        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]:
            keywords = _SEVERITY_INDICATORS[severity]
            if any(kw in text for kw in keywords):
                return severity
        return Severity.MEDIUM

    def _extract_error_codes(self, text: str) -> list[str]:
        pattern = r"(SYNC-\d{3}|AUTH-\d{3}|PERF-\d{3}|API-\d{3}|ACCT-\d{3})"
        return re.findall(pattern, text, re.IGNORECASE)

    def _calculate_confidence(
        self, category: InquiryCategory, articles: list[SearchResult], text: str
    ) -> float:
        confidence = 0.3  # base

        if category != InquiryCategory.UNKNOWN:
            confidence += 0.3

        if articles:
            best_score = max(a.score for a in articles)
            confidence += min(0.3, best_score * 0.3)

        if self._extract_error_codes(text):
            confidence += 0.1

        return min(1.0, confidence)

    def _generate_summary(self, category: InquiryCategory, inquiry_text: str) -> str:
        prefix = {
            InquiryCategory.SYNC: "File synchronization issue",
            InquiryCategory.PERMISSION: "Access/permission issue",
            InquiryCategory.PERFORMANCE: "Performance degradation",
            InquiryCategory.API: "API/integration issue",
            InquiryCategory.ACCOUNT: "Account/billing issue",
            InquiryCategory.FEATURE: "Feature question",
            InquiryCategory.UNKNOWN: "Unclassified inquiry",
        }
        # Truncate inquiry for summary
        short = inquiry_text[:100] + ("..." if len(inquiry_text) > 100 else "")
        return f"{prefix[category]}: {short}"
