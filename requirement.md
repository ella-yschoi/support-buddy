# Requirements Specification

## 1. Overview

**Support Buddy** is an AI-powered internal tool that ingests company domain knowledge and assists Technical Support Engineers (TSEs) in resolving customer inquiries quickly and accurately.

**Success Metric:** 80%+ of customer inquiries can be answered through this tool.

**Measurement rule:** "answered through this tool" is defined as the **auto-resolvable rate** (FR-10.3): the share of golden-set cases that reach `AUTO` or `CONFIRM` with every deterministic check passed. No figure is quoted in docs, README, or resume without the golden-set size and the date it was measured.

**Phase 5 philosophy:** the tool *multiplies* TSEs, it does not replace them. TSEs always own sending and escalation. AI output is never acted on without an independent, deterministic check.

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

### FR-7: Trust Layer (deterministic verification)
- **FR-7.1:** Every AI-generated draft passes a rule-based verifier before it can be approved or routed (see design-doc §8)
- **FR-7.2:** Verifier checks: citations exist and were retrieved, error codes valid, plan entitlement, no commitments (refund/SLA/dates), PII leak, process-state match
- **FR-7.3:** Severity floor rules can raise, never lower, the LLM-assigned severity
- **FR-7.4:** The verification score replaces the LLM's self-reported confidence in all routing decisions
- **FR-7.5:** The Trust Layer must not depend on any LLM call or the Anthropic SDK (enforced by test)

### FR-8: Autonomy Policy
- **FR-8.1:** Each inquiry is routed to exactly one level: `AUTO`, `CONFIRM`, or `HUMAN_ONLY`
- **FR-8.2:** Rules live in an editable `policy.yaml`; routing is deterministic, first match wins, most restrictive first
- **FR-8.3:** Every decision exposes human-readable reasons in the UI
- **FR-8.4:** Security, legal/compliance, refund, and data-loss inquiries are always `HUMAN_ONLY`
- **FR-8.5:** Errors or unknown categories fail safe to `HUMAN_ONLY`
- **FR-8.6:** `AUTO` is simulation-only in the MVP (shown as "would auto-send"); nothing is sent to customers automatically

### FR-9: Briefings & Overnight Queue
- **FR-9.1:** New inquiries (email, folder drop, manual) are processed into a stored briefing without TSE action
- **FR-9.2:** A briefing contains summary, ranked hypotheses, evidence (log lines + KB citations), verification report, autonomy decision, and draft (omitted for `HUMAN_ONLY`)
- **FR-9.3:** Each briefing gets a deterministic sufficiency verdict; `INSUFFICIENT` briefings lead with raw logs
- **FR-9.4:** Queue is sorted by severity, then age, and shows verdict and autonomy level at a glance
- **FR-9.5:** TSE can approve/edit a draft; the edit distance is recorded

### FR-10: Evaluation & Model Registry
- **FR-10.1:** A golden set (≥ 40 cases, ≥ 8 adversarial or expected-`HUMAN_ONLY`) is stored in YAML under `src/eval/golden/`
- **FR-10.2:** The runner executes the full pipeline per case and per model configuration
- **FR-10.3:** Reported metrics: category accuracy, severity under-triage rate, citation validity, routing agreement, **auto-resolvable rate**, unsafe-pass rate (target 0), cost, latency
- **FR-10.4:** Model IDs per role (`classify`, `draft`, `critic`, `accuracy`) come from config; no hardcoded model IDs in modules
- **FR-10.5:** A report compares multiple model configs side by side (e.g. Haiku / Sonnet / Opus, different context sizes)

### FR-11: Review Chain
- **FR-11.1:** Drafts go through ≥ 3 parallel critics (empathy/tone, technical accuracy, security/compliance)
- **FR-11.2:** A reviser produces v2; an accuracy agent marks each factual claim SUPPORTED/UNSUPPORTED against retrieved evidence
- **FR-11.3:** Unsupported claims are removed or flagged; the count is displayed
- **FR-11.4:** The chain is optional (toggle) so cost and latency can be traded off
- **FR-11.5:** The chain's output always goes through FR-7 afterwards

