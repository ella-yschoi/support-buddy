# Requirements Specification

## 1. Overview

**Support Buddy** is an AI-powered internal tool that ingests company domain knowledge and assists Technical Support Engineers (TSEs) in resolving customer inquiries quickly and accurately.

**Success Metric:** 80%+ of customer inquiries can be answered through this tool.

---

## 2. Virtual Company Scenario

For development and testing, we use a fictional SaaS company:

### CloudSync Inc.
- **Product:** CloudSync - a cloud-based file synchronization and team collaboration platform
- **Customers:** B2B SaaS companies, 50-5000 employees
- **Support channels:** Email, in-app chat, Linear tickets

### Common Inquiry Categories
| Category | Example | Frequency |
|---|---|---|
| Sync errors | "Files not syncing between devices" | 30% |
| Permission issues | "User can't access shared folder" | 20% |
| Performance | "Dashboard loading slowly" | 15% |
| API integration | "Webhook not firing on file upload" | 15% |
| Account & billing | "Can't add new team members" | 10% |
| Feature questions | "How do I set up auto-backup?" | 10% |

### Error Codes
- `SYNC-001` ~ `SYNC-010`: Sync engine errors
- `AUTH-001` ~ `AUTH-005`: Authentication/permission errors
- `PERF-001` ~ `PERF-005`: Performance-related errors
- `API-001` ~ `API-010`: API/webhook errors
- `ACCT-001` ~ `ACCT-005`: Account/billing errors

---

## 3. Functional Requirements

### FR-1: Domain Knowledge Ingestion
- **FR-1.1:** Ingest Markdown/JSON documents as knowledge sources
- **FR-1.2:** Generate vector embeddings for semantic search
- **FR-1.3:** Support incremental updates (add/modify/delete documents)
- **FR-1.4:** Categorize knowledge by type: FAQ, troubleshooting guide, error code reference, runbook, feature doc

### FR-2: Inquiry Analysis
- **FR-2.1:** Accept customer inquiry as natural language input
- **FR-2.2:** Classify inquiry into category and severity
- **FR-2.3:** Generate a checklist of things the TSE should verify/ask the customer
- **FR-2.4:** Retrieve relevant knowledge base articles with relevance scores
- **FR-2.5:** Suggest follow-up questions to narrow down the issue

### FR-3: Resolution Suggestion
- **FR-3.1:** Given inquiry + customer context (logs, config, environment), suggest a resolution
- **FR-3.2:** Cite specific knowledge base sources for each suggestion
- **FR-3.3:** Provide step-by-step resolution instructions
- **FR-3.4:** Flag when confidence is low and human escalation is recommended

### FR-4: Log Analysis
- **FR-4.1:** Accept log input in common formats (JSON, plain text, CSV)
- **FR-4.2:** Parse and extract key events, errors, timestamps
- **FR-4.3:** Identify anomalies (slow operations, error spikes, unusual patterns)
- **FR-4.4:** Generate natural language summary: "what happened and why"
- **FR-4.5:** Visualize timeline of events and error distribution

### FR-5: Integration
- **FR-5.1:** Connect to Linear to read/create/update tickets
- **FR-5.2:** Connect to GitHub to reference issues, PRs, and code
- **FR-5.3:** Accept email input (parse email content into structured inquiry)

### FR-6: Response Drafting
- **FR-6.1:** Generate a draft customer response based on analysis
- **FR-6.2:** Match tone and style guidelines (professional, empathetic, solution-focused)
- **FR-6.3:** Include relevant links to documentation

---

## 4. Non-Functional Requirements

### NFR-1: Performance
- Knowledge base search: < 2 seconds
- Inquiry analysis + suggestion: < 10 seconds
- Log parsing (up to 10,000 lines): < 30 seconds

### NFR-2: Security
- No customer PII stored in knowledge base
- API keys and credentials never committed to repository
- All external API calls use HTTPS

### NFR-3: Usability
- TSE should be able to use the tool with < 10 minutes of training
- Clear, actionable outputs (not vague suggestions)
- Confidence scores on all AI-generated suggestions

### NFR-4: Maintainability
- Knowledge base updateable without code changes
- Modular architecture: each component independently testable
- 80%+ test coverage on core modules

---

## 5. Implementation Phases

### Phase 1 - Foundation (MVP)
- [ ] Project setup (Python, FastAPI, ChromaDB)
- [ ] Knowledge ingestion pipeline (Markdown → embeddings)
- [ ] Basic RAG engine (query → retrieve → generate)
- [ ] CLI interface for "inquiry in → guidance out"
- [ ] Virtual company test data (CloudSync Inc.)

### Phase 2 - Core Intelligence
- [ ] Inquiry classifier (category + severity)
- [ ] Checklist generator
- [ ] Log parser (JSON, plain text)
- [ ] Log analysis with AI insights
- [ ] Response draft generator

### Phase 3 - Integration & UI
- [ ] Linear integration (read/write tickets)
- [ ] GitHub integration (reference issues/code)
- [ ] Email parser
- [ ] Streamlit web UI with log visualization

### Phase 4 - Optimization
- [ ] Feedback loop (TSE corrections improve knowledge)
- [ ] 80% auto-response rate measurement
- [ ] Onboarding simulation mode
- [ ] Performance tuning
