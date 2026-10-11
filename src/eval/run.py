"""Orchestrate eval runs and write reports."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any

from src.config import DATA_DIR, KNOWLEDGE_DIR
from src.core.ai.registry import ModelRegistry, load_registries
from src.core.exceptions import ConfigError
from src.core.knowledge.engine import KnowledgeEngine
from src.core.knowledge.loader import KnowledgeLoader
from src.core.models import InquiryCategory, Severity
from src.core.policy.loader import load_policy
from src.core.policy.models import AutonomyLevel
from src.core.trust.kb_index import KnowledgeIndex, build_kb_index
from src.eval.cases import DEFAULT_GOLDEN_DIR, Expected, load_golden
from src.eval.metrics import compute_metrics
from src.eval.models import CaseResult, Usage
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


def write_reports(
    runs: list[ConfigRun], out_dir: Path, measured_on: str | None = None
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    if measured_on is None:
        measured_on = date.today().isoformat()
    md_path = out_dir / "eval-report.md"
    json_path = out_dir / "eval-report.json"
    md_path.write_text(render_markdown(runs, measured_on), encoding="utf-8")
    json_path.write_text(render_json(runs, measured_on), encoding="utf-8")
    return md_path, json_path


def _case_result_from_dict(d: dict[str, Any]) -> CaseResult:
    exp = d["expected"]
    return CaseResult(
        case_id=d["case_id"],
        expected=Expected(
            category=InquiryCategory(exp["category"]),
            min_severity=Severity(exp["min_severity"]),
            autonomy=AutonomyLevel(exp["autonomy"]),
            must_cite=tuple(exp.get("must_cite", [])),
            must_not_say=tuple(exp.get("must_not_say", [])),
        ),
        predicted_category=InquiryCategory(d["predicted_category"]),
        model_severity=Severity(d["model_severity"]),
        effective_severity=Severity(d["effective_severity"]),
        autonomy=AutonomyLevel(d["autonomy"]),
        verification_passed=d["verification_passed"],
        verification_score=d["verification_score"],
        failed_checks=tuple(d.get("failed_checks", [])),
        cited_titles=tuple(d.get("cited_titles", [])),
        citations_valid=d["citations_valid"],
        has_draft=d["has_draft"],
        draft_body=d.get("draft_body", ""),
        usage=Usage(**d["usage"]),
        error=d.get("error"),
    )


def recompute_reports_from_json(
    json_path: Path,
    out_dir: Path,
    golden_dir: Path = DEFAULT_GOLDEN_DIR,
) -> tuple[Path, Path]:
    """Reload golden expected labels from YAML and pipeline outputs from *json_path*.

    Recomputes metrics (applying any fixes to the metric functions) and writes
    updated reports to *out_dir*. Does not call the API.
    """
    raw = json.loads(json_path.read_text(encoding="utf-8"))
    measured_on: str = raw["measured_on"]

    # Build a lookup of expected values from the current golden YAML so that
    # updated labels and must_not_say phrases are picked up without a full re-run.
    golden_by_id = {c.id: c.expected for c in load_golden(golden_dir)}

    runs: list[ConfigRun] = []
    for config in raw["configs"]:
        results: list[CaseResult] = []
        for c in config["cases"]:
            result = _case_result_from_dict(c)
            # Overlay the current golden expected values (labels may have changed).
            if result.case_id in golden_by_id:
                result = CaseResult(
                    case_id=result.case_id,
                    expected=golden_by_id[result.case_id],
                    predicted_category=result.predicted_category,
                    model_severity=result.model_severity,
                    effective_severity=result.effective_severity,
                    autonomy=result.autonomy,
                    verification_passed=result.verification_passed,
                    verification_score=result.verification_score,
                    failed_checks=result.failed_checks,
                    cited_titles=result.cited_titles,
                    citations_valid=result.citations_valid,
                    has_draft=result.has_draft,
                    draft_body=result.draft_body,
                    usage=result.usage,
                    error=result.error,
                )
            results.append(result)
        runs.append(ConfigRun(config["name"], config["models"], results, compute_metrics(results)))

    return write_reports(runs, out_dir, measured_on)