### FR-12: Log Intake & Privacy
- **FR-12.1:** Multiple log files can be uploaded at once; attachments from emails are ingested automatically
- **FR-12.2:** Events are correlated across files by request/trace ID, falling back to time windows
- **FR-12.3:** PII (emails, IPs, tokens, API keys, phone numbers) is redacted deterministically before any text is sent to a model; a local reverse map allows the TSE to view originals
- **FR-12.4:** Log analysis keeps handling arbitrary formats gracefully (existing rule)

### FR-13: System Context & Patterns
- **FR-13.1:** Decisions consider system context: active incidents / known issues, recent releases, current volume per category
- **FR-13.2:** Inquiries sharing a root cause are grouped; a single batch decision is offered
- **FR-13.3:** Recurring clusters without KB coverage are surfaced as deflection candidates, with a KB article stub draft
- **FR-13.4:** Given a release note, the tool predicts likely inquiry topics and prepares draft macros

### FR-14: Feedback & Multiplier Metrics
- **FR-14.1:** Record draft approval rate and draft-to-sent edit distance per TSE (local, opt-in)
- **FR-14.2:** Insights page shows time-to-first-response and approval trends

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
- Verification score and autonomy reasons on all AI-generated suggestions (not LLM self-reported confidence)

### NFR-3b: UI Design ("Quiet Apple", see design-doc §15)
- One primary task per screen; progressive disclosure for evidence and logs
- Single accent color; semantic colors only for state
- System font stack, soft radii, hairline borders, translucent sidebar
- Light and dark mode via `prefers-color-scheme`
- No gradient/glow/emoji decoration; motion limited to short fades
- Text contrast meets WCAG AA

### NFR-5: Trust & Safety
- Deterministic checks are independent of LLM output
- Fail-safe default: any pipeline error routes to `HUMAN_ONLY`
- Nothing is sent to customers automatically in the MVP
- Customer logs are redacted before leaving the machine

### NFR-6: Model Agnosticism
- Swapping a model requires a config change only
- Eval harness must run unchanged against any configured model

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
- [ ] 80% auto-response rate measurement (superseded by Phase 5 eval harness, FR-10)
- [ ] Onboarding simulation mode
- [ ] Performance tuning

### Phase 5 - Trustworthy Automation
Ordered; each step TDD. See design-doc §16.
- [x] 5.1 Trust Layer (FR-7)
- [x] 5.2 Autonomy Policy (FR-8)
- [x] 5.3 Eval harness, 40-case golden set, model registry (FR-10)
- [x] 5.4 Briefing pipeline, store, inbox trigger and API (FR-9; Overnight Queue UI follows in 5.5)
- [ ] 5.5 UI restyle to Quiet Apple, new information architecture (NFR-3b). Started: `web/` has Queue and Briefing detail with demo-data fallback; Analyze, Knowledge and Insights screens remain
- [ ] 5.6 Review chain (FR-11)
- [ ] 5.7 Log correlation + PII redaction (FR-12)
- [ ] 5.8 System context, patterns, forecast, batch decisions (FR-13)
- [ ] 5.9 Multiplier metrics (FR-14)

**Phase 5 exit criteria**
- [x] Unsafe-pass rate = 0 on the golden set (local baseline, n = 40, 2026-10-04)
- [x] Auto-resolvable rate measured and recorded with set size and date (local baseline: 60.0% of 40 cases, 77.4% of in-scope cases, 2026-10-04; Claude configs pending)
- [ ] Model comparison report committed for ≥ 3 configs
- [x] Trust Layer has no LLM/SDK dependency (test passes)
- [ ] README and resume figures match the committed eval report
