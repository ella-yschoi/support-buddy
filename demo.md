# Support Buddy Demo Guide

총 10-15분 기준, 3개 시나리오로 구성합니다.

---

## 시나리오 1: 고객 이메일 인입 → 즉시 분석 (3분)

**스토리:** "신규 TSE가 첫 날, 고객 이메일을 받았다"

**Email Analysis** 페이지에서 아래 이메일을 붙여넣기:

```
From: john.park@acmecorp.com
To: support@cloudsync.io
Subject: Urgent - Files not syncing and getting SYNC-002 error

Hi Support Team,

Since this morning, none of our team's files are syncing. We have about 200 employees using CloudSync and everyone is affected.

We keep seeing error code SYNC-002 when trying to upload any file larger than 50MB. We already tried restarting the sync agent on multiple machines but the issue persists.

This is blocking our entire team's work. Please help ASAP.

Thanks,
John Park
IT Manager, Acme Corp
```

**보여줄 포인트:**
- 이메일 자동 파싱 (발신자, 제목, 에러코드 추출)
- 즉시 분류: `SYNC` / `HIGH` severity
- 체크리스트가 바로 나옴 → "신규 TSE도 뭘 확인해야 할지 즉시 알 수 있다"

---

## 시나리오 2: 로그 분석으로 근본 원인 파악 (4분)

**스토리:** "고객이 로그를 보내왔다. 쿼리 없이 무엇이 문제인지 파악한다"

**Log Analysis** 페이지에서 `data/sample_logs/sync_error.json` 업로드 또는 내용 붙여넣기:

```json
[
  {"timestamp": "2024-01-15T10:00:00Z", "level": "INFO", "message": "Sync session started", "service": "sync-engine", "user_id": "user-123"},
  {"timestamp": "2024-01-15T10:00:05Z", "level": "INFO", "message": "Uploading 12 modified files", "service": "sync-engine"},
  {"timestamp": "2024-01-15T10:00:15Z", "level": "WARN", "message": "Slow upload detected: presentation_final.pptx (850MB, 25.3s)", "service": "sync-engine", "duration_ms": 25300},
  {"timestamp": "2024-01-15T10:00:42Z", "level": "ERROR", "message": "Upload failed: SYNC-002 - Storage quota exceeded for user-123", "service": "sync-engine", "error_code": "SYNC-002"},
  {"timestamp": "2024-01-15T10:00:55Z", "level": "ERROR", "message": "Upload failed: SYNC-002 - Storage quota exceeded for user-123", "service": "sync-engine", "error_code": "SYNC-002"},
  {"timestamp": "2024-01-15T10:01:08Z", "level": "ERROR", "message": "Upload failed: SYNC-002 - Storage quota exceeded for user-123", "service": "sync-engine", "error_code": "SYNC-002"},
  {"timestamp": "2024-01-15T10:01:09Z", "level": "ERROR", "message": "Max retries exceeded for video_recording.mp4. Marking as failed.", "service": "sync-engine", "error_code": "SYNC-002"},
  {"timestamp": "2024-01-15T10:01:10Z", "level": "INFO", "message": "Sync completed with errors: 11/12 files uploaded", "service": "sync-engine"}
]
```

**보여줄 포인트:**
1. 먼저 AI **없이** 분석 → 차트(레벨 분포), 에러 4건, 슬로우 1건, SYNC-002 자동 조회
2. 그 다음 **AI 토글 ON** → "Storage quota exceeded" 근본 원인 가설이 자연어로 나옴
3. "쿼리를 짤 줄 몰라도 로그를 이해할 수 있다"

---

## 시나리오 3: 문의 분석 → 응답 초안 생성 (4분)

**스토리:** "분석 결과를 바탕으로 고객에게 보낼 답변까지 자동 생성한다"

**Inquiry Analysis** 페이지에서:

```
Our webhook endpoint at https://api.company.com/events stopped receiving notifications after we renewed our SSL certificate yesterday. We're getting API-002 errors in our logs. This is breaking our automated pipeline.
```

**보여줄 포인트:**
1. AI 토글 ON으로 분석 → `API` 카테고리, 체크리스트, 팔로업 질문
2. 관련 KB 문서 자동 매칭 (API-002: Webhook Delivery Failed, Webhooks 기능 문서)
3. **"Generate Response Draft"** 클릭 → 고객 답변 초안 생성
4. "80%의 문의를 여기서 바로 처리할 수 있다"

---

## 마무리 (1분)

**Knowledge Search** 페이지에서 자유 검색:
- `"delta sync"` → 기능 문서 즉시 조회
- `"SSO login failure"` → 런북 조회

**클로징 멘트 제안:**

