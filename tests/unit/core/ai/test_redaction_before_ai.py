"""Customer text is redacted before it reaches Claude, on every path that sends it."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.ai.client import AIClient
from src.core.analyzer.log_analyzer import AILogAnalyzer
from src.core.knowledge.engine import KnowledgeEngine
from src.core.models import InquiryCategory, InquiryResult, Severity
from src.core.responder.drafter import ResponseDrafter

EMAIL = "jane.doe@acme-corp.com"
PHONE = "415-555-0134"
IP = "10.20.30.40"
TOKEN = "lin_api_abcdefgh12345678"


@pytest.fixture
def knowledge_engine(tmp_path: Path, sample_knowledge_dir: Path) -> KnowledgeEngine:
    engine = KnowledgeEngine(persist_dir=str(tmp_path / "chroma"))
    engine.ingest_directory(sample_knowledge_dir)
    return engine


@pytest.fixture
def create():
    """The mocked messages.create, answering with an empty JSON object."""
    block = MagicMock()
    block.type = "text"
    block.text = "{}"
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [block]
    with patch("src.core.ai.client.anthropic") as mock:
        mock.Anthropic.return_value.messages.create.return_value = response
        yield mock.Anthropic.return_value.messages.create


def sent_text(create: MagicMock) -> str:
    """Everything the model was shown in the first call: system prompt and messages."""
    kwargs = create.call_args.kwargs
    return str(kwargs.get("system", "")) + str(kwargs["messages"])


def assert_no_pii(text: str) -> None:
    for secret in (EMAIL, PHONE, IP, TOKEN):
        assert secret not in text, f"{secret} reached the model"


class TestInquiryAnalysis:
    def test_inquiry_is_redacted(self, knowledge_engine, create):
        client = AIClient(knowledge_engine, api_key="test-key")
        client.analyze_inquiry(f"I am {EMAIL}, call {PHONE}. Server {IP} fails, key {TOKEN}")
        shown = sent_text(create)
        assert_no_pii(shown)
        assert "[EMAIL_1]" in shown


class TestLogAnalysis:
    def test_log_summary_is_redacted(self, knowledge_engine, create):
        client = AIClient(knowledge_engine, api_key="test-key")
        client.analyze_logs(f"ERROR login failed for {EMAIL} from {IP}")
        assert_no_pii(sent_text(create))

    def test_raw_logs_through_the_analyzer_are_redacted(self, knowledge_engine, create):
        analyzer = AILogAnalyzer(knowledge_engine, api_key="test-key")
        analyzer.analyze(
            f"2026-11-01T10:00:00Z ERROR auth failed user={EMAIL} ip={IP} token={TOKEN}\n"
        )
        assert_no_pii(sent_text(create))


class TestDrafting:
    def _analysis(self, summary: str) -> InquiryResult:
        return InquiryResult(
            category=InquiryCategory.SYNC,
            severity=Severity.HIGH,
            summary=summary,
            checklist=["Check the sync client version"],
            follow_up_questions=[],
            relevant_articles=[],
            confidence=0.8,
        )

    def test_inquiry_and_analysis_summary_are_redacted(self, knowledge_engine, create):
        drafter = ResponseDrafter(knowledge_engine, api_key="test-key")
        drafter.draft(
            f"Files do not sync for {EMAIL}, reach me on {PHONE}",
            self._analysis(f"sync issue: Files do not sync for {EMAIL} on {IP}"),
        )
        assert_no_pii(sent_text(create))

    def test_knowledge_base_text_is_left_alone(self, knowledge_engine, create):
        """The KB is ours. Its contact addresses must reach the model unchanged."""
        analysis = self._analysis("sync issue")
        analysis.relevant_articles = [
            MagicMock(title="Escalation", category="faq",
                      content="Write to sales@cloudsync.io for enterprise plans.")
        ]
        drafter = ResponseDrafter(knowledge_engine, api_key="test-key")
        drafter.draft("Files do not sync", analysis)
        assert "sales@cloudsync.io" in sent_text(create)
