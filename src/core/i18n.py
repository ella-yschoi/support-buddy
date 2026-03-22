"""Internationalization support for Korean/English bilingual output."""

import re
from enum import Enum


class Language(str, Enum):
    EN = "en"
    KO = "ko"


_HANGUL_PATTERN = re.compile(r"[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]")


def detect_language(text: str) -> Language:
    """Detect language from text based on Hangul character presence."""
    if _HANGUL_PATTERN.search(text):
        return Language.KO
    return Language.EN


_STRINGS: dict[str, dict[Language, str]] = {
    "checklist_title": {
        Language.EN: "Checklist:",
        Language.KO: "체크리스트:",
    },
    "follow_up_title": {
        Language.EN: "Suggested Follow-up Questions:",
        Language.KO: "추천 후속 질문:",
    },
    "inquiry_analysis_title": {
        Language.EN: "Inquiry Analysis",
        Language.KO: "문의 분석",
    },
    "ai_inquiry_analysis_title": {
        Language.EN: "AI-Powered Inquiry Analysis",
        Language.KO: "AI 기반 문의 분석",
    },
    "log_analysis_title": {
        Language.EN: "Log Analysis",
        Language.KO: "로그 분석",
    },
    "ai_log_analysis_title": {
        Language.EN: "AI Log Analysis",
        Language.KO: "AI 로그 분석",
    },
    "draft_response_title": {
        Language.EN: "Draft Response",
        Language.KO: "응답 초안",
    },
    "internal_note_title": {
        Language.EN: "Internal Note (not sent to customer)",
        Language.KO: "내부 메모 (고객에게 전송되지 않음)",
    },
    "kb_articles_title": {
        Language.EN: "Relevant Knowledge Base Articles",
        Language.KO: "관련 지식 베이스 문서",
    },
    "low_confidence_warning": {
        Language.EN: "Low confidence — consider escalating to a senior TSE.",
        Language.KO: "신뢰도 낮음 — 시니어 TSE에게 에스컬레이션을 고려하세요.",
    },
    "no_results": {
        Language.EN: "No results found.",
        Language.KO: "결과를 찾을 수 없습니다.",
    },
    "no_log_events": {
        Language.EN: "No log events could be parsed from the input.",
        Language.KO: "입력에서 로그 이벤트를 파싱할 수 없습니다.",
    },
    "api_key_missing": {
        Language.EN: "Error: ANTHROPIC_API_KEY not set. Use without --ai or set the key.",
        Language.KO: "오류: ANTHROPIC_API_KEY가 설정되지 않았습니다. --ai 없이 사용하거나 키를 설정하세요.",
    },
    "using_ai_analysis": {
        Language.EN: "Using Claude AI for analysis...",
        Language.KO: "Claude AI로 분석 중...",
    },
    "using_ai_log_analysis": {
        Language.EN: "Using Claude AI for log analysis...",
        Language.KO: "Claude AI로 로그 분석 중...",
    },
    "analyzing_inquiry": {
        Language.EN: "Analyzing inquiry...",
        Language.KO: "문의 분석 중...",
    },
    "generating_draft": {
        Language.EN: "Generating response draft...",
        Language.KO: "응답 초안 생성 중...",
    },
    "loaded_chunks": {
        Language.EN: "Loaded {count} knowledge chunks from {path}",
        Language.KO: "{path}에서 {count}개의 지식 청크를 로드했습니다",
    },
    "kb_not_found": {
        Language.EN: "Warning: Knowledge directory not found: {path}",
        Language.KO: "경고: 지식 디렉토리를 찾을 수 없습니다: {path}",
    },
    "path_not_found": {
        Language.EN: "Path not found: {path}",
        Language.KO: "경로를 찾을 수 없습니다: {path}",
    },
    "ingested_chunks": {
        Language.EN: "Ingested {count} document chunks from {path}",
        Language.KO: "{path}에서 {count}개의 문서 청크를 수집했습니다",
    },
    "no_documentation_found": {
        Language.EN: "No documentation found",
        Language.KO: "문서를 찾을 수 없습니다",
    },
    "needs_escalation_yes": {
        Language.EN: "YES — Escalation Recommended",
        Language.KO: "예 — 에스컬레이션 권장",
    },
    "needs_escalation_no": {
        Language.EN: "No",
        Language.KO: "아니오",
    },
    "needs_escalation_label": {
        Language.EN: "Needs escalation: ",
        Language.KO: "에스컬레이션 필요: ",
    },
    "sources_title": {
        Language.EN: "Sources:",
        Language.KO: "출처:",
    },
    "summary_label": {
        Language.EN: "Summary:",
        Language.KO: "요약:",
    },
    "root_cause_label": {
        Language.EN: "Root Cause Hypothesis:",
        Language.KO: "근본 원인 가설:",
    },
    "anomalies_label": {
        Language.EN: "Anomalies Detected:",
        Language.KO: "감지된 이상 항목:",
    },
    "errors_found": {
        Language.EN: "{count} Error(s):",
        Language.KO: "{count}개의 오류:",
    },
    "slow_ops_found": {
        Language.EN: "{count} Slow Operation(s):",
        Language.KO: "{count}개의 느린 작업:",
    },
    "error_code_details": {
        Language.EN: "Error Code Details:",
        Language.KO: "오류 코드 상세:",
    },
    "col_title": {
        Language.EN: "Title",
        Language.KO: "제목",
    },
    "col_category": {
        Language.EN: "Category",
        Language.KO: "카테고리",
    },
    "col_score": {
        Language.EN: "Score",
        Language.KO: "점수",
    },
}


def t(key: str, lang: Language = Language.EN) -> str:
    """Translate a string key to the given language."""
    entry = _STRINGS.get(key)
    if entry is None:
        return key
    return entry.get(lang, entry.get(Language.EN, key))
