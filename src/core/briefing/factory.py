"""Wire a briefing builder from local or Claude-backed components."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from src.config import DATA_DIR, KNOWLEDGE_DIR
from src.core.ai.registry import ModelRegistry, default_registry
from src.core.analyzer.ai_inquiry import AIInquiryAnalyzer
from src.core.analyzer.inquiry import InquiryAnalyzer
from src.core.analyzer.log_parser import LogParser
from src.core.briefing.budget import DailyAiBudget
from src.core.briefing.builder import AnalyzeFn, BriefingBuilder, DraftFn
from src.core.briefing.routed import RoutedBuilder
from src.core.knowledge.engine import KnowledgeEngine
from src.core.knowledge.loader import KnowledgeLoader
from src.core.models import DraftResponse, InquiryResult, LogInsight
from src.core.pii.redactor import PIIRedactor
from src.core.policy.loader import load_policy
from src.core.responder.drafter import ResponseDrafter, fallback_draft
from src.core.trust.kb_index import build_kb_index

DEFAULT_POLICY_PATH = DATA_DIR / "policy" / "policy.yaml"


def local_log_insight(raw_logs: str) -> LogInsight:
    """Parser-only log analysis: errors, slow operations and error codes, no LLM."""
    parser = LogParser()
    events = parser.parse(raw_logs) if raw_logs.strip() else []
    if not events:
        return LogInsight("No log events found.", [], [], [], [], "No data available for analysis.")

    errors = parser.extract_errors(events)
    slow = parser.extract_slow_operations(events)
    codes = parser.extract_error_codes(events)

    anomalies = []
    if errors:
        anomalies.append(f"{len(errors)} error(s) detected")
    if slow:
        anomalies.append(f"{len(slow)} slow operation(s) detected")

    if codes:
        hypothesis = (
            f"Errors related to code(s): {', '.join(codes)}. "
            "Check the knowledge base for resolution steps."
        )
    elif errors:
        hypothesis = "Errors found without a known error code; review the error messages."
    else:
        hypothesis = "No errors detected in the provided logs."

    return LogInsight(
        summary=parser.generate_text_summary(events),
        errors=errors,
        slow_operations=slow,
        anomalies=anomalies,
        timeline=events,
        root_cause_hypothesis=hypothesis,
    )


def _claude_parts(
    engine: KnowledgeEngine,
    api_key: str | None,
    registry: ModelRegistry | None,
) -> tuple[AnalyzeFn, DraftFn, list[Callable[[], int]]]:
    """Analyze and draft functions that redact PII first, plus a probe per AI stage.

    Each probe returns the tokens that stage has been billed for so far. It rises only when
    Claude answered, because the analyzer and drafter fall back silently on API errors.
    """
    reg = registry or default_registry()
    redactor = PIIRedactor()

    ai_analyzer = AIInquiryAnalyzer(engine, api_key=api_key, model=reg.classify)
    ai_drafter = ResponseDrafter(engine, api_key=api_key, model=reg.draft)

    def pii_analyze(text: str) -> InquiryResult:
        return ai_analyzer.analyze(redactor.redact(text).text)

    def pii_draft(text: str, analysis: InquiryResult) -> DraftResponse:
        return ai_drafter.draft(redactor.redact(text).text, analysis)

    probes = [
        lambda: sum(ai_analyzer.token_usage),
        lambda: sum(ai_drafter.token_usage),
    ]
    return pii_analyze, pii_draft, probes


def build_claude_builder(
    engine: KnowledgeEngine,
    api_key: str | None = None,
    policy_path: Path = DEFAULT_POLICY_PATH,
    knowledge_dir: Path = KNOWLEDGE_DIR,
    registry: ModelRegistry | None = None,
) -> BriefingBuilder:
    """Claude-backed analysis and drafting with PII redaction before every AI call.

    PII (emails, IPs, API keys, phones) is stripped from the inquiry text before
    it reaches any model.  The local builder remains available as the free default.
    """
    analyze, draft, _probes = _claude_parts(engine, api_key, registry)
    return BriefingBuilder(
        analyze=analyze,
        draft=draft,
        analyze_logs=local_log_insight,
        kb_index=build_kb_index(KnowledgeLoader().load_directory(knowledge_dir)),
        policy=load_policy(policy_path),
    )


def build_routed_builder(
    engine: KnowledgeEngine,
    budget: DailyAiBudget,
    api_key: str | None = None,
    policy_path: Path = DEFAULT_POLICY_PATH,
    knowledge_dir: Path = KNOWLEDGE_DIR,
    registry: ModelRegistry | None = None,
) -> RoutedBuilder:
    """Claude while the daily budget lasts, the local builder after, labelled either way."""
    analyze, draft, probes = _claude_parts(engine, api_key, registry)
    kb_index = build_kb_index(KnowledgeLoader().load_directory(knowledge_dir))
    policy = load_policy(policy_path)
    ai = BriefingBuilder(
        analyze=analyze, draft=draft, analyze_logs=local_log_insight,
        kb_index=kb_index, policy=policy,
    )
    return RoutedBuilder(
        ai,
        build_local_builder(engine, policy_path, knowledge_dir),
        budget,
        probes,
    )


def build_local_builder(
    engine: KnowledgeEngine,
    policy_path: Path = DEFAULT_POLICY_PATH,
    knowledge_dir: Path = KNOWLEDGE_DIR,
) -> BriefingBuilder:
    """Keyword analysis + template drafts + parser-only logs: free and deterministic."""
    analyzer = InquiryAnalyzer(engine)

    def draft(_text: str, analysis: InquiryResult) -> DraftResponse:
        return fallback_draft(analysis)

    return BriefingBuilder(
        analyze=analyzer.classify,
        draft=draft,
        analyze_logs=local_log_insight,
        kb_index=build_kb_index(KnowledgeLoader().load_directory(knowledge_dir)),
        policy=load_policy(policy_path),
    )
