# Handoff: Support Buddy

Written 2026-10-06 for a new Claude Code session on another machine. Read this first, then `CLAUDE.md`, `convention.md`, `design-doc.md`, `requirement.md`. This file holds what those do not: the decisions, the reasons, the current state, and what to do next.

No secrets are in this file. See "Setting up a new machine" for what you must supply.

---

## 1. What this is and who it is for

**Support Buddy** is an internal AI tool that helps Technical Support Engineers (TSEs) handle customer tickets faster and more safely. The owner is **Ella** (`ella-yschoi`), a TSE, who is also using this project as a portfolio piece while job hunting after a gap of about a year. The goal is that she can speak credibly with practising support engineers about how AI is used in real support work.

Core idea, in one line: **prepare the investigation before the engineer opens the ticket, check it with rules that do not trust the AI, and leave the final judgement and sending to the human.**

It is not a replacement for Zendesk, Jira, Linear or Intercom. It is a sidecar to them.

A non-technical explainer in Korean exists as a private Claude artifact (open it from the same claude.ai account): https://claude.ai/artifact/WgYio6fAM3ndP5CcpZijDX. It is the best short answer to "what is this and when does it help".

## 2. How to work with Ella (preferences and rules)

- **Reply in Korean** in chat. Repo documents and code are in English.
- **Honesty about numbers is non-negotiable.** She is putting these figures on a resume. Never state a metric that was not measured, and say what a metric means and does not mean. Her old resume claimed "automating 80% of repetitive support tasks" with no measurement; that claim is being retired. See section 9.
- **Confirm before outward-facing actions**: pushing, opening or merging PRs, writing to external services, spending money. She has authorised pushes and PRs for the web and adapter work case by case. Writing to a real ticket tool beyond the sandbox, deploys and API spend need a fresh yes.
- **Commits:** no `Co-Authored-By` line (stated in `convention.md` and in her memory). Do not add "Generated with Claude Code" to PR bodies either. Imperative subject, max 72 chars, `type: subject`, bullets in the body. One logical unit per commit; infra and config changes first and separate.
- **Branches:** `feature/<name>`, `fix/<name>`, `refactor/<name>`. Never commit straight to `main`.
- **TDD is mandatory** (`CLAUDE.md`): write the failing test, see it fail, implement, refactor. New code must pass `ruff` and `mypy --strict`.
- **Do not run `ruff format` on whole existing directories.** It reformats files you did not change. Format only files you created.
- She approved bypass-style permissions but wants to be asked for anything that truly needs her approval. A few commands were denied by the harness (e.g. starting an ad-hoc local HTTP server); if one is denied, change approach instead of retrying.
- Design taste: she dislikes generic "AI-generated" looking UI. Final direction is **black, Vercel-style** (see section 5).

## 3. Product principles (from practitioner interviews)

These came from two interviews with working support/ops engineers and drive the whole design:

1. **Probabilistic plus deterministic, always paired.** The AI proposes; a separate rule-based layer verifies. Never act on AI output on trust.
2. **Prepare before the human arrives.** First-pass analysis exists when the engineer logs in (the 2 a.m. page scenario). If it is not enough, the engineer falls back to reading raw logs.
3. **Judge with system context, not per item.** (Planned: batch decisions, known incidents.)
4. **Make the human/AI boundary explicit:** Auto, Confirm, Human-only, written in an editable policy file.
5. **Generate, critique, verify** with a multi-agent review chain. (Planned, not built.)
6. **Multiply people, do not replace them.** The tool never sends anything to customers.
7. **Model-agnostic.** Model IDs come from config, not code.

## 4. Decisions made, with reasons

