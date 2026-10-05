# Design Document - Support Buddy

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      User Interface                      │
│              Streamlit UI  /  CLI  /  API                │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                    API Layer (FastAPI)                    │
│  POST /analyze    POST /logs    POST /draft-response     │
│  POST /knowledge  GET /search   GET /health              │
└───┬──────────────┬──────────────┬───────────────────────┘
    │              │              │
    ▼              ▼              ▼
┌────────┐  ┌───────────┐  ┌──────────────┐
│Analyzer│  │Log Parser │  │  Responder   │
│        │  │& Insights │  │(Draft Writer)│
└───┬────┘  └─────┬─────┘  └──────┬───────┘
    │             │               │
    └──────┬──────┴───────────────┘
           │
    ┌──────▼──────┐
    │  AI Engine  │        ┌──────────────────┐
    │ (Claude API │◄──────►│ Knowledge Engine  │
    │  + Tools)   │        │ (ChromaDB + RAG)  │
    └─────────────┘        └────────┬─────────┘
                                    │
                           ┌────────▼─────────┐
                           │  Knowledge Store  │
                           │  Markdown / JSON  │
                           │  + Vector Embeddings│
                           └──────────────────┘

External Integrations (Phase 3):
  ├── Linear API  ──► ticket read/write
  ├── GitHub API  ──► issue/PR reference
  └── Email IMAP  ──► inquiry ingestion
```

## 2. Core Components

### 2.1 Knowledge Engine (`src/core/knowledge/`)

**Purpose:** Ingest, embed, store, and retrieve domain knowledge.

```
knowledge/
├── __init__.py
├── engine.py          # KnowledgeEngine: main orchestrator
├── embedder.py        # Document → vector embedding
├── store.py           # ChromaDB wrapper
├── loader.py          # Markdown/JSON file loader
└── models.py          # Data models (KnowledgeDoc, SearchResult)
```

**Flow:**
```
Markdown/JSON files → Loader → Chunking → Embedder → ChromaDB
                                                         │
User query ─────────────────── Embedder → Search ────────┘
                                              │
                                     Ranked results with metadata
```

**Key decisions:**
- **ChromaDB** for MVP: embedded (no separate server), simple API, good enough for <10k docs
- **Chunking strategy:** Split by heading (H2/H3) for Markdown; keep JSON objects intact
- **Embedding model:** Use Anthropic's built-in or a local model (sentence-transformers) to avoid API cost on embeddings
- **Metadata:** Each chunk stores `source_file`, `category`, `title`, `last_updated`

### 2.2 Analyzer (`src/core/analyzer/`)

**Purpose:** Classify inquiries, generate checklists, analyze logs.

```
analyzer/
├── __init__.py
├── inquiry.py         # InquiryAnalyzer: classify & generate checklist
├── log_parser.py      # Parse various log formats
├── log_analyzer.py    # AI-powered log insight generation
└── models.py          # InquiryResult, LogInsight, Checklist
```

**Inquiry Analysis Flow:**
```
Customer message
    │
    ▼
┌─────────────────┐     ┌──────────────┐
│ Classify category│────►│ Search KB    │
│ & severity       │     │ for relevant │
└────────┬────────┘     │ articles     │
         │              └──────┬───────┘
         ▼                     │
┌─────────────────┐           │
│ Generate         │◄──────────┘
│ - Checklist      │
│ - Follow-up Qs   │
│ - Initial assess  │
└─────────────────┘
```

**Log Analysis Flow:**
```
Raw logs (text/JSON/CSV)
    │
    ▼
┌──────────────┐
│ Format detect │
│ & parse       │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌─────────────┐
│ Extract       │────►│ AI Analysis │
│ - timestamps  │     │ via Claude  │
│ - errors      │     │ (summarize, │
│ - slow ops    │     │  find root  │
│ - patterns    │     │  cause)     │
└──────────────┘     └──────┬──────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Natural lang  │
                    │ summary +     │
                    │ visualization │
                    │ data          │
                    └───────────────┘
