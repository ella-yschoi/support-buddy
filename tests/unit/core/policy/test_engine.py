"""Tests for the autonomy policy engine."""

from __future__ import annotations

import pytest

from src.core.models import InquiryCategory, Severity
from src.core.policy.engine import PolicyEngine
from src.core.policy.models import AutonomyLevel, Policy
from src.core.trust.verifier import Verifier
from tests.unit.core.conftest import make_analysis, make_draft


@pytest.fixture
def policy() -> Policy:
    return Policy(
        human_only_keywords=("breach", "refund", "lawsuit"),
        human_only_categories=(InquiryCategory.UNKNOWN,),
        human_only_min_severity=Severity.CRITICAL,
        human_only_score_below=0.7,
        confirm_plans=("enterprise",),
        confirm_min_severity=Severity.HIGH,
        auto_categories=(InquiryCategory.FEATURE,),
        auto_max_severity=Severity.MEDIUM,
        auto_min_score=1.0,
        auto_send_enabled=False,
    )


def route(policy, inp):
    report = Verifier().verify(inp)
    return PolicyEngine(policy).route(inp, report)


def feature_analysis(severity: Severity = Severity.LOW):
    analysis = make_analysis(severity=severity)
    analysis.category = InquiryCategory.FEATURE
    return analysis


class TestHumanOnly:
    def test_security_keyword_is_human_only(self, policy, make_input):
        inp = make_input(
            inquiry_text="We suspect a data breach", analysis=feature_analysis(), plan="free"
        )
        decision = route(policy, inp)
        assert decision.level is AutonomyLevel.HUMAN_ONLY
        assert any("breach" in r for r in decision.reasons)

    def test_refund_keyword_is_human_only(self, policy, make_input):
        inp = make_input(inquiry_text="I want a refund", analysis=feature_analysis())
        assert route(policy, inp).level is AutonomyLevel.HUMAN_ONLY

    def test_keyword_matches_whole_words_only(self, policy, make_input):
        text = "Is auto-refunding a feature? Also, a preacher asked."
        inp = make_input(inquiry_text=text, analysis=feature_analysis())
        # "preacher" must not match "breach"; "refunding" is not the word "refund"
        assert route(policy, inp).level is not AutonomyLevel.HUMAN_ONLY

    def test_unknown_category_is_human_only(self, policy, make_input):
        analysis = make_analysis()
        analysis.category = InquiryCategory.UNKNOWN
        assert route(policy, make_input(analysis=analysis)).level is AutonomyLevel.HUMAN_ONLY

    def test_critical_effective_severity_is_human_only(self, policy, make_input):
        inp = make_input(analysis=feature_analysis(Severity.CRITICAL))
        assert route(policy, inp).level is AutonomyLevel.HUMAN_ONLY

    def test_severity_floor_escalation_to_critical_is_human_only(self, policy, make_input):
        inp = make_input(
            inquiry_text="Our files were deleted, data loss everywhere",
            analysis=feature_analysis(Severity.LOW),
        )
        assert route(policy, inp).level is AutonomyLevel.HUMAN_ONLY

    def test_commitment_language_is_human_only(self, policy, make_input):
        inp = make_input(
            analysis=feature_analysis(), draft=make_draft(body="We guarantee a fix. SYNC-002")
        )
        assert route(policy, inp).level is AutonomyLevel.HUMAN_ONLY

    def test_no_draft_is_human_only(self, policy, make_input):
        inp = make_input(analysis=feature_analysis(), with_draft=False)
        assert route(policy, inp).level is AutonomyLevel.HUMAN_ONLY

    def test_very_low_score_is_human_only(self, policy, make_input):
        inp = make_input(
            analysis=feature_analysis(),
            draft=make_draft(body="Try SYNC-099 and enable SSO", citations=[]),
            plan="free",
        )
        assert route(policy, inp).level is AutonomyLevel.HUMAN_ONLY


class TestConfirm:
    def test_enterprise_plan_is_confirm(self, policy, make_input):
        inp = make_input(analysis=feature_analysis(), plan="enterprise")
        decision = route(policy, inp)
        assert decision.level is AutonomyLevel.CONFIRM
        assert any("enterprise" in r.lower() for r in decision.reasons)

    def test_high_severity_is_confirm(self, policy, make_input):
        inp = make_input(analysis=feature_analysis(Severity.HIGH))
        assert route(policy, inp).level is AutonomyLevel.CONFIRM

    def test_category_not_in_auto_list_is_confirm(self, policy, make_input):
        inp = make_input(analysis=make_analysis(severity=Severity.LOW))  # SYNC
        assert route(policy, inp).level is AutonomyLevel.CONFIRM

    def test_failed_block_auto_check_caps_at_confirm(self, policy, make_input):
        inp = make_input(
            analysis=feature_analysis(), draft=make_draft(body="See SYNC-099 for details.")
        )
        decision = route(policy, inp)
        assert decision.level is AutonomyLevel.CONFIRM
        assert any("error_codes_valid" in r for r in decision.reasons)

    def test_plan_entitlement_warning_forces_confirm(self, policy, make_input):
        inp = make_input(
            analysis=feature_analysis(), draft=make_draft(body="Enable SSO. SYNC-002"), plan="pro"
        )
        assert route(policy, inp).level is AutonomyLevel.CONFIRM


class TestAuto:
    def test_clean_low_risk_feature_question_is_auto(self, policy, make_input):
        inp = make_input(analysis=feature_analysis(), plan="pro")
        decision = route(policy, inp)
        assert decision.level is AutonomyLevel.AUTO

    def test_auto_is_simulated_when_sending_disabled(self, policy, make_input):
        decision = route(policy, make_input(analysis=feature_analysis(), plan="pro"))
        assert decision.simulated is True

    def test_auto_not_simulated_when_sending_enabled(self, policy, make_input):
        enabled = Policy(**{**policy.__dict__, "auto_send_enabled": True})
        decision = route(enabled, make_input(analysis=feature_analysis(), plan="pro"))
        assert decision.level is AutonomyLevel.AUTO
        assert decision.simulated is False

    def test_every_decision_has_reasons(self, policy, make_input):
        decision = route(policy, make_input(analysis=feature_analysis(), plan="pro"))
        assert decision.reasons


class TestFailSafe:
    def test_error_in_routing_fails_safe_to_human_only(self, policy, make_input):
        class Boom:
            @property
            def effects(self):
                raise TypeError("corrupt report")

        decision = PolicyEngine(policy).route(make_input(), Boom())
        assert decision.level is AutonomyLevel.HUMAN_ONLY
        assert any("fail-safe" in r.lower() for r in decision.reasons)