| Decision | Reason |
|---|---|
| Sidecar to the ticket tool, not a second inbox | A separate queue becomes a second inbox; state drifts, SLA and ownership live in the tracker. Tracker is source of truth for ticket state; Support Buddy is source of truth for briefings, verification, evidence, edit ratio. The web queue is a view that links back to the ticket. |
| Adapter order: **Linear, then Zendesk**; Jira and Intercom get an adapter plus contract tests against recorded fixtures only, documented as "not verified live" | Linear: client exists, easy sandbox, free. Zendesk: most relevant to TSE jobs and on her resume, has "internal note". Jira/Intercom: lower value per effort. Resume may claim only what was truly connected. |
| Hosting "Option C": static React on Cloudflare Pages plus FastAPI on Cloud Run | Streamlit Cloud sleeps and needs manual waking. Static hosting never sleeps; Cloud Run wakes on request. |
| Public demo serves **pre-computed briefings** and needs no API key | Cost and safety. Only "run it yourself" may call Claude, behind per-IP and global daily limits plus an Anthropic console spend limit. Real customer data must never be put on the public site. |
| Black Vercel-style UI, dark only, no light mode | Her request. One theme halves the design surface. |
| Logo: "Pair" (two overlapping rings, shared part filled) | A person and the assistant working together. Chosen from six options by Ella. Favicon switches black/white with the browser theme. |
| Local keyword pipeline is the live default; Claude is not yet wired into briefings | Needed cost caps and PII masking first. |
| Default Sonnet model moved from the retired `claude-sonnet-4-20250514` to `claude-sonnet-5-5` | The old ID is retired on the first-party API. |
| Polling by update cursor before webhooks | Webhooks need a public URL, which means deployment. |
| Reading from a ticket tool never writes; write-back (later) is internal note plus label only, never customer-visible, dry-run by default | Safety. |

## 5. Current state (as of 2026-10-06)

### Repository and PRs
- Repo: `https://github.com/ella-yschoi/support-buddy`
- `main` contains PR #1 (trust layer, policy, eval, briefings) and PR #3 (web UI). PR #2 was merged into the feature branch by mistake, then brought in by #3.
- **PR #4 is OPEN** (`feature/ticket-adapters` to `main`): ticket-source adapters, Linear intake, `watch`, seed/cleanup, origin links in the web UI, docs, README fixes, removal of `demo.md`. All commits are pushed. **Ella needs to review and merge it.** Until then, work from branch `feature/ticket-adapters`.
- Stale local branches on the old machine (`feature/trust-layer`, `feature/web-ui`) are merged and can be ignored or deleted.

### What is built
- **Trust layer** (`src/core/trust/`): 8 pure, deterministic checks (`citations_exist`, `citations_retrieved`, `error_codes_valid`, `plan_entitlement`, `no_commitments`, `severity_floor`, `pii_leak`, `process_state`), a weighted score, fail-closed on any check error. Must not import any LLM code (a test enforces this).
- **Autonomy policy** (`src/core/policy/`, `data/policy/policy.yaml`): routes to `auto` / `confirm` / `human_only`, most restrictive first, with human-readable reasons. `auto_send_enabled: false`: Auto is simulated only; nothing is ever sent.
- **Briefings** (`src/core/briefing/`): builder, SQLite queue store, sufficiency rule (KB citation, log evidence for technical categories, score at least 0.80), fail-safe briefing on any pipeline error, `process_inbox` for `.eml` drops, `ingest_tickets`, `run_watch`. Briefings carry an `origin` (source, id, key, url).
- **Eval harness** (`src/eval/`): 40-case golden set in `src/eval/golden/*.yaml`, metrics, side-by-side model comparison, Markdown and JSON reports, `LocalPipeline` (keyword plus template, free) and `ClaudePipeline` (paid; treats silent fallback to local output as an error). Model registry in `src/core/ai/registry.py`, named configs in `data/eval/model_configs.yaml`.
- **Ticket sources** (`src/integrations/tickets/`): `Ticket` model, `TicketSource` protocol, `InMemoryTicketSource`, `LinearTicketSource`, `CursorStore`, `seed.py`. Shared contract tests in `tests/unit/integrations/tickets/contract.py`: every new adapter must subclass `TicketSourceContract`.
- **API** (`src/api/`): `POST/GET /api/v1/briefings`, `GET /api/v1/briefings/{id}`, `POST .../approve` (records edit ratio; 409 if already approved), `GET /api/v1/policy`, plus the older analyze/logs/draft/search endpoints.
- **Web** (`web/`, Vite + React + TypeScript, no UI library): Queue, Briefing detail, Analyze (paste a ticket), reply editor (edit, copy, mark as sent), demo-data fallback with a "Demo data" badge and read-only forms, ticket link ("Open SUP-5 in Linear"), logo, favicon, boot screen.
- **Legacy**: the original Streamlit UI (`src/ui/`) and a keep-alive GitHub Action (`.github/workflows/keep-alive.yml`) still exist. Decide whether to retire them once the web app is deployed.

