"""Load and validate policy.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.core.exceptions import PolicyError
from src.core.models import InquiryCategory, Severity
from src.core.policy.models import Policy

SUPPORTED_VERSION = 1


def load_policy(path: Path) -> Policy:
    """Parse a policy file. Raises PolicyError on any problem; never returns a partial policy."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PolicyError(f"cannot read policy {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise PolicyError(f"policy {path} must be a mapping")
    if raw.get("version") != SUPPORTED_VERSION:
        raise PolicyError(f"unsupported policy version: {raw.get('version')!r}")

    human = _section(raw, "human_only")
    confirm = _section(raw, "confirm")
    auto = _section(raw, "auto")

    return Policy(
        human_only_keywords=tuple(k.lower() for k in _str_list(human, "keywords")),
        human_only_categories=_categories(_str_list(human, "categories")),
        human_only_min_severity=_severity(human.get("min_severity", "critical")),
        human_only_score_below=_number(human, "min_score_below", 0.6),
        confirm_plans=tuple(p.lower() for p in _str_list(confirm, "plans")),
        confirm_min_severity=_severity(confirm.get("min_severity", "high")),
        auto_categories=_categories(_str_list(auto, "categories")),
        auto_max_severity=_severity(auto.get("max_severity", "medium")),
        auto_min_score=_number(auto, "min_score", 1.0),
        auto_send_enabled=bool(raw.get("auto_send_enabled", False)),
    )


def _str_list(section: dict[str, Any], key: str) -> list[str]:
    value = section.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise PolicyError(f"policy field '{key}' must be a list")
    return [str(v) for v in value]


def _number(section: dict[str, Any], key: str, default: float) -> float:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PolicyError(f"policy field '{key}' must be a number, got {value!r}")
    return float(value)


def _section(raw: dict[str, Any], name: str) -> dict[str, Any]:
    section = raw.get(name)
    if not isinstance(section, dict):
        raise PolicyError(f"policy section '{name}' is missing or not a mapping")
    return section


def _categories(values: list[str]) -> tuple[InquiryCategory, ...]:
    try:
        return tuple(InquiryCategory(v) for v in values)
    except ValueError as exc:
        raise PolicyError(f"unknown category in policy: {exc}") from exc


def _severity(value: str) -> Severity:
    try:
        return Severity(value)
    except ValueError as exc:
        raise PolicyError(f"unknown severity in policy: {value!r}") from exc
