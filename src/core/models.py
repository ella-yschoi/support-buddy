"""Shared data models for Support Buddy."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class InquiryCategory(str, Enum):
    SYNC = "sync"
    PERMISSION = "permission"
    PERFORMANCE = "performance"
    API = "api"
    ACCOUNT = "account"
    FEATURE = "feature"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class KnowledgeCategory(str, Enum):
    FAQ = "faq"
    TROUBLESHOOTING = "troubleshooting"
    ERROR_CODE = "error_code"
    RUNBOOK = "runbook"
    FEATURE = "feature"


@dataclass
class KnowledgeDoc:
    id: str
    title: str
    content: str
    category: KnowledgeCategory
    source_file: str
    metadata: dict = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class SearchResult:
    doc_id: str
    title: str
    content: str
    category: str
    score: float
    source_file: str


@dataclass
class InquiryResult:
    category: InquiryCategory
    severity: Severity
    summary: str
    checklist: list[str]
    follow_up_questions: list[str]
    relevant_articles: list[SearchResult]
    confidence: float


@dataclass
class LogEvent:
    timestamp: str
    level: str
    message: str
    metadata: dict = field(default_factory=dict)


@dataclass
class LogInsight:
    summary: str
    errors: list[LogEvent]
    slow_operations: list[LogEvent]
    anomalies: list[str]
    timeline: list[LogEvent]
    root_cause_hypothesis: str


@dataclass
class DraftResponse:
    body: str
    citations: list[SearchResult]
    confidence: float
    needs_escalation: bool
    suggested_internal_note: str