```

### 2.3 Responder (`src/core/responder/`)

**Purpose:** Generate customer-facing response drafts.

```
responder/
├── __init__.py
├── drafter.py         # ResponseDrafter: generate response
├── templates.py       # Response templates by category
└── models.py          # DraftResponse, Citation
```

**Key behavior:**
- Every claim in the response must cite a knowledge base source
- Confidence is a **verification score computed by the Trust Layer** (see §7), not the LLM's self-reported number. The LLM's own `confidence` is kept only as a diagnostic signal.
- If verification fails or the autonomy policy says so (see §8), the draft is routed to human review
- Tone: professional, empathetic, solution-focused

### 2.4 AI Engine (`src/core/ai/`)

**Purpose:** Centralized Claude API interaction with tool use.

```
ai/
├── __init__.py
├── client.py          # AnthropicClient wrapper
├── tools.py           # Tool definitions for Claude (search_kb, get_error_code, etc.)
└── prompts.py         # System prompts for each use case
```

**Claude Tool Use design:**
- `search_knowledge_base(query, category?)` → search ChromaDB
- `get_error_code_info(code)` → lookup error code details
- `get_troubleshooting_guide(topic)` → retrieve specific runbook
- `classify_inquiry(text)` → return category + severity

This lets Claude autonomously decide when to search the knowledge base during analysis.

## 3. Data Models

```python
@dataclass
class KnowledgeDoc:
    id: str
    title: str
    content: str
    category: str          # faq, troubleshooting, error_code, runbook, feature
    source_file: str
    metadata: dict
    last_updated: datetime

@dataclass
class InquiryResult:
    category: str          # sync, permission, performance, api, account, feature
    severity: str          # low, medium, high, critical
    summary: str
    checklist: list[str]
    follow_up_questions: list[str]
    relevant_articles: list[SearchResult]
    confidence: float

@dataclass
class LogInsight:
    summary: str           # Natural language summary
    errors: list[LogEvent]
    slow_operations: list[LogEvent]
    anomalies: list[str]
    timeline: list[LogEvent]  # For visualization
    root_cause_hypothesis: str

@dataclass
class DraftResponse:
    body: str
    citations: list[Citation]
    confidence: float
    needs_escalation: bool
    suggested_internal_note: str
```

## 4. API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/analyze` | Analyze a customer inquiry |
| `POST` | `/api/v1/logs/analyze` | Parse and analyze logs |
| `POST` | `/api/v1/draft-response` | Generate a response draft |
| `POST` | `/api/v1/knowledge/ingest` | Ingest new knowledge documents |
| `GET`  | `/api/v1/knowledge/search` | Search knowledge base |
| `GET`  | `/api/v1/health` | Health check |

## 5. Tech Stack Rationale

| Choice | Why | Alternatives Considered |
|---|---|---|
| **Python 3.11+** | Best AI/ML ecosystem, Anthropic SDK native | TypeScript (good but weaker ML libs) |
| **FastAPI** | Async, auto-docs, type-safe, fast | Flask (simpler but no async), Django (too heavy) |
| **ChromaDB** | Embedded, no infra, good for MVP scale | Qdrant (better at scale, but needs server), Pinecone (SaaS cost) |
| **Claude API** | Long context for docs, tool use for KB search, high quality reasoning | GPT-4 (comparable but less controllable tool use) |
| **Streamlit** | Fastest path to interactive UI with charts | Gradio (similar), React (better but slower to build) |
| **pytest** | De facto Python testing standard | unittest (verbose) |

## 6. Phase 1 MVP Scope

The MVP proves the core value: **"paste a customer inquiry → get actionable guidance"**

### What's IN:
1. Knowledge ingestion from Markdown files (CloudSync virtual data)
2. Vector search via ChromaDB
3. Claude-powered inquiry analysis with tool use
4. Checklist + follow-up question generation
5. Basic log parsing (JSON format)
6. CLI interface
7. Unit + integration tests

### What's OUT (later phases):
- Web UI, Linear/GitHub integration, email parsing
- Log visualization (charts)
- Response drafting
- Feedback loop

### MVP Validation Criteria:
- [ ] Given 10 sample inquiries from CloudSync scenarios, the tool provides relevant checklists for 8+
- [ ] Knowledge search returns relevant articles in top-3 results for 80%+ of queries
- [ ] JSON log analysis correctly identifies errors and slow operations
- [ ] All core modules have 80%+ test coverage

