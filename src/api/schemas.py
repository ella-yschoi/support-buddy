"""Pydantic schemas for API request/response models."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    inquiry: str = Field(..., description="Customer inquiry text")
    use_ai: bool = Field(False, description="Use Claude AI for enhanced analysis")
    lang: str = Field("en", description="Response language: en or ko")


class LogAnalyzeRequest(BaseModel):
    logs: str = Field(..., description="Raw log content (JSON or text)")
    use_ai: bool = Field(False, description="Use Claude AI for enhanced analysis")
    lang: str = Field("en", description="Response language: en or ko")


class DraftRequest(BaseModel):
    inquiry: str = Field(..., description="Customer inquiry text")
    lang: str = Field("en", description="Response language: en or ko")


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    category: Optional[str] = Field(None, description="Filter by category")
    top_k: int = Field(5, ge=1, le=20, description="Number of results")


class IngestRequest(BaseModel):
    path: str = Field(..., description="Path to file or directory to ingest")


class EmailAnalyzeRequest(BaseModel):
    raw_email: str = Field(..., description="Raw email content")
    use_ai: bool = Field(False, description="Use Claude AI for analysis")
    lang: str = Field("en", description="Response language: en or ko")


class SearchResultResponse(BaseModel):
    doc_id: str
    title: str
    content: str
    category: str
    score: float
    source_file: str


class AnalyzeResponse(BaseModel):
    category: str
    severity: str
    summary: str
    checklist: list[str]
    follow_up_questions: list[str]
    relevant_articles: list[SearchResultResponse]
    confidence: float


class LogAnalyzeResponse(BaseModel):
    summary: str
    errors: list[dict]
    slow_operations: list[dict]
    anomalies: list[str]
    root_cause_hypothesis: str


class DraftResponseModel(BaseModel):
    body: str
    confidence: float
    needs_escalation: bool
    suggested_internal_note: str
    citations: list[SearchResultResponse]


class EmailParseResponse(BaseModel):
    sender: str
    subject: str
    body: str
    error_codes: list[str]
    analysis: Optional[AnalyzeResponse] = None


class HealthResponse(BaseModel):
    status: str
    knowledge_docs: int


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value


class BriefingRequest(BaseModel):
    inquiry: str = Field(..., description="Customer inquiry text")
    plan: Literal["free", "pro", "enterprise", "unknown"] = "unknown"
    logs: str = Field("", description="Optional raw log content")

    _check_inquiry = field_validator("inquiry")(_not_blank)


class ApproveRequest(BaseModel):
    final_body: str = Field(..., description="The text the TSE actually sent")

    _check_body = field_validator("final_body")(_not_blank)


class HypothesisModel(BaseModel):
    statement: str
    log_evidence: list[str]
    kb_evidence: list[str]


class CitationModel(BaseModel):
    doc_id: str
    title: str


class CheckModel(BaseModel):
    name: str
    passed: bool
    detail: str


class BriefingResponse(BaseModel):
    id: str
    created_at: str
    inquiry_text: str
    customer_plan: str
    summary: str
    category: str
    model_severity: str
    effective_severity: str
    hypotheses: list[HypothesisModel]
    citations: list[CitationModel]
    checks: list[CheckModel]
    verification_score: float
    verification_passed: bool
    autonomy: str
    autonomy_reasons: list[str]
    simulated: bool
    draft_body: Optional[str]
    sufficiency: str
    sufficiency_reasons: list[str]
    status: str
    approved_body: Optional[str]
    edit_ratio: Optional[float]


class PolicyResponse(BaseModel):
    auto_send_enabled: bool
    human_only_keywords: list[str]
    human_only_categories: list[str]
    human_only_min_severity: str
    human_only_score_below: float
    confirm_plans: list[str]
    confirm_min_severity: str
    auto_categories: list[str]
    auto_max_severity: str
    auto_min_score: float
