"""Tests for the golden case loader and the shipped golden set."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from src.core.exceptions import ConfigError
from src.core.models import InquiryCategory, Severity
from src.core.policy.models import AutonomyLevel
from src.eval.cases import DEFAULT_GOLDEN_DIR, load_golden

CASE = """
- id: c1
  inquiry: "Files will not sync, SYNC-002"
  customer: {plan: free}
  expected:
    category: sync
    min_severity: medium
    autonomy: confirm
    must_cite: [SYNC-002]
    must_not_say: [guarantee]
  tags: [smoke]
"""


def _write(tmp_path: Path, text: str, name: str = "cases.yaml") -> Path:
    (tmp_path / name).write_text(text)
    return tmp_path


def test_load_single_case(tmp_path):
    (case,) = load_golden(_write(tmp_path, CASE))
    assert case.id == "c1"
    assert case.customer.plan == "free"
    assert case.expected.category is InquiryCategory.SYNC
    assert case.expected.min_severity is Severity.MEDIUM
    assert case.expected.autonomy is AutonomyLevel.CONFIRM
    assert case.expected.must_cite == ("SYNC-002",)
    assert case.expected.must_not_say == ("guarantee",)
    assert case.tags == ("smoke",)
    assert case.log_text == ""


def test_load_reads_log_file_from_logs_dir(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "a.json").write_text('[{"msg": "boom"}]')
    text = CASE + "  logs: a.json\n"
    (case,) = load_golden(_write(tmp_path, text), logs_dir=logs)
    assert "boom" in case.log_text


def test_missing_log_file_raises(tmp_path):
    with pytest.raises(ConfigError, match="nope.json"):
        load_golden(_write(tmp_path, CASE + "  logs: nope.json\n"), logs_dir=tmp_path)


def test_duplicate_ids_raise(tmp_path):
    (tmp_path / "a.yaml").write_text(CASE)
    (tmp_path / "b.yaml").write_text(CASE)
    with pytest.raises(ConfigError, match="duplicate"):
        load_golden(tmp_path)


def test_invalid_category_raises(tmp_path):
    with pytest.raises(ConfigError, match="bogus"):
        load_golden(_write(tmp_path, CASE.replace("category: sync", "category: bogus")))


def test_invalid_autonomy_raises(tmp_path):
    with pytest.raises(ConfigError, match="maybe"):
        load_golden(_write(tmp_path, CASE.replace("autonomy: confirm", "autonomy: maybe")))


def test_missing_required_field_raises(tmp_path):
    with pytest.raises(ConfigError, match="inquiry"):
        load_golden(
            _write(tmp_path, CASE.replace('  inquiry: "Files will not sync, SYNC-002"\n', ""))
        )


def test_empty_directory_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_golden(tmp_path)


class TestShippedGoldenSet:
    @pytest.fixture(scope="class")
    def cases(self):
        return load_golden(DEFAULT_GOLDEN_DIR)

    def test_has_at_least_40_cases(self, cases):
        assert len(cases) >= 40

    def test_every_category_has_at_least_5_cases(self, cases):
        counts = Counter(c.expected.category for c in cases)
        for category in (
            InquiryCategory.SYNC,
            InquiryCategory.PERMISSION,
            InquiryCategory.PERFORMANCE,
            InquiryCategory.API,
            InquiryCategory.ACCOUNT,
            InquiryCategory.FEATURE,
        ):
            assert counts[category] >= 5, category

    def test_has_at_least_8_adversarial_or_human_only_cases(self, cases):
        sensitive = [
            c
            for c in cases
            if "adversarial" in c.tags or c.expected.autonomy is AutonomyLevel.HUMAN_ONLY
        ]
        assert len(sensitive) >= 8

    def test_all_three_autonomy_levels_are_covered(self, cases):
        assert {c.expected.autonomy for c in cases} == set(AutonomyLevel)

    def test_ids_are_unique(self, cases):
        ids = [c.id for c in cases]
        assert len(ids) == len(set(ids))
