"""Pipelines under evaluation. A pipeline turns an inquiry into an analysis and a draft."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.core.ai.registry import ModelRegistry
from src.core.analyzer.ai_inquiry import AIInquiryAnalyzer
from src.core.analyzer.inquiry import InquiryAnalyzer
from src.core.exceptions import AIClientError
from src.core.knowledge.engine import KnowledgeEngine
from src.core.models import DraftResponse, InquiryResult
from src.core.responder.drafter import ResponseDrafter, fallback_draft
from src.eval.cases import GoldenCase
from src.eval.models import Usage
from src.eval.pricing import estimate_cost


@dataclass(frozen=True)
class PipelineOutput:
    analysis: InquiryResult
    draft: DraftResponse | None
    usage: Usage


class Pipeline(Protocol):
    def run(self, case: GoldenCase) -> PipelineOutput: ...


class LocalPipeline:
    """Keyword classifier + template draft. No API calls, so it is free and deterministic."""

    def __init__(self, knowledge_engine: KnowledgeEngine):
        self._analyzer = InquiryAnalyzer(knowledge_engine)

    def run(self, case: GoldenCase) -> PipelineOutput:
        analysis = self._analyzer.classify(case.inquiry)
        return PipelineOutput(analysis, fallback_draft(analysis), Usage())


class ClaudePipeline:
    """Claude-backed classification and drafting using the models of a ModelRegistry."""

    def __init__(
        self, knowledge_engine: KnowledgeEngine, registry: ModelRegistry, api_key: str | None = None
    ):
        self._registry = registry
        self._analyzer = AIInquiryAnalyzer(knowledge_engine, api_key, model=registry.classify)
        self._drafter = ResponseDrafter(knowledge_engine, api_key, model=registry.draft)

    def run(self, case: GoldenCase) -> PipelineOutput:
        in0, out0 = self._analyzer.token_usage
        analysis = self._analyzer.analyze(case.inquiry)
        in1, out1 = self._analyzer.token_usage
        classify_tokens = (in1 - in0, out1 - out0)

        din0, dout0 = self._drafter.token_usage
        draft = self._drafter.draft(case.inquiry, analysis)
        din1, dout1 = self._drafter.token_usage
        draft_tokens = (din1 - din0, dout1 - dout0)

        # The AI components silently fall back to keyword/template output when the API
        # fails. That would be measured as "Claude" results, so treat it as an error.
        if classify_tokens[0] == 0 or draft_tokens[0] == 0:
            raise AIClientError("API call produced no tokens; component fell back to local output")

        cost = (estimate_cost(self._registry.classify, *classify_tokens) or 0.0) + (
            estimate_cost(self._registry.draft, *draft_tokens) or 0.0
        )
        usage = Usage(
            input_tokens=classify_tokens[0] + draft_tokens[0],
            output_tokens=classify_tokens[1] + draft_tokens[1],
            cost_usd=cost,
        )
        return PipelineOutput(analysis, draft, usage)
