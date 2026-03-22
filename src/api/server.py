"""FastAPI server for Support Buddy."""

from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException

from src.config import ANTHROPIC_API_KEY, KNOWLEDGE_DIR
from src.core.analyzer.inquiry import InquiryAnalyzer
from src.core.analyzer.log_parser import LogParser
from src.core.knowledge.engine import KnowledgeEngine
from src.integrations.email.parser import EmailParser

from src.api.schemas import (
    AnalyzeRequest, AnalyzeResponse,
    DraftRequest, DraftResponseModel,
    EmailAnalyzeRequest, EmailParseResponse,
    HealthResponse,
    IngestRequest,
    LogAnalyzeRequest, LogAnalyzeResponse,
    SearchRequest, SearchResultResponse,
)

app = FastAPI(
    title="Support Buddy API",
    description="AI-powered support tool for Technical Support Engineers",
    version="0.2.0",
)

# Shared engine instance
_engine: Optional[KnowledgeEngine] = None


def get_engine() -> KnowledgeEngine:
    global _engine
    if _engine is None:
        _engine = KnowledgeEngine()
        if KNOWLEDGE_DIR.is_dir():
            _engine.ingest_directory(KNOWLEDGE_DIR)
    return _engine


def _to_search_result_response(r) -> SearchResultResponse:
    return SearchResultResponse(
        doc_id=r.doc_id, title=r.title, content=r.content,
        category=r.category, score=r.score, source_file=r.source_file,
    )


@app.get("/api/v1/health", response_model=HealthResponse)
def health():
    engine = get_engine()
    return HealthResponse(status="ok", knowledge_docs=engine.doc_count())


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    engine = get_engine()

    if req.use_ai:
        if not ANTHROPIC_API_KEY:
            raise HTTPException(400, "ANTHROPIC_API_KEY not configured")
        from src.core.analyzer.ai_inquiry import AIInquiryAnalyzer
        analyzer = AIInquiryAnalyzer(engine)
        result = analyzer.analyze(req.inquiry)
    else:
        analyzer = InquiryAnalyzer(engine)
        result = analyzer.classify(req.inquiry)

    return AnalyzeResponse(
        category=result.category.value,
        severity=result.severity.value,
        summary=result.summary,
        checklist=result.checklist,
        follow_up_questions=result.follow_up_questions,
        relevant_articles=[_to_search_result_response(a) for a in result.relevant_articles],
        confidence=result.confidence,
    )


@app.post("/api/v1/logs/analyze", response_model=LogAnalyzeResponse)
def analyze_logs(req: LogAnalyzeRequest):
    if req.use_ai:
        if not ANTHROPIC_API_KEY:
            raise HTTPException(400, "ANTHROPIC_API_KEY not configured")
        engine = get_engine()
        from src.core.analyzer.log_analyzer import AILogAnalyzer
        ai_analyzer = AILogAnalyzer(engine)
        insight = ai_analyzer.analyze(req.logs)

        return LogAnalyzeResponse(
            summary=insight.summary,
            errors=[{"timestamp": e.timestamp, "level": e.level, "message": e.message} for e in insight.errors],
            slow_operations=[{"timestamp": s.timestamp, "message": s.message, "duration_ms": s.metadata.get("duration_ms")} for s in insight.slow_operations],
            anomalies=insight.anomalies,
            root_cause_hypothesis=insight.root_cause_hypothesis,
        )
    else:
        parser = LogParser()
        events = parser.parse(req.logs)
        if not events:
            raise HTTPException(400, "No log events could be parsed")

        errors = parser.extract_errors(events)
        slow_ops = parser.extract_slow_operations(events)
        summary = parser.generate_text_summary(events)

        return LogAnalyzeResponse(
            summary=summary,
            errors=[{"timestamp": e.timestamp, "level": e.level, "message": e.message} for e in errors],
            slow_operations=[{"timestamp": s.timestamp, "message": s.message, "duration_ms": s.metadata.get("duration_ms")} for s in slow_ops],
            anomalies=[],
            root_cause_hypothesis="",
        )


@app.post("/api/v1/draft-response", response_model=DraftResponseModel)
def draft_response(req: DraftRequest):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(400, "ANTHROPIC_API_KEY not configured")

    engine = get_engine()
    from src.core.analyzer.ai_inquiry import AIInquiryAnalyzer
    from src.core.responder.drafter import ResponseDrafter

    analyzer = AIInquiryAnalyzer(engine)
    analysis = analyzer.analyze(req.inquiry)

    drafter = ResponseDrafter(engine)
    response = drafter.draft(req.inquiry, analysis)

    return DraftResponseModel(
        body=response.body,
        confidence=response.confidence,
        needs_escalation=response.needs_escalation,
        suggested_internal_note=response.suggested_internal_note,
        citations=[_to_search_result_response(c) for c in response.citations],
    )


@app.get("/api/v1/knowledge/search", response_model=list[SearchResultResponse])
def search_knowledge(query: str, category: Optional[str] = None, top_k: int = 5):
    engine = get_engine()
    results = engine.search(query, top_k=top_k, category=category)
    return [_to_search_result_response(r) for r in results]


@app.post("/api/v1/knowledge/ingest")
def ingest_knowledge(req: IngestRequest):
    engine = get_engine()
    p = Path(req.path)
    if p.is_dir():
        count = engine.ingest_directory(p)
    elif p.is_file():
        count = engine.ingest_file(p)
    else:
        raise HTTPException(404, f"Path not found: {req.path}")
    return {"ingested_chunks": count}


@app.post("/api/v1/email/analyze", response_model=EmailParseResponse)
def analyze_email(req: EmailAnalyzeRequest):
    email_parser = EmailParser()
    parsed = email_parser.parse(req.raw_email)

    analysis = None
    if parsed.body:
        engine = get_engine()
        inquiry_text = parsed.to_inquiry_text()

        if req.use_ai and ANTHROPIC_API_KEY:
            from src.core.analyzer.ai_inquiry import AIInquiryAnalyzer
            analyzer = AIInquiryAnalyzer(engine)
            result = analyzer.analyze(inquiry_text)
        else:
            analyzer = InquiryAnalyzer(engine)
            result = analyzer.classify(inquiry_text)

        analysis = AnalyzeResponse(
            category=result.category.value,
            severity=result.severity.value,
            summary=result.summary,
            checklist=result.checklist,
            follow_up_questions=result.follow_up_questions,
            relevant_articles=[_to_search_result_response(a) for a in result.relevant_articles],
            confidence=result.confidence,
        )

    return EmailParseResponse(
        sender=parsed.sender,
        subject=parsed.subject,
        body=parsed.body,
        error_codes=parsed.error_codes,
        analysis=analysis,
    )
