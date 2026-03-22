# Support Buddy

AI-powered internal support tool that helps Technical Support Engineers handle customer inquiries faster and more accurately.

## Project Context

- **Owner:** Ella (Technical Support Engineer)
- **Goal:** Reduce TSE onboarding from 2 weeks to days; enable 80%+ of customer inquiries to be answered through this tool
- **Domain:** Customer support for a SaaS product (developed with a virtual company scenario for testing)

## Tech Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI
- **AI:** Claude API (Anthropic SDK) with tool use
- **Knowledge Store:** ChromaDB (vector embeddings) + structured Markdown/JSON docs
- **Frontend:** Streamlit (MVP) → React (later)
- **Integrations:** Linear API, GitHub API, Email (IMAP)
- **Testing:** pytest, pytest-asyncio

## Development Workflow

1. **Superpowers workflow:** Brainstorming → Git Worktree → Plan → Subagent Dev (TDD) → Code Review → Branch Finish
2. **agentic-dev-pipeline:** Used for verification (lint → test → security → triangular review)
3. **TDD enforced:** RED → GREEN → REFACTOR cycle for all features

## Directory Structure

```
support-buddy/
├── CLAUDE.md              # This file
├── convention.md          # Code conventions
├── design-doc.md          # Architecture & design
├── requirement.md         # Requirements spec
├── src/
│   ├── core/              # Core business logic
│   │   ├── knowledge/     # Knowledge base engine (embedding, retrieval)
│   │   ├── analyzer/      # Inquiry analysis & log parsing
│   │   └── responder/     # Response generation
│   ├── integrations/      # External service connectors
│   │   ├── linear/
│   │   ├── github/
│   │   └── email/
│   ├── api/               # FastAPI routes
│   └── ui/                # Streamlit UI
├── data/
│   ├── knowledge/         # Domain knowledge documents
│   ├── sample_logs/       # Sample logs for testing
│   └── virtual_company/   # Virtual company scenario data
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── pyproject.toml
└── .env.example
```

## Key Rules

- Never commit secrets (.env, API keys, credentials) — they are in .gitignore
- All new features require tests FIRST (TDD)
- Use type hints for all function signatures
- Domain knowledge files go in `data/knowledge/` as Markdown or JSON
- Log analysis must handle arbitrary log formats gracefully
- AI responses must always cite their source from the knowledge base
