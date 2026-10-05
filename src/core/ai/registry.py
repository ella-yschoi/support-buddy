"""Model registry: which model serves which role. No module hardcodes a model ID."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from src.config import MODEL_FAST, MODEL_STANDARD
from src.core.exceptions import ConfigError

ROLES = ("classify", "draft", "critic", "accuracy")


@dataclass(frozen=True)
class ModelRegistry:
    name: str
    classify: str
    draft: str
    critic: str
    accuracy: str


def default_registry() -> ModelRegistry:
    """Fast tier for classify/critic, standard tier for draft/accuracy; env can override a role."""

    def pick(role: str, fallback: str) -> str:
        return os.getenv(f"ANTHROPIC_MODEL_{role.upper()}", fallback)

    return ModelRegistry(
        name="default",
        classify=pick("classify", MODEL_FAST),
        draft=pick("draft", MODEL_STANDARD),
        critic=pick("critic", MODEL_FAST),
        accuracy=pick("accuracy", MODEL_STANDARD),
    )


def load_registries(path: Path) -> dict[str, ModelRegistry]:
    """Load named model configurations (used by the eval harness to compare models)."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"cannot read model configs {path}: {exc}") from exc

    configs = raw.get("configs") if isinstance(raw, dict) else None
    if not isinstance(configs, dict) or not configs:
        raise ConfigError(f"{path} must define a non-empty 'configs' mapping")

    registries: dict[str, ModelRegistry] = {}
    for name, roles in configs.items():
        if not isinstance(roles, dict):
            raise ConfigError(f"config '{name}' must be a mapping of roles to model ids")
        missing = [r for r in ROLES if r not in roles]
        if missing:
            raise ConfigError(f"config '{name}' is missing roles: {', '.join(missing)}")
        registries[str(name)] = ModelRegistry(name=str(name), **{r: str(roles[r]) for r in ROLES})
    return registries
