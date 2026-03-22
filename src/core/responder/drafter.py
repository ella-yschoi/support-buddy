"""Response drafter — generate customer-facing response drafts."""

from __future__ import annotations

import json
from typing import Any

from src.config import MODEL_STANDARD
from src.core.ai.client import AIClient
from src.core.ai.prompts import RESPONSE_DRAFT_PROMPT
from src.core.knowledge.engine import KnowledgeEngine
from src.core.models import DraftResponse, InquiryResult, SearchResult


class ResponseDrafter:
    """Generate customer response drafts using Claude AI (Sonnet)."""

    def __init__(self, knowledge_engine: KnowledgeEngine, api_key: str | None = None):
        self._knowledge = knowledge_engine
        # Response drafting is complex — always use Sonnet
        self._ai_client = AIClient(knowledge_engine, api_key=api_key, model=MODEL_STANDARD)

    def draft(self, inquiry_text: str, analysis: InquiryResult) -> DraftResponse:
        """Generate a response draft based on inquiry and analysis results."""
        # Build context for Claude
        context = self._build_context(inquiry_text, analysis)

        try:
            raw = self._ai_client._run_with_tools(
                system_prompt=RESPONSE_DRAFT_PROMPT,
                user_message=context,
            )
            return self._build_response(raw, analysis)
        except Exception:
            return self._fallback_response(inquiry_text, analysis)

    def _build_context(self, inquiry_text: str, analysis: InquiryResult) -> str:
        """Build the prompt context from inquiry + analysis."""
        articles_text = ""
        if analysis.relevant_articles:
            articles_text = "\n\nRelevant knowledge base articles:\n"
            for a in analysis.relevant_articles[:3]:
                articles_text += f"\n### {a.title} ({a.category})\n{a.content[:500]}\n"

        checklist_text = "\n".join(f"- {c}" for c in analysis.checklist)

        return (
            f"Draft a customer support response for the following inquiry.\n\n"
            f"**Customer inquiry:**\n{inquiry_text}\n\n"
            f"**Analysis:**\n"
            f"- Category: {analysis.category.value}\n"
            f"- Severity: {analysis.severity.value}\n"
            f"- Summary: {analysis.summary}\n"
            f"- Checklist for TSE:\n{checklist_text}\n"
            f"{articles_text}\n\n"
            f"Respond with a JSON object containing:\n"
            f"- body (string): the customer-facing email/message response\n"
            f"- confidence (float 0-1): how confident you are in this response\n"
            f"- needs_escalation (boolean): whether this should be escalated\n"
            f"- internal_note (string): a note for the TSE (not sent to customer)"
        )

    def _build_response(
        self, raw: dict[str, Any], analysis: InquiryResult
    ) -> DraftResponse:
        """Build DraftResponse from AI output."""
        if raw.get("parse_error"):
            # Use the raw text as the body
            return DraftResponse(
                body=raw.get("raw_response", "Unable to generate response."),
                citations=analysis.relevant_articles[:3],
                confidence=0.3,
                needs_escalation=True,
                suggested_internal_note="AI response could not be parsed into structured format.",
            )

        confidence = raw.get("confidence", 0.5)
        if not isinstance(confidence, (int, float)):
            confidence = 0.5

        needs_escalation = raw.get("needs_escalation", False)
        if not isinstance(needs_escalation, bool):
            needs_escalation = str(needs_escalation).lower() == "true"

        return DraftResponse(
            body=str(raw.get("body", "Unable to generate response.")),
            citations=analysis.relevant_articles[:3],
            confidence=max(0.0, min(1.0, float(confidence))),
            needs_escalation=needs_escalation,
            suggested_internal_note=str(raw.get("internal_note", "")),
        )

    def _fallback_response(
        self, inquiry_text: str, analysis: InquiryResult
    ) -> DraftResponse:
        """Generate a basic response without AI."""
        checklist = "\n".join(f"  {i}. {c}" for i, c in enumerate(analysis.checklist, 1))

        body = (
            f"Thank you for reaching out to CloudSync Support.\n\n"
            f"I understand you're experiencing an issue related to "
            f"{analysis.category.value}. I'd like to help resolve this for you.\n\n"
            f"To investigate further, could you please check the following:\n"
            f"{checklist}\n\n"
        )

        if analysis.follow_up_questions:
            questions = "\n".join(f"  - {q}" for q in analysis.follow_up_questions[:3])
            body += (
                f"Additionally, it would help if you could provide:\n"
                f"{questions}\n\n"
            )

        body += (
            "Please don't hesitate to reply with any additional information, "
            "and I'll work to get this resolved for you as quickly as possible.\n\n"
            "Best regards,\nCloudSync Support Team"
        )

        return DraftResponse(
            body=body,
            citations=analysis.relevant_articles[:3],
            confidence=0.4,
            needs_escalation=analysis.confidence < 0.6,
            suggested_internal_note=(
                f"Auto-generated fallback response (AI unavailable). "
                f"Category: {analysis.category.value}, "
                f"Severity: {analysis.severity.value}."
            ),
        )
