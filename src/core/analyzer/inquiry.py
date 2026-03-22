"""Inquiry analyzer — classify, generate checklist, and suggest follow-ups."""

from __future__ import annotations

import re
from typing import Optional

from src.core.i18n import Language, detect_language
from src.core.knowledge.engine import KnowledgeEngine
from src.core.models import InquiryCategory, InquiryResult, SearchResult, Severity

# Keyword-based classification rules (used for local classification without AI)
# Both English and Korean keywords are merged so detection works for either language.
_CATEGORY_KEYWORDS: dict[InquiryCategory, list[str]] = {
    InquiryCategory.SYNC: [
        "sync", "syncing", "not syncing", "file conflict", "upload failed",
        "download failed", "sync-0", "not appearing", "missing file",
        "동기화", "싱크", "파일 충돌", "업로드 실패", "다운로드 실패",
        "파일 누락", "동기화 안됨", "동기화가 안",
    ],
    InquiryCategory.PERMISSION: [
        "permission", "access denied", "can't access", "cannot access",
        "shared folder", "auth-0", "not authorized", "forbidden", "role",
        "권한", "접근 거부", "접근 불가", "접근이 안", "공유 폴더",
        "인증", "금지", "역할",
    ],
    InquiryCategory.PERFORMANCE: [
        "slow", "loading", "performance", "timeout", "perf-0", "lag",
        "takes long", "hanging", "unresponsive", "speed",
        "느림", "느려", "느립니다", "로딩", "성능", "타임아웃",
        "지연", "응답 없음", "속도",
    ],
    InquiryCategory.API: [
        "api", "webhook", "endpoint", "rate limit", "api-0", "integration",
        "rest", "callback", "payload",
        "웹훅", "엔드포인트", "속도 제한", "연동", "콜백",
    ],
    InquiryCategory.ACCOUNT: [
        "account", "billing", "team member", "invite", "subscription",
        "plan", "upgrade", "acct-0", "greyed out", "grayed out",
        "계정", "결제", "팀원", "초대", "구독", "요금제", "업그레이드",
    ],
    InquiryCategory.FEATURE: [
        "how do i", "how to", "set up", "configure", "enable", "feature",
        "what is", "can i",
        "어떻게", "설정", "활성화", "기능", "방법", "사용법",
    ],
}

_SEVERITY_INDICATORS: dict[Severity, list[str]] = {
    Severity.CRITICAL: [
        "data loss", "all files gone", "deleted everything", "production down",
        "entire organization", "sso failure for all",
        "데이터 손실", "파일 전부 삭제", "프로덕션 장애", "전체 조직",
        "모든 파일이 사라", "전부 삭제",
    ],
    Severity.HIGH: [
        "can't login", "cannot access", "broken", "not working at all",
        "urgent", "critical", "blocking", "all users",
        "로그인 불가", "접근 불가", "작동 안함", "전혀 안",
        "긴급", "차단", "모든 사용자",
    ],
    Severity.MEDIUM: [
        "error", "failed", "not working", "issue", "problem",
        "오류", "실패", "안됨", "안 됨", "문제",
    ],
    Severity.LOW: [
        "how to", "question", "wondering", "feature request", "slow",
        "질문", "궁금", "기능 요청", "느림",
    ],
}

# Checklist templates by category — English
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