> Phase 1-3 are implemented (Streamlit UI, email parser, Linear/GitHub clients, response drafter). Sections 7-14 below describe the Phase 5 direction ("Trustworthy Automation"), informed by interviews with practicing support/operations engineers.

---

## 7. Design Principles for Phase 5 (from practitioner interviews)

| # | Principle | Source insight | Consequence in this design |
|---|---|---|---|
| P1 | **Probabilistic + deterministic, always paired** | "AI knows what pleases people, not what is true." | Every AI output passes an independent rule-based check (Trust Layer, §8) before it can be acted on |
| P2 | **Prepare before the human arrives** | AI finishes first-pass analysis before the on-call engineer logs in | Briefing pipeline (§10) |
| P3 | **Judge with system context, not per item** | Redrive decisions must consider load and other incidents | Context-aware decisions (§13) |
| P4 | **Make the human/AI boundary explicit** | Liability: who is responsible when AI errs? | Autonomy policy: Auto / Confirm / Human-only (§9) |
| P5 | **Generate → critique → verify** | Multi-agent review chain with an accuracy agent | Review chain (§11) |
| P6 | **Multiply people, don't replace them** | AI frees engineers for more work; escalation paths unchanged | TSE always owns send/escalate; "multiplier" metrics (§12) |
| P7 | **Model-agnostic** | Teams experiment with several models and context sizes | Model registry via config, eval-based comparison (§12) |

## 8. Trust Layer (`src/core/trust/`)

**Purpose:** Independent, deterministic verification of AI output. It never asks an LLM whether the LLM was right.

```
trust/
├── __init__.py
├── verifier.py        # Verifier: run all checks, return VerificationReport
├── checks.py          # Individual deterministic checks (pure functions)
├── rules.py           # Rule data: severity floors, plan gates, commitment/PII patterns
├── kb_index.py        # KnowledgeIndex: doc ids and error codes that exist in the KB
└── models.py          # Check, VerificationReport
```

**Checks (each is a pure function, `(draft, analysis, kb, customer) -> Check`):**

| Check | Rule | Failure effect |
|---|---|---|
| `citations_exist` | Every cited article ID/title exists in the KB | block Auto |
| `citations_retrieved` | Cited articles were actually returned by retrieval for this inquiry | block Auto |
| `error_codes_valid` | Every `XXXX-NNN` code in the draft exists in `error_codes.md` | block Auto |
| `plan_entitlement` | Plan-gated features named in the customer's question **or** our draft are available on the customer's plan (`plan_matrix.md`). Found by the golden set: checking the draft alone let "Can we use SSO on Pro?" through | force Confirm |
| `no_commitments` | No refund, SLA, credit, or time promises (pattern list in `rules.py`) | force Human-only |
| `severity_floor` | Rule-based minimum severity (e.g. enterprise + "all users affected" → ≥ HIGH) overrides a lower LLM severity | raise severity |
| `pii_leak` | Draft contains no addresses/tokens/keys from the log input | block Auto |
| `process_state` | For multi-step flows (e.g. migration, SSO setup) the claimed step matches the step recorded in state | force Confirm |

**Output:** `VerificationReport(checks, passed, score)` where `score = passed_weight / total_weight`. This replaces LLM self-reported confidence in routing decisions.

**Rule:** the Trust Layer has no dependency on `core/ai/`. This is enforced by a unit test that imports the module with the Anthropic SDK blocked.

## 9. Autonomy Policy (`src/core/policy/`)

**Purpose:** Make "where AI acts alone vs. where a human must be involved" an explicit, reviewable artifact.

```
policy/
├── engine.py          # PolicyEngine.route(analysis, report, customer) -> Decision
├── models.py          # AutonomyLevel, Decision(level, reasons)
└── policy.yaml        # Human-editable rules (ships in data/)
```

| Level | Meaning | Example |
|---|---|---|
| `AUTO` | Draft may be sent without TSE action (initially: off by default, simulated in eval and shown as "would auto-send") | FAQ + all checks passed + non-enterprise |
| `CONFIRM` | TSE reviews and one-click approves | Standard troubleshooting, plan entitlement warnings |
| `HUMAN_ONLY` | AI prepares a briefing only; no customer-facing draft is offered | Security incidents, legal/compliance, refunds, data-loss reports |

