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
- Confidence score (0-1) on overall response
- If confidence < 0.6, explicitly flag for human review
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
