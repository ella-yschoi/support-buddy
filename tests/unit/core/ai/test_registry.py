"""Tests for the model registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.config import DATA_DIR, MODEL_FAST, MODEL_STANDARD
from src.core.ai.registry import ModelRegistry, default_registry, load_registries
from src.core.exceptions import ConfigError

YAML = """
configs:
  cheap:
    classify: model-a
    draft: model-a
    critic: model-a
    accuracy: model-a
  mixed:
    classify: model-a
    draft: model-b
    critic: model-a
    accuracy: model-b
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "models.yaml"
    path.write_text(text)
    return path


def test_default_registry_uses_config_tiers(monkeypatch):
    for role in ("CLASSIFY", "DRAFT", "CRITIC", "ACCURACY"):
        monkeypatch.delenv(f"ANTHROPIC_MODEL_{role}", raising=False)
    reg = default_registry()
    assert reg.classify == MODEL_FAST
    assert reg.critic == MODEL_FAST
    assert reg.draft == MODEL_STANDARD
    assert reg.accuracy == MODEL_STANDARD


def test_default_registry_role_env_overrides(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL_DRAFT", "custom-model")
    assert default_registry().draft == "custom-model"


def test_default_standard_model_is_not_retired():
    assert "sonnet-4-2025" not in MODEL_STANDARD


def test_load_registries_returns_named_configs(tmp_path):
    regs = load_registries(_write(tmp_path, YAML))
    assert set(regs) == {"cheap", "mixed"}
    assert regs["mixed"] == ModelRegistry(
        name="mixed", classify="model-a", draft="model-b", critic="model-a", accuracy="model-b"
    )


def test_load_registries_missing_role_raises(tmp_path):
    bad = "configs:\n  x:\n    classify: a\n    draft: a\n    critic: a\n"
    with pytest.raises(ConfigError, match="accuracy"):
        load_registries(_write(tmp_path, bad))


def test_load_registries_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_registries(tmp_path / "missing.yaml")


def test_load_registries_empty_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_registries(_write(tmp_path, "configs: {}\n"))


def test_shipped_model_configs_load():
    regs = load_registries(DATA_DIR / "eval" / "model_configs.yaml")
    assert len(regs) >= 3
