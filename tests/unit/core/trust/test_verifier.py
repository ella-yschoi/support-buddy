"""Tests for the Verifier orchestrator."""

from __future__ import annotations

import pytest

from src.core.models import Severity
from src.core.trust import checks
from src.core.trust.models import Check, FailEffect
from src.core.trust.verifier import Verifier
from tests.unit.core.conftest import make_analysis, make_draft


def test_clean_draft_passes_with_full_score(make_input):
    report = Verifier().verify(make_input())
    assert report.passed
    assert report.score == pytest.approx(1.0)
    assert report.effects == frozenset()
    assert len(report.checks) == len(checks.ALL_CHECKS)


def test_score_is_weighted_pass_ratio(make_input):
    draft = make_draft(body="We guarantee a fix (SYNC-002).")  # no_commitments weight 3
    report = Verifier().verify(make_input(draft=draft))
    total = sum(c.weight for c in report.checks)
    assert report.score == pytest.approx((total - 3.0) / total)
    assert not report.passed
    assert FailEffect.FORCE_HUMAN_ONLY in report.effects


def test_effective_severity_raised_to_floor(make_input):
    inp = make_input(
        inquiry_text="All users cannot sync",
        analysis=make_analysis(severity=Severity.LOW),
        plan="enterprise",
    )
    report = Verifier().verify(inp)
    assert report.severity_floor is Severity.HIGH
    assert report.effective_severity is Severity.HIGH
    assert FailEffect.RAISE_SEVERITY in report.effects


def test_effective_severity_never_lowered(make_input):
    inp = make_input(analysis=make_analysis(severity=Severity.CRITICAL))
    assert Verifier().verify(inp).effective_severity is Severity.CRITICAL


def test_check_that_raises_fails_closed_to_human_only(make_input):
    def broken(_inp) -> Check:
        raise ValueError("boom")

    report = Verifier(check_fns=(broken,)).verify(make_input())
    assert not report.passed
    assert FailEffect.FORCE_HUMAN_ONLY in report.effects
    assert report.checks[0].name == "broken"
    assert "boom" in report.checks[0].detail


def test_verifier_runs_without_draft(make_input):
    report = Verifier().verify(make_input(with_draft=False))
    assert report.passed