### CLI (run with `uv run python -m src.cli ...`)
`analyze`, `logs`, `draft`, `search`, `ingest` (older), and new: `eval`, `demo-data`, `watch`, `seed-linear`, `cleanup-linear`.
Note: the `support-buddy` console script fails in git worktrees (`No module named 'src'`); use `python -m src.cli`.

### Tests
- Python: **469 passed** (`uv run pytest`; takes about 6 minutes because ChromaDB embeds documents).
- Web: **87 passed** (`cd web && npm test`), `tsc --noEmit` and `npm run build` clean.
- New code passes `ruff` and `mypy --strict`. The repo has about 89 **pre-existing** ruff errors in untouched files; leave them.

### Evaluation numbers (local baseline, 2026-10-04, 40 cases)
Pipeline measured: keyword classifier plus template drafts. **Claude has not been evaluated.**

| Metric | Value |
|---|---|
| Cases | 40 (6 categories with at least 5 each, 9 adversarial) |
| Sensitive cases that must go to a human | 9; **0 routed below Human-only** |
| Routing agreement | 100% (40/40) |
| Checks all passed and routed Auto or Confirm | 60.0% (77.4% of the 31 in-scope cases) |
| Routed Auto only | 7.5% |
| Category accuracy | 72.5% |
| Severity under-triage | 25.0% by the model, 17.5% after the trust layer's severity floors |
| Drafts passing every check | 80.0% (32/40) |

Read these carefully:
- "Auto-resolvable" means every check passed and the case went to Auto or Confirm. **It does not mean the answer was correct.**
- The 80.0% "drafts passing every check" is template drafts, not AI drafts, and its failures are checks doing their job. It coincides with the retired "80%" resume claim, so do **not** use it as a headline.
- The expected labels and the policy were written by the same person, so `0 of 9` shows the rules behave as designed, not independent validation.
- The golden set already caught one real bug: asking about SSO on Pro with a draft that never named SSO went to Auto. `plan_entitlement` now scans the customer's question too.

### External state (not in git)
- **Linear sandbox**: workspace "Support Buddy Sandbox", team key `SUP`. `SUP-1` to `SUP-4` are Linear's own onboarding issues. `SUP-5` to `SUP-7` are seeded test tickets (label `seed`, plan label `plan:pro`). 37 more seed tickets can be created with `seed-linear`. Free plan limit: 250 issues.
- **Local data on the old machine**: `briefing_data/briefings.db` holds briefings made from those three tickets. Not in git; recreate with `watch`.
- **Her `.env`** holds `LINEAR_API_KEY` (and possibly `ANTHROPIC_API_KEY`). Not in git.

## 6. Architecture in one picture

```
Ticket tool (Linear now; Zendesk next; Jira/Intercom adapter-only)
        |  TicketSource.fetch_updated(cursor)           [read-only]
        v
 ingest_tickets  -- skips closed, label filter, dedupe by id "<source>-<ticket id>"
        |
        v
 BriefingBuilder: classify -> logs -> KB search -> draft
        |                                     (local keyword/template today; Claude planned)
        v
 Trust layer (8 deterministic checks) -> Policy (Auto / Confirm / Human-only)
        |
        v
 BriefingStore (SQLite)  <--  FastAPI  <--  Web (Queue, detail, Analyze, reply editor)
                                                 |
                                   TSE reads, edits, sends from the ticket tool,
                                   marks "sent" -> edit ratio recorded
```

