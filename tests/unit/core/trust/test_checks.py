"""Tests for deterministic trust checks."""

from __future__ import annotations

from src.core.models import Severity
from src.core.trust import checks
from src.core.trust.models import FailEffect, ProcessState
from tests.unit.core.trust.conftest import make_analysis, make_draft, make_result


class TestCitationsExist:
    def test_all_citations_in_kb_passes(self, make_input):
        assert checks.citations_exist(make_input()).passed

    def test_no_citations_fails(self, make_input):
        result = checks.citations_exist(make_input(draft=make_draft(citations=[])))
        assert not result.passed
        assert result.on_fail is FailEffect.BLOCK_AUTO

    def test_unknown_doc_id_fails(self, make_input):
        draft = make_draft(citations=[make_result("ghost")])
        result = checks.citations_exist(make_input(draft=draft))
        assert not result.passed
        assert "ghost" in result.detail

    def test_no_draft_passes_vacuously(self, make_input):
        assert checks.citations_exist(make_input(with_draft=False)).passed


class TestCitationsRetrieved:
    def test_cited_article_was_retrieved_passes(self, make_input):
        assert checks.citations_retrieved(make_input()).passed

    def test_cited_but_not_retrieved_fails(self, make_input):
        analysis = make_analysis(articles=[make_result("doc-1")])
        draft = make_draft(citations=[make_result("doc-2")])
        result = checks.citations_retrieved(make_input(analysis=analysis, draft=draft))
        assert not result.passed
        assert result.on_fail is FailEffect.BLOCK_AUTO


class TestErrorCodesValid:
    def test_known_code_passes(self, make_input):
        assert checks.error_codes_valid(make_input()).passed

    def test_hallucinated_code_fails(self, make_input):
        draft = make_draft(body="This is SYNC-099, restart the agent.")
        result = checks.error_codes_valid(make_input(draft=draft))
        assert not result.passed
        assert "SYNC-099" in result.detail

    def test_unrelated_prefix_ignored(self, make_input):
        draft = make_draft(body="See ISO-123 for details.")
        assert checks.error_codes_valid(make_input(draft=draft)).passed

    def test_no_codes_passes(self, make_input):
        draft = make_draft(body="Please restart the app.")
        assert checks.error_codes_valid(make_input(draft=draft)).passed


class TestPlanEntitlement:
    def test_feature_available_on_plan_passes(self, make_input):
        draft = make_draft(body="Set up a webhook endpoint in settings.")
        assert checks.plan_entitlement(make_input(draft=draft, plan="pro")).passed

    def test_feature_above_plan_fails_force_confirm(self, make_input):
        draft = make_draft(body="Configure SSO under Account > Security.")
        result = checks.plan_entitlement(make_input(draft=draft, plan="pro"))
        assert not result.passed
        assert result.on_fail is FailEffect.FORCE_CONFIRM

    def test_unknown_plan_with_gated_feature_fails(self, make_input):
        draft = make_draft(body="Enable SAML for your team.")
        assert not checks.plan_entitlement(make_input(draft=draft, plan="unknown")).passed

    def test_unknown_plan_without_gated_feature_passes(self, make_input):
        draft = make_draft(body="Restart the app.")
        assert checks.plan_entitlement(make_input(draft=draft, plan="unknown")).passed

    def test_enterprise_can_use_everything(self, make_input):
        draft = make_draft(body="Use SSO and the audit log and webhooks.")
        assert checks.plan_entitlement(make_input(draft=draft, plan="enterprise")).passed


class TestNoCommitments:
    def test_plain_draft_passes(self, make_input):
        assert checks.no_commitments(make_input()).passed

    def test_refund_promise_fails_human_only(self, make_input):
        draft = make_draft(body="We will issue a refund for last month.")
        result = checks.no_commitments(make_input(draft=draft))
        assert not result.passed
        assert result.on_fail is FailEffect.FORCE_HUMAN_ONLY

    def test_guarantee_fails(self, make_input):
        draft = make_draft(body="We guarantee this is fixed tonight.")
        assert not checks.no_commitments(make_input(draft=draft)).passed

    def test_time_promise_fails(self, make_input):
        draft = make_draft(body="Engineering will resolve this within 2 hours.")
        assert not checks.no_commitments(make_input(draft=draft)).passed

    def test_service_credit_fails(self, make_input):
        draft = make_draft(body="You will receive a service credit.")
        assert not checks.no_commitments(make_input(draft=draft)).passed


