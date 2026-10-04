"""Golden case schema and loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from src.config import SAMPLE_LOGS_DIR
from src.core.exceptions import ConfigError
from src.core.models import InquiryCategory, Severity
from src.core.policy.models import AutonomyLevel
from src.core.trust.models import Customer

DEFAULT_GOLDEN_DIR = Path(__file__).parent / "golden"


@dataclass(frozen=True)
class Expected:
    category: InquiryCategory
    min_severity: Severity
    autonomy: AutonomyLevel
    must_cite: tuple[str, ...] = ()
    must_not_say: tuple[str, ...] = ()


@dataclass(frozen=True)
class GoldenCase:
    id: str
    inquiry: str
    customer: Customer
    expected: Expected
    log_text: str = ""
    tags: tuple[str, ...] = ()


def load_golden(directory: Path, logs_dir: Path = SAMPLE_LOGS_DIR) -> list[GoldenCase]:
    """Load every *.yaml file in a directory. Raises ConfigError on any invalid case."""
    files = sorted(directory.glob("*.yaml"))
    if not files:
        raise ConfigError(f"no golden case files in {directory}")

    cases: list[GoldenCase] = []
    seen: set[str] = set()
    for file in files:
        try:
            raw = yaml.safe_load(file.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigError(f"cannot read {file}: {exc}") from exc
        if not isinstance(raw, list):
            raise ConfigError(f"{file} must contain a list of cases")
        for entry in raw:
            case = _parse_case(entry, logs_dir, file)
            if case.id in seen:
                raise ConfigError(f"duplicate golden case id: {case.id}")
            seen.add(case.id)
            cases.append(case)
    return cases


def _parse_case(entry: Any, logs_dir: Path, file: Path) -> GoldenCase:
    if not isinstance(entry, dict):
        raise ConfigError(f"{file}: each case must be a mapping")
    case_id = str(entry.get("id", "<no id>"))
    for key in ("id", "inquiry", "expected"):
        if key not in entry:
            raise ConfigError(f"{file}: case {case_id} is missing '{key}'")

    exp = entry["expected"]
    for key in ("category", "min_severity", "autonomy"):
        if key not in exp:
            raise ConfigError(f"{file}: case {case_id} expected.{key} is missing")

    try:
        expected = Expected(
            category=InquiryCategory(exp["category"]),
            min_severity=Severity(exp["min_severity"]),
            autonomy=AutonomyLevel(exp["autonomy"]),
            must_cite=tuple(str(s) for s in exp.get("must_cite", [])),
            must_not_say=tuple(str(s) for s in exp.get("must_not_say", [])),
        )
    except ValueError as exc:
        raise ConfigError(f"{file}: case {case_id}: {exc}") from exc

    log_text = ""
    if "logs" in entry:
        log_path = logs_dir / str(entry["logs"])
        try:
            log_text = log_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigError(f"{file}: case {case_id}: cannot read log {entry['logs']}") from exc

    customer = entry.get("customer", {})
    return GoldenCase(
        id=case_id,
        inquiry=str(entry["inquiry"]).strip(),
        customer=Customer(plan=str(customer.get("plan", "unknown")).lower()),
        expected=expected,
        log_text=log_text,
        tags=tuple(str(t) for t in entry.get("tags", [])),
    )