> "기존에 2주 걸리던 온보딩 기간 동안 머릿속에 넣어야 했던 도메인 지식이, 이 도구 안에 들어있습니다. 신규 TSE도 첫 날부터 고객 문의를 처리할 수 있습니다."

---

## 부록: 주요 기능 원리 설명

### 즉시 분류 (SYNC / HIGH) — 어떻게 동작하는가?

두 단계로 나뉩니다: **카테고리 분류**와 **심각도 판단**.

**카테고리 분류 — 키워드 매칭**

고객 문의 텍스트를 소문자로 변환한 뒤, 카테고리별 키워드 목록과 대조해서 가장 많이 일치하는 카테고리를 선택합니다.

데모 이메일 예시:
```
"Files not syncing" → "syncing" 매칭 → SYNC +1
"SYNC-002"         → "sync-0"  매칭 → SYNC +1
→ SYNC가 2점으로 최고 → 카테고리 = SYNC
```

**심각도 판단 — 위에서 아래로 우선순위 매칭**

CRITICAL → HIGH → MEDIUM → LOW 순서로 검사하고, 처음 일치하는 레벨을 반환합니다.

데모 이메일 예시:
```
"blocking our entire team's work" → "blocking" 매칭 → HIGH
(CRITICAL 키워드에는 해당 없으므로 HIGH에서 확정)
```

**전체 흐름:**
```
고객 문의 텍스트
     │
     ├─→ 카테고리 키워드 매칭 (각 카테고리별 점수 → 최고점 선택)
     ├─→ 심각도 키워드 매칭 (CRITICAL→HIGH→MEDIUM→LOW 순서 스캔)
     ├─→ 에러코드 정규식 추출 ("SYNC-002" 감지)
     ├─→ KB 벡터 검색 (ChromaDB 코사인 유사도 → 관련 문서 5건)
     └─→ 신뢰도 계산 (카테고리 +0.3, KB 결과 +0.3, 에러코드 +0.1)
```

`--ai` 모드를 켜면 이 키워드 매칭 대신 Claude가 직접 분류합니다.
키워드 분류는 API 없이도 동작하는 fallback이자, 비용이 0인 기본 모드입니다.

---

### Event Level Distribution — 무엇을 보여주는가?

로그에서 파싱된 각 이벤트의 **로그 레벨별 건수**를 차트로 시각화합니다.

데모 로그 기준:

| Level | Count | 의미 |
|---|---|---|
| INFO | 5 | 정상 동작 기록 |
| WARN | 3 | 주의가 필요한 상황 |
| ERROR | 4 | 실패/오류 발생 |

로그를 전부 읽지 않아도 **한눈에 "에러가 얼마나 많은지"** 파악할 수 있습니다.
1만 줄 로그를 받아도 이 차트 하나로 에러 비율을 바로 확인 가능합니다.

---

### Knowledge Search — 어떻게 활용하는가?

TSE가 고객 문의를 처리하다가 **특정 정보를 빠르게 찾고 싶을 때** 사용합니다.

| 상황 | 검색어 | 찾아지는 것 |
|---|---|---|
| 고객이 에러코드를 알려줌 | `SYNC-002` | 원인, 해결 방법 |
| 기능 설정 방법을 물어봄 | `delta sync` | 기능 문서, 활성화 방법 |
| 장애 대응 절차가 필요함 | `data loss` | 런북 (즉시 조치 사항) |
| SSO 관련 문의가 왔는데 모름 | `SSO login failure` | 트러블슈팅 가이드 + 런북 |

**기존 방식:** Wiki 열고 → 키워드로 검색 → 여러 문서 돌아다니며 찾기 → 5-10분
**Knowledge Search:** 자연어로 검색 → 관련도 순으로 바로 나옴 → 10초

핵심은 **시맨틱 검색**입니다. 정확한 키워드가 아니어도 됩니다:
```
"파일이 안 올라감"  →  "SYNC-002: Upload Failed" 매칭됨
"느려요"          →  "Slow Sync Performance" 매칭됨
```

카테고리 필터로 범위를 좁힐 수 있습니다:
- **error_code** — 에러코드만 / **runbook** — 대응 절차만 / **faq** — FAQ만 / **troubleshooting** — 트러블슈팅만

> "신규 TSE가 모르는 것이 있으면 여기서 바로 검색하면 된다. 선배한테 물어보지 않아도 된다."

---

## 데모 체크리스트

| 준비 사항 | 확인 |
|---|---|
| `.env`에 `ANTHROPIC_API_KEY` 설정됨 | |
| `PYTHONPATH=$(pwd) streamlit run src/ui/app.py` 실행 | |
| 위 3개 시나리오 텍스트 미리 복사해둘 곳 준비 (메모장 등) | |
| AI 토글 OFF → ON 전환 비교를 보여줄 것 | |