**Routing is deterministic:** first matching rule wins, evaluated from the most restrictive level down. Every `Decision` carries human-readable `reasons`, shown in the UI ("Why Confirm? → Enterprise customer; severity HIGH").

**Safety default:** any exception, missing field, or unknown category routes to `HUMAN_ONLY`.

## 10. Briefing Pipeline & Overnight Queue (`src/core/briefing/`)

**Purpose:** By the time a TSE opens a ticket, first-pass analysis is already done.

```
New inquiry (email / Linear webhook / folder drop)
    │
    ▼
Ingest ─► Parse ─► Classify ─► Log analysis ─► KB search ─► Draft
                                                              │
                                              Trust Layer ◄───┘
                                                   │
                                           Policy decision
                                                   │
                                                   ▼
                                        Briefing (stored, status=READY)
```

- `Briefing` = summary, hypotheses (ranked), evidence (log lines, KB citations), verification report, autonomy decision, draft (unless HUMAN_ONLY).
- **Sufficiency verdict:** deterministic rule. `SUFFICIENT` if root-cause hypothesis cites ≥1 log evidence line and ≥1 KB article and verification score ≥ threshold; otherwise `INSUFFICIENT`, and the UI leads with raw logs (fallback to the classic workflow).
- Storage: SQLite (`briefings` table, path from `BRIEFING_DB_PATH`); the queue is the **Overnight Queue**, sorted by effective severity (after trust-layer floors) then age.
- **Sufficiency rule (implemented):** a briefing is `SUFFICIENT` only if the draft has a KB citation, technical categories (sync, performance, api, permission) have log evidence, and the verification score is ≥ 0.80. Otherwise the reasons say what is missing (e.g. "ask the customer for logs").
- **Fail-safe:** a pipeline or log-analysis failure never drops the ticket. It becomes a visible human-only briefing with effective severity HIGH.
- Human-only briefings carry no customer-facing draft.
- TSE approval records `edit_ratio` (0.0 = sent as drafted, 1.0 = fully rewritten).
- Trigger modes: manual (`POST /api/v1/briefings`), folder drop (`process_inbox`: `.eml` plus optional `.log` sidecar; implemented), IMAP poll (later, reusing `integrations/email`).

## 11. Review Chain (`src/core/review/`)

**Purpose:** Replace single-shot drafting with generate → critique → revise → verify.

```
Draft v1
   │
   ├─► Critic: customer empathy / tone
   ├─► Critic: technical accuracy (vs. KB + logs)
   └─► Critic: security & compliance
           │  (run in parallel, structured JSON findings)
           ▼
   Reviser ─► Draft v2
           │
           ▼
   Accuracy agent: lists every factual claim in v2 and marks each
   SUPPORTED / UNSUPPORTED against retrieved KB + log evidence
           │
           ▼
   Trust Layer (deterministic) ─► Policy decision
```

- 3 critics + 1 accuracy agent (the original interview example used 30+5; the principle matters, not the count).
- `UNSUPPORTED` claims are removed or flagged; the count is shown as "Hallucinations caught: N".
- The accuracy agent is **not** the final gate; the deterministic Trust Layer is.
- Cost control: Haiku for critics, Sonnet for reviser/accuracy by default (configurable).

## 12. Evaluation Harness & Model Registry (`src/eval/`, `src/config.py`)

**Purpose:** Make every quality claim measurable; allow model swaps without code changes.

```
eval/
├── golden/            # YAML cases: inquiry, optional logs, customer, expected_*
├── runner.py          # Run pipeline per case per model config
├── metrics.py         # Pure metric functions
└── report.py          # Markdown + JSON report, model comparison table
```

**Golden case schema (YAML):**
```yaml
id: sync-002-enterprise
inquiry: "..."
customer: {plan: enterprise}
logs: sync_error.json            # optional
expected:
  category: sync
  min_severity: high
  must_cite: [error_codes#SYNC-002]
  autonomy: confirm              # expected routing
  must_not_say: ["refund", "guarantee"]
```

**Metrics:**

