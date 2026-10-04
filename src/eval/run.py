"""Orchestrate eval runs and write reports."""

from __future__ import annotations

import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from src.config import DATA_DIR, KNOWLEDGE_DIR
from src.core.ai.registry import ModelRegistry, load_registries
from src.core.exceptions import ConfigError
from src.core.knowledge.engine import KnowledgeEngine
from src.core.knowledge.loader import KnowledgeLoader
from src.core.policy.loader import load_policy
from src.core.trust.kb_index import KnowledgeIndex, build_kb_index
from src.eval.cases import DEFAULT_GOLDEN_DIR, load_golden
from src.eval.metrics import compute_metrics
from src.eval.pipeline import ClaudePipeline, LocalPipeline, Pipeline
from src.eval.report import ConfigRun, render_json, render_markdown
from src.eval.runner import EvalRunner

DEFAULT_POLICY_PATH = DATA_DIR / "policy" / "policy.yaml"
DEFAULT_MODEL_CONFIGS = DATA_DIR / "eval" / "model_configs.yaml"


@contextmanager
def _knowledge() -> Iterator[tuple[KnowledgeEngine, KnowledgeIndex]]:
    """Isolated knowledge engine plus the existence index for the trust layer."""
    with tempfile.TemporaryDirectory() as tmp:
        engine = KnowledgeEngine(persist_dir=tmp)
        engine.ingest_directory(KNOWLEDGE_DIR)
        index = build_kb_index(KnowledgeLoader().load_directory(KNOWLEDGE_DIR))
        yield engine, index


def _run(
    name: str,
    models: str,
    pipeline: Pipeline,
    index: KnowledgeIndex,
    golden_dir: Path,
    policy_path: Path,
) -> ConfigRun:
    cases = load_golden(golden_dir)
    results = EvalRunner(pipeline, index, load_policy(policy_path)).run(cases)
    return ConfigRun(name, models, results, compute_metrics(results))


def run_local_eval(
    golden_dir: Path = DEFAULT_GOLDEN_DIR, policy_path: Path = DEFAULT_POLICY_PATH
) -> list[ConfigRun]:
    """Free baseline: keyword classifier and template drafts, no API calls."""
    with _knowledge() as (engine, index):
        run = _run(
            "local-baseline",
            "keyword + template",
            LocalPipeline(engine),
            index,
            golden_dir,
            policy_path,
        )
    return [run]


def select_registries(path: Path | None, names: Sequence[str] | None) -> list[ModelRegistry]:
    available = load_registries(path or DEFAULT_MODEL_CONFIGS)
    if not names:
        return list(available.values())
    unknown = [n for n in names if n not in available]
    if unknown:
        raise ConfigError(
            f"unknown model config(s): {', '.join(unknown)}; available: {', '.join(available)}"
        )
    return [available[n] for n in names]


def run_claude_eval(
    registries: Sequence[ModelRegistry],
    api_key: str,
    golden_dir: Path = DEFAULT_GOLDEN_DIR,
    policy_path: Path = DEFAULT_POLICY_PATH,
) -> list[ConfigRun]:
    """Run the golden set once per model configuration. Calls the paid API."""
    runs: list[ConfigRun] = []
    with _knowledge() as (engine, index):
        for registry in registries:
            models = f"{registry.classify} / {registry.draft}"
            pipeline = ClaudePipeline(engine, registry, api_key=api_key)
            runs.append(_run(registry.name, models, pipeline, index, golden_dir, policy_path))
    return runs


def write_reports(runs: list[ConfigRun], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    measured_on = date.today().isoformat()
    md_path = out_dir / "eval-report.md"
    json_path = out_dir / "eval-report.json"
    md_path.write_text(render_markdown(runs, measured_on), encoding="utf-8")
    json_path.write_text(render_json(runs, measured_on), encoding="utf-8")
    return md_path, json_path