# Checklist templates by category — Korean
_CHECKLISTS_KO: dict[InquiryCategory, list[str]] = {
    InquiryCategory.SYNC: [
        "동기화 에이전트가 실행 중인지 확인 (트레이 아이콘 상태)",
        "네트워크 연결 상태 확인",
        "설정 > 로그에서 오류 코드 확인",
        "파일 크기가 5GB 제한 이내인지 확인",
        "파일 경로에 특수 문자가 포함되어 있는지 확인",
        "어떤 기기에서 문제가 발생하는지 확인",
        "저장소 용량 확인",
    ],
    InquiryCategory.PERMISSION: [
        "사용자의 현재 워크스페이스 역할 확인",
        "폴더/파일 공유가 아직 활성 상태인지 확인",
        "사용자 계정이 정지되었는지 확인",
        "SSO 사용자의 경우 IdP에서 그룹 멤버십 확인",
        "마지막으로 접근 가능했던 시점 확인",
    ],
    InquiryCategory.PERFORMANCE: [
        "무엇이 느린지 확인 (동기화, 대시보드, API, 데스크톱 클라이언트)",
        "시스템 상태 페이지에서 알려진 이슈 확인",
        "구체적인 수치 확인 (정상 속도 vs. 현재 속도)",
        "클라이언트 버전 및 OS 확인",
        "네트워크 속도 테스트 결과 요청",
    ],
    InquiryCategory.API: [
        "호출 중인 API 엔드포인트 확인",
        "API 키가 유효하고 만료되지 않았는지 확인",
        "Rate limit 상태 확인",
        "전체 요청/응답 내용 요청 (인증 헤더 제외)",
        "최근 변경 사항이 있었는지 확인 (배포, 키 교체)",
    ],
    InquiryCategory.ACCOUNT: [
        "고객의 현재 요금제 및 제한 사항 확인",
        "사용자 역할 확인 (일부 작업에는 관리자 권한 필요)",
        "계정의 활성 제한 사항 확인",
        "어떤 작업에서 실패하는지 확인",
    ],
    InquiryCategory.FEATURE: [
        "문의 대상 기능 확인",
        "고객의 요금제 확인 (업그레이드가 필요할 수 있음)",
        "지식 베이스에서 기능 문서 검색",
    ],
    InquiryCategory.UNKNOWN: [
        "문제에 대한 추가 정보 요청",
        "해당되는 경우 스크린샷 요청",
        "클라이언트 버전 및 OS 확인",
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

_FOLLOW_UPS_KO: dict[InquiryCategory, list[str]] = {
    InquiryCategory.SYNC: [
        "어떤 기기에서 동기화 문제가 발생하나요?",
        "문제를 처음 발견한 시점이 언제인가요?",
        "모든 파일에 영향이 있나요, 아니면 특정 파일만 해당되나요?",
        "오류 메시지나 코드가 표시되나요?",
    ],
    InquiryCategory.PERMISSION: [
        "오류가 발생했을 때 어떤 작업을 수행하려고 했나요?",
        "이전에는 이 리소스에 접근할 수 있었나요?",
        "최근에 역할이나 팀 멤버십이 변경되었나요?",
    ],
    InquiryCategory.PERFORMANCE: [
        "느려지기 시작한 시점이 언제인가요?",
        "모든 작업에 영향이 있나요, 아니면 특정 작업만 해당되나요?",
        "동기화 대상 파일/폴더가 몇 개인가요?",
        "네트워크 대역폭이 어느 정도인가요?",
    ],
    InquiryCategory.API: [
        "어떤 HTTP 상태 코드를 받고 있나요?",
        "API 엔드포인트와 메서드를 공유해 주시겠어요?",
        "문제가 간헐적인가요, 아니면 지속적인가요?",
        "최근에 연동 설정에 변경 사항이 있었나요?",
    ],
    InquiryCategory.ACCOUNT: [
        "어떤 작업을 수행하려고 하시나요?",
        "현재 요금제가 무엇인가요?",
        "워크스페이스 관리자이신가요?",
    ],
    InquiryCategory.FEATURE: [
        "현재 어떤 요금제를 사용 중이신가요?",
        "무엇을 달성하려고 하시나요?",
    ],
    InquiryCategory.UNKNOWN: [
        "문제를 좀 더 자세히 설명해 주시겠어요?",
        "문제가 발생했을 때 무엇을 하고 계셨나요?",
        "스크린샷이나 오류 메시지를 공유해 주시겠어요?",
    ],
}

# Summary prefixes by language
_SUMMARY_PREFIXES: dict[Language, dict[InquiryCategory, str]] = {
    Language.EN: {
        InquiryCategory.SYNC: "File synchronization issue",
        InquiryCategory.PERMISSION: "Access/permission issue",
        InquiryCategory.PERFORMANCE: "Performance degradation",
        InquiryCategory.API: "API/integration issue",
        InquiryCategory.ACCOUNT: "Account/billing issue",
        InquiryCategory.FEATURE: "Feature question",
        InquiryCategory.UNKNOWN: "Unclassified inquiry",
    },
    Language.KO: {
        InquiryCategory.SYNC: "파일 동기화 문제",
        InquiryCategory.PERMISSION: "접근/권한 문제",
        InquiryCategory.PERFORMANCE: "성능 저하",
        InquiryCategory.API: "API/연동 문제",
        InquiryCategory.ACCOUNT: "계정/결제 문제",
        InquiryCategory.FEATURE: "기능 관련 문의",
        InquiryCategory.UNKNOWN: "미분류 문의",
    },
}


class InquiryAnalyzer:
    """Analyze customer inquiries using keyword classification and knowledge base search."""

    def __init__(self, knowledge_engine: KnowledgeEngine):
        self._knowledge = knowledge_engine

    def classify(self, inquiry_text: str, lang: Language | None = None) -> InquiryResult:
        """Classify an inquiry and generate guidance for the TSE."""
        if lang is None:
            lang = detect_language(inquiry_text)

        text_lower = inquiry_text.lower()

        category = self._detect_category(text_lower)
        severity = self._detect_severity(text_lower)

        checklists = _CHECKLISTS_KO if lang == Language.KO else _CHECKLISTS
        follow_ups = _FOLLOW_UPS_KO if lang == Language.KO else _FOLLOW_UPS

        checklist = checklists.get(category, checklists[InquiryCategory.UNKNOWN])
        follow_up = follow_ups.get(category, follow_ups[InquiryCategory.UNKNOWN])

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
            summary=self._generate_summary(category, inquiry_text, lang),
            checklist=checklist,
            follow_up_questions=follow_up,
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

    def _generate_summary(
        self, category: InquiryCategory, inquiry_text: str, lang: Language = Language.EN
    ) -> str:
        prefix = _SUMMARY_PREFIXES[lang]
        short = inquiry_text[:100] + ("..." if len(inquiry_text) > 100 else "")
        return f"{prefix[category]}: {short}"