| Metric | Definition |
|---|---|
| Category accuracy | predicted == expected |
| Severity under-triage rate | predicted < expected min (the dangerous direction) |
| Citation validity | % drafts where `citations_exist` and `citations_retrieved` pass |
| Routing agreement | policy decision == expected autonomy |
| **Auto-resolvable rate** | % cases that reach `AUTO` or `CONFIRM` with all checks passed. **This is the only definition of "automation rate" used in docs or on the resume.** |
| Unsafe-pass rate | cases expected `HUMAN_ONLY` that were routed lower (target: 0) |
| Cost / latency | tokens and wall time per case |

**Model registry:** `MODELS` in config maps roles (`classify`, `draft`, `critic`, `accuracy`) to model IDs via env/YAML. The runner accepts multiple configs (e.g. Haiku / Sonnet / Opus, 200K vs 1M context) and outputs a side-by-side table. No module may hardcode a model ID.

**Golden set size:** 40 cases at start (≥ 5 per category, ≥ 8 expected HUMAN_ONLY or adversarial). Reported numbers always state the set size.

**Running it:** `python -m src.cli eval --pipeline local` is free and deterministic (keyword classifier + template draft) and is the committed baseline in `docs/eval/`. `--pipeline claude --names balanced,premium` calls the paid API after a cost confirmation. A Claude component that silently falls back to local output is recorded as an error, never as a Claude result.

**What "auto-resolvable" does and does not mean:** it measures that a draft passed every deterministic check and was routed to Auto or Confirm. It does **not** measure that the answer is correct. Answer quality needs human or LLM-judge grading and is not claimed.

**Multiplier metrics (live usage):** draft approval rate, edit distance between draft and sent text, time-to-first-response, per TSE (opt-in, stored locally).

## 13. Log Intake, PII Redaction & Context-Aware Decisions

### 13.1 Log intake (`src/core/analyzer/`)
- Multi-file upload and drag-and-drop; email attachments flow in automatically via the Briefing pipeline.
- **Correlation:** merge events from multiple files by `request_id`/`trace_id`, fall back to timestamp windows.
- **PII redaction (`redactor.py`)** runs *before* any text is sent to a model: emails, IPs, bearer tokens, API keys, phone numbers → stable placeholders (`<EMAIL_1>`). A reverse map stays local so the TSE view can un-redact. Redaction is deterministic (regex + checksum rules) and unit-tested.

### 13.2 Context-aware decisions (`src/core/context/`)
- `SystemContext` = active incidents / `known_issues.md` matches, recent releases (`data/virtual_company/release_notes.md`), current ticket volume per category.
- Used for: batch replies (N tickets sharing a root cause → one decision), and suppressing "troubleshoot your setup" advice during a known incident.
- **Pattern detection:** cluster recent inquiries by category + error code + embedding similarity; surface "deflection candidates" (clusters ≥ N with no KB coverage) and draft KB article stubs.
- **Change-driven forecast:** given a release note, predict likely inquiry topics and prepare macros before tickets arrive.

## 14. Data Model & API Additions

