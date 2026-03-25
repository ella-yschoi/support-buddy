# Code Conventions

## Language & Style

- **Python 3.11+** with type hints on all public functions
- Follow [PEP 8](https://peps.python.org/pep-0008/) with line length 100
- Use `ruff` for linting and formatting
- Use `mypy` for type checking (strict mode)

## Naming

| Element | Convention | Example |
|---|---|---|
| Files & modules | snake_case | `log_parser.py` |
| Classes | PascalCase | `KnowledgeEngine` |
| Functions & methods | snake_case | `analyze_inquiry()` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| Private members | leading underscore | `_parse_log_entry()` |
| Type aliases | PascalCase | `LogEntry = dict[str, Any]` |

## Project Structure Rules

- One class per file when the class is substantial (>50 lines)
- Group related small utilities in a single module
- Each package (`core/`, `integrations/`, etc.) must have an `__init__.py` with public API exports
- Tests mirror the `src/` structure: `src/core/knowledge/engine.py` → `tests/unit/core/knowledge/test_engine.py`

## Imports

```python
# Standard library
import os
from pathlib import Path

# Third-party
from fastapi import FastAPI
import anthropic

# Local
from src.core.knowledge.engine import KnowledgeEngine
```

- Use absolute imports from project root
- Group imports: stdlib → third-party → local (separated by blank lines)
- No wildcard imports (`from x import *`)

## Error Handling

- Use custom exception classes in `src/core/exceptions.py`
- Never catch bare `Exception` unless re-raising
- Log errors with structured context (not just the message)

## Documentation

- Docstrings: Google style, required for public functions/classes
- In-code comments: only when "why" is not obvious from the code
- No auto-generated boilerplate docstrings

## Git & Commits

- **Branch naming:** `feature/<name>`, `fix/<name>`, `refactor/<name>`
- **Commit messages:** imperative mood, max 72 chars for subject line
  - Format: `<type>: <subject>` (e.g., `feat: add log parser for JSON format`)
  - Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`
- **Commit granularity:** 하나의 커밋은 하나의 논리적 단위로 구성한다
  - 모듈/컴포넌트 단위로 커밋을 분리 (e.g., knowledge engine, analyzer, log parser 각각 별도 커밋)
  - 각 커밋에는 해당 기능의 구현 코드 + 관련 테스트 + 관련 데이터를 함께 포함
  - 인프라/설정 변경(pyproject.toml, config, 공통 모델 등)은 기능 커밋과 분리하여 먼저 커밋
  - 하나의 커밋이 여러 독립적인 기능을 포함하지 않도록 한다
  - 커밋 body에 변경 사항을 bullet point로 요약
- **Co-Authored-By:** 커밋에 `Co-Authored-By` 줄을 추가하지 않는다
- **PR:** one logical change per PR, include test plan

## Testing

- **Framework:** pytest
- **TDD:** Write failing test → implement → refactor
- **Coverage target:** 80%+ for core modules
- **Naming:** `test_<what>_<condition>_<expected>` (e.g., `test_parse_log_empty_input_returns_empty_list`)
- **Fixtures:** shared fixtures in `tests/conftest.py`, module-specific in local `conftest.py`
- No mocking of core business logic; mock only external services

## Dependencies

- Managed via `pyproject.toml` (PEP 621)
- Pin major versions, allow minor updates: `anthropic>=0.40,<1.0`
- Dev dependencies in `[project.optional-dependencies]` under `dev` group
