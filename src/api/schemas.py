"""Pydantic schemas for API request/response models."""

from typing import List, Optional

from pydantic import BaseModel, Field


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