```python
class AutonomyLevel(str, Enum):
    AUTO = "auto"
    CONFIRM = "confirm"
    HUMAN_ONLY = "human_only"

@dataclass
class Check:
    name: str
    passed: bool
    weight: float
    detail: str

@dataclass
class VerificationReport:
    checks: list[Check]
    passed: bool
    score: float            # weighted pass ratio, deterministic

@dataclass
class Decision:
    level: AutonomyLevel
    reasons: list[str]

@dataclass
class Briefing:
    id: str
    inquiry: InquiryResult
    log_insight: LogInsight | None
    draft: DraftResponse | None     # None when HUMAN_ONLY
    report: VerificationReport
    decision: Decision
    sufficient: bool
    created_at: datetime
```

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/briefings` | Create a briefing (runs full pipeline) |
| `GET` | `/api/v1/briefings` | List the Overnight Queue |
| `GET` | `/api/v1/briefings/{id}` | One briefing with evidence and decision reasons |
| `POST` | `/api/v1/briefings/{id}/approve` | TSE approves/edits the draft (records edit distance) |
| `POST` | `/api/v1/eval/run` | Run golden set against a model config |
| `GET` | `/api/v1/policy` | Current autonomy policy (read-only) |

## 15. UI Design System ("Quiet Apple")

The current UI ("Intelligent Ledger": Manrope/Inter, blue accent, gray container stack) reads as generic AI-dashboard styling. Phase 5 replaces it with a restrained, Apple-inspired system.

**Principles**
1. **Content first, chrome last.** One primary task per screen; fewer borders, boxes, and badges. Whitespace and type size create hierarchy, not cards.
2. **One accent color.** Neutral grayscale plus a single blue (`#0071e3`, system blue). Semantic color (green / orange / red) appears only for state: verification passed / warning / failed and autonomy level.
3. **System typography.** `-apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", Inter, sans-serif` (no web-font import for Mac/iOS; Inter as fallback). Large light-weight titles (34-40px / 600), 15-17px body, tight tracking on titles (-0.02em).
4. **Soft depth.** 12-16px radii, no hard borders: 1px `rgba(0,0,0,0.06)` hairlines and very soft shadows. Translucent sidebar (`backdrop-filter: blur(20px)`).
5. **Quiet motion.** 150-250ms ease-out fades; no bouncing or gradients; skeleton shimmer only while loading.
6. **Progressive disclosure.** Summary first; evidence, raw logs, and verification details live in expandable sections.
7. **Dark mode** follows `prefers-color-scheme`.

**Tokens**

| Token | Light | Dark |
|---|---|---|
| `--bg` | `#ffffff` | `#000000` |
| `--bg-secondary` | `#f5f5f7` | `#1c1c1e` |
| `--text` | `#1d1d1f` | `#f5f5f7` |
| `--text-secondary` | `#6e6e73` | `#a1a1a6` |
| `--accent` | `#0071e3` | `#0a84ff` |
| `--ok` / `--warn` / `--bad` | `#34c759` / `#ff9f0a` / `#ff3b30` | same |
| `--hairline` | `rgba(0,0,0,.06)` | `rgba(255,255,255,.10)` |

**Signature components**
- **Autonomy pill:** `Auto` / `Confirm` / `Human-only` segmented capsule with the "why" on hover/tap.
- **Verification strip:** a single horizontal row of check dots (filled = passed); click expands the list. Never a wall of badges.
- **Briefing card:** title, one-sentence summary, verdict line ("Briefing ready" / "Needs your eyes"), then collapsed evidence.
- **Draft diff:** v1 → v2 inline diff with "N unsupported claims removed".
- **Eval table:** minimal table with sparkline-free numbers, best value per row in accent color.

**Information architecture (replaces the current five-page sidebar)**
1. **Queue** (default, Overnight Queue)
2. **Briefing** (detail)
3. **Analyze** (manual: paste inquiry, email, or logs: one input box, auto-detected type)
4. **Knowledge** (search + browse merged)
5. **Insights** (patterns, eval results, multiplier metrics)

**Hosting decision (Option C):** the production UI is a static React app (Cloudflare Pages: no sleep, no cost) talking to the FastAPI backend (Cloud Run, scale to zero, wakes on request). The public demo serves **pre-computed briefings** and never needs an API key; "run it yourself" is the only path that calls Claude and sits behind per-IP and global daily limits plus a console spend limit. Streamlit remains until the React app replaces it.

**Implementation notes (Streamlit era):** Streamlit stays for the MVP; styling is centralized in `src/ui/styles.py` (tokens as CSS variables). Streamlit chrome (header, footer, default fonts) is overridden; icons use inline SVG (SF-Symbols-like, 1.5px stroke) instead of Material Symbols. React migration remains a later option, and the tokens are portable.

## 16. Phase 5 Delivery Order

1. Trust Layer + tests (pure Python, no UI) **(done)**
2. Autonomy Policy + `policy.yaml` **(done)**
3. Eval harness + 40-case golden set + model registry **(done; Claude-pipeline numbers pending an API run)**
4. Briefing pipeline, queue store, folder-drop trigger and API **(done; Overnight Queue UI is part of step 5)**
5. UI restyle to the Quiet Apple system (can start in parallel with 4)
6. Review chain
7. Log correlation + PII redaction
8. Pattern detection, change-driven forecast, batch decisions

All steps follow TDD (RED → GREEN → REFACTOR) per `CLAUDE.md`.
