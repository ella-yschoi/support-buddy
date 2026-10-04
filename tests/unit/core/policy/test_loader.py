"""Tests for loading policy.yaml."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.config import DATA_DIR
from src.core.exceptions import PolicyError
from src.core.models import InquiryCategory, Severity
from src.core.policy.loader import load_policy

VALID = """
version: 1
auto_send_enabled: false
human_only:
  keywords: [breach, refund]
  categories: [unknown]
  min_severity: critical
  min_score_below: 0.5
confirm:
  plans: [enterprise]
  min_severity: high
auto:
  categories: [feature]
  max_severity: medium
  min_score: 1.0
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "policy.yaml"
    path.write_text(text)
    return path


def test_load_valid_policy(tmp_path):
    policy = load_policy(_write(tmp_path, VALID))
    assert policy.human_only_keywords == ("breach", "refund")
    assert policy.human_only_categories == (InquiryCategory.UNKNOWN,)
    assert policy.human_only_min_severity is Severity.CRITICAL
    assert policy.confirm_plans == ("enterprise",)
    assert policy.auto_categories == (InquiryCategory.FEATURE,)
    assert policy.auto_max_severity is Severity.MEDIUM
    assert policy.auto_min_score == 1.0
    assert policy.auto_send_enabled is False


def test_missing_file_raises_policy_error(tmp_path):
    with pytest.raises(PolicyError):
        load_policy(tmp_path / "nope.yaml")


def test_invalid_yaml_raises_policy_error(tmp_path):
    with pytest.raises(PolicyError):
        load_policy(_write(tmp_path, "human_only: [unclosed"))


def test_unknown_category_raises_policy_error(tmp_path):
    bad = VALID.replace("categories: [feature]", "categories: [bogus]")
    with pytest.raises(PolicyError, match="bogus"):
        load_policy(_write(tmp_path, bad))


def test_unknown_severity_raises_policy_error(tmp_path):
    bad = VALID.replace("max_severity: medium", "max_severity: extreme")
    with pytest.raises(PolicyError, match="extreme"):
        load_policy(_write(tmp_path, bad))


def test_missing_section_raises_policy_error(tmp_path):
    with pytest.raises(PolicyError, match="auto"):
        load_policy(_write(tmp_path, "version: 1\nhuman_only: {}\nconfirm: {}\n"))


def test_unsupported_version_raises_policy_error(tmp_path):
    with pytest.raises(PolicyError, match="version"):
        load_policy(_write(tmp_path, VALID.replace("version: 1", "version: 99")))


def test_shipped_policy_is_valid_and_never_auto_sends():
    policy = load_policy(DATA_DIR / "policy" / "policy.yaml")
    assert policy.auto_send_enabled is False
    assert policy.human_only_keywords