Key files: `src/core/trust/checks.py`, `rules.py`; `src/core/policy/engine.py`; `src/core/briefing/{builder,ingest,watch,store,inbox,factory}.py`; `src/eval/{cases,runner,metrics,report,run,demo,pipeline}.py`; `src/integrations/tickets/*`; `src/integrations/linear/client.py`; `src/api/{server,briefings,schemas}.py`; `web/src/{App,api,format}.ts(x)` and `web/src/components/*`.

## 7. What to do next (in order)

Each step is its own branch and PR. Before any step, merge PR #4.

**B. PII masking, then Claude briefings** (needs Ella's go-ahead on spend)
- First confirm Ella has set an **Anthropic console spend limit** and that `ANTHROPIC_API_KEY` is in `.env`.
- Build deterministic PII redaction (emails, IPs, tokens, API keys, phones) that runs **before** any text goes to a model, with a local reverse map (FR-12). Real ticket data must not reach Claude without it.
- Wire a Claude-backed `BriefingBuilder` (analyze, draft, log insight) using the model registry; keep the local builder as the free default.
- Add cost controls: per-IP and global daily limits for any public "run it yourself" path, hard monthly cap, and show spend.
- Run the Claude eval (`eval --pipeline claude --names balanced,premium`; costs roughly $4 to $20, an estimate from assumed token counts at about $0.11 per briefing) and commit the report to `docs/eval/`. **This produces the first real numbers for the resume.**

**C. Write back to Linear** (internal comment plus label only, dry-run by default)
- Never change state or assignee; mark the comment as AI-generated; avoid webhook loops from our own comments.
- Fetch the actually sent reply from the ticket and compute the edit ratio automatically (removes the manual "Mark as sent").

**D. Auth and deploy**
- Login (the data is sensitive), Cloudflare Pages for `web/`, Cloud Run for the API, secrets in the host's secret store, webhooks instead of polling. The public site stays demo-data only.

**E. Zendesk adapter, then a two-week shadow pilot**
- Subclass `TicketSourceContract`. Zendesk has a 14-day free trial (sandbox is an Enterprise feature), so start the trial only when the adapter code is ready. Jira and Intercom: adapter plus contract tests with recorded fixtures only.
- Pilot: one or two TSEs, shadow mode (no writes), measure time to first useful action, edit ratio, escalation accuracy, unsafe passes (must stay 0).

**Smaller follow-ups**
- Doc ids in citations derive from the absolute file path, so regenerating `web/public/demo/briefings.json` in a different checkout location changes those ids (content identical). Make `KnowledgeLoader._make_id` use a repo-relative path.
- `npm audit` reports advisories in dev tooling (not in the production bundle). Clean up before deploy.
- Light mode and a real phone width were never visually verified (headless Chrome here renders dark only). Light mode was dropped by decision.
- Review chain (generate, critique, verify), log correlation across files, pattern detection and batch decisions (design-doc sections 11 to 13) are designed but unbuilt.
- Decide whether to retire Streamlit and the keep-alive workflow.
- A Notion or docs write-up of the design is optional; none exists.

## 8. Setting up a new machine

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/), Node 18+ (the web app pins Vite 5 and Vitest 2 because of Node 18), `gh` logged in as `ella-yschoi`.

```bash
git clone https://github.com/ella-yschoi/support-buddy.git && cd support-buddy
git checkout feature/ticket-adapters        # or main once PR #4 is merged
uv sync --extra dev
cp .env.example .env                        # then fill in keys; never commit .env
cd web && npm install && cd ..
```