class TestSeverityFloor:
    def test_enterprise_all_users_affected_requires_high(self, make_input):
        inp = make_input(
            inquiry_text="Everyone on our team cannot sync",
            analysis=make_analysis(severity=Severity.LOW),
            plan="enterprise",
        )
        result = checks.severity_floor(inp)
        assert not result.passed
        assert result.on_fail is FailEffect.RAISE_SEVERITY
        assert result.floor is Severity.HIGH

    def test_sufficient_llm_severity_passes(self, make_input):
        inp = make_input(
            inquiry_text="Everyone on our team cannot sync",
            analysis=make_analysis(severity=Severity.CRITICAL),
            plan="enterprise",
        )
        assert checks.severity_floor(inp).passed

    def test_data_loss_requires_critical_for_any_plan(self, make_input):
        inp = make_input(
            inquiry_text="Our files were deleted and we have data loss",
            analysis=make_analysis(severity=Severity.MEDIUM),
            plan="free",
        )
        result = checks.severity_floor(inp)
        assert not result.passed
        assert result.floor is Severity.CRITICAL

    def test_no_trigger_passes(self, make_input):
        inp = make_input(analysis=make_analysis(severity=Severity.LOW))
        assert checks.severity_floor(inp).passed

    def test_works_without_draft(self, make_input):
        inp = make_input(
            inquiry_text="All users are down",
            analysis=make_analysis(severity=Severity.LOW),
            plan="enterprise",
            with_draft=False,
        )
        assert not checks.severity_floor(inp).passed


class TestPiiLeak:
    def test_clean_draft_passes(self, make_input):
        assert checks.pii_leak(make_input()).passed

    def test_log_ip_in_draft_fails(self, make_input):
        inp = make_input(
            log_text="client 203.0.113.9 failed",
            draft=make_draft(body="The request from 203.0.113.9 was blocked."),
        )
        assert not checks.pii_leak(inp).passed

    def test_log_email_in_draft_fails(self, make_input):
        inp = make_input(
            log_text="user=jane.doe@acme.com error",
            draft=make_draft(body="We saw jane.doe@acme.com in the logs."),
        )
        assert not checks.pii_leak(inp).passed

    def test_customer_provided_email_not_a_leak(self, make_input):
        inp = make_input(
            inquiry_text="Contact me at jane.doe@acme.com",
            log_text="user=jane.doe@acme.com",
            draft=make_draft(body="We will reach you at jane.doe@acme.com."),
        )
        assert checks.pii_leak(inp).passed

    def test_bearer_token_in_draft_always_fails(self, make_input):
        inp = make_input(draft=make_draft(body="Use Bearer abcdefghijklmnop1234567890 to retry."))
        result = checks.pii_leak(inp)
        assert not result.passed
        assert result.on_fail is FailEffect.BLOCK_AUTO

    def test_api_key_pattern_fails(self, make_input):
        inp = make_input(draft=make_draft(body="Your key sk-abcdefghijklmnopqrstuv is invalid."))
        assert not checks.pii_leak(inp).passed


class TestProcessState:
    def test_no_state_passes(self, make_input):
        assert checks.process_state(make_input()).passed

    def test_matching_step_passes(self, make_input):
        state = ProcessState(flow="sso_setup", recorded_step=3, claimed_step=3)
        assert checks.process_state(make_input(process_state=state)).passed

    def test_mismatched_step_fails_force_confirm(self, make_input):
        state = ProcessState(flow="sso_setup", recorded_step=2, claimed_step=4)
        result = checks.process_state(make_input(process_state=state))
        assert not result.passed
        assert result.on_fail is FailEffect.FORCE_CONFIRM
        assert "sso_setup" in result.detail