`.env` variables: `ANTHROPIC_API_KEY` (optional until step B), `LINEAR_API_KEY` (a personal API key from the **sandbox** workspace), `BRIEFING_DB_PATH` (optional), `ANTHROPIC_MODEL_*` (optional overrides). Ella must create these herself; do not ask her to paste keys into chat.

```bash
uv run pytest -q -p no:warnings             # about 6 min the first time (downloads an ONNX embedding model)
(cd web && npm test && npm run build)

uv run uvicorn src.api.server:app --port 8000      # API
(cd web && npm run dev)                             # http://localhost:5173, proxies /api to :8000; works without the API in demo mode

uv run python -m src.cli eval --pipeline local --out docs/eval
uv run python -m src.cli demo-data                  # regenerate web/public/demo/briefings.json
uv run python -m src.cli seed-linear --team SUP --dry-run
uv run python -m src.cli watch --source linear --team SUP --label seed --once
```

First ChromaDB use prints harmless "Failed to send telemetry event" lines.

## 9. Resume and interview guidance (she may submit before step B)

Only claim what is true today. As of this handoff, true: reads tickets from Linear, rule-based verification, 40-case eval, 0 of 9 sensitive cases routed below human review. **Not** true yet: Zendesk connected, Claude-evaluated results, a real TSE pilot, always-on operation.

Bullet drafted for today (about 55 words):

> Built an AI support triage tool (Claude, FastAPI, React) that reads tickets from Linear and prepares a briefing with log evidence, knowledge-base citations, and a draft before an engineer opens the ticket. A rule-based verification layer and a 40-case eval suite route each case to auto, confirm, or human-only, with 0 of 9 sensitive cases routed below human review.

Also: remove "automating 80%", remove "contributing back to the team" unless true, keep "Hackathon-winning" only if true, use "Open Source" only if the repo is public, and update the project dates (work continued to October 2026). Add Linear to skills; do not list Zendesk, Jira or Intercom as connected integrations for this project.

Limits she should volunteer in interviews: the evaluated pipeline is the rule-based baseline, not Claude; she wrote both the labels and the policy; the metric is routing safety, not answer correctness; the live ticket path runs on demand, not as a deployed service.

After step B produces Claude numbers, replace the figures with the measured ones and consider extending to Zendesk once it is truly connected.

## 10. Gotchas learned the hard way

- **Retargeting PRs:** PR #2 was stacked on #1 and merged into the feature branch, not `main`, because GitHub did not retarget it. When stacking, retarget the child to `main` before merging the parent, or merge the child first.
- Vitest, Vite and `@types/node` are pinned for Node 18; newer majors need Node 20.
- macOS `sed -i ''` needs the empty string; large multi-line edits are safer with Python.
- `ruff format` on directories rewrites untouched files. Check `git status` after formatting.
- `InquiryResult` is a mutable dataclass; some tests assign `analysis.category` directly.
- The ChromaDB ephemeral client shares state inside one process, so tests and eval runs use a temporary persistent directory.
- Do not print or log API keys. Verify a key with a read-only call (for Linear, `LinearClient().get_teams()`) and print only the result.
- Pricing facts used (checked 2026-10-03 from official pages; re-check before relying on them): Claude Haiku 4.5 $1/$5, Sonnet 5.5 $2/$10, Opus 5.5 $4/$20 per million tokens (input/output). Linear free plan includes API and webhooks with a 250-issue cap. Zendesk Support Team $19 per agent per month annual or $25 monthly with a 14-day trial. Intercom developer workspaces are free (up to 20 users, no outbound email). Jira Free is 10 users (from third-party sources; official page not read).

## 11. Open questions for Ella

1. Is an Anthropic spend limit set, and is the key in `.env`? (Blocks step B.)
2. Is "Hackathon-winning" true, and is the repo public (for "Open Source")?
3. Should Streamlit and the keep-alive workflow be retired?
4. When to start the Zendesk 14-day trial (after the adapter exists)?
5. Has PR #4 been merged?
