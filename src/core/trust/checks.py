"""Deterministic checks. Each is a pure function: TrustInput -> Check."""

from __future__ import annotations

from src.core.models import Severity
from src.core.trust import rules
from src.core.trust.models import Check, FailEffect, TrustInput


def _body(inp: TrustInput) -> str:
    return inp.draft.body if inp.draft else ""


def citations_exist(inp: TrustInput) -> Check:
    if inp.draft is None:
        return Check("citations_exist", True, 2.0, "no draft")
    cited = [c.doc_id for c in inp.draft.citations]
    missing = [d for d in cited if d not in inp.kb_index.doc_ids]
    if not cited:
        return Check("citations_exist", False, 2.0, "draft cites no sources", FailEffect.BLOCK_AUTO)
    if missing:
        return Check(
            "citations_exist",
            False,
            2.0,
            f"unknown sources: {', '.join(missing)}",
            FailEffect.BLOCK_AUTO,
        )
    return Check("citations_exist", True, 2.0, f"{len(cited)} sources found")


def citations_retrieved(inp: TrustInput) -> Check:
    if inp.draft is None:
        return Check("citations_retrieved", True, 1.0, "no draft")
    retrieved = {a.doc_id for a in inp.analysis.relevant_articles}
    stray = [c.doc_id for c in inp.draft.citations if c.doc_id not in retrieved]
    if stray:
        return Check(
            "citations_retrieved",
            False,
            1.0,
            f"cited but never retrieved: {', '.join(stray)}",
            FailEffect.BLOCK_AUTO,
        )
    return Check("citations_retrieved", True, 1.0, "all cited sources were retrieved")


def error_codes_valid(inp: TrustInput) -> Check:
    prefixes = inp.kb_index.error_prefixes | rules.PRODUCT_ERROR_PREFIXES
    found = {
        m.group(0)
        for m in rules.ERROR_CODE_TOKEN_RE.finditer(_body(inp))
        if m.group(1) in prefixes
    }
    unknown = sorted(found - inp.kb_index.error_codes)
    if unknown:
        return Check(
            "error_codes_valid",
            False,
            2.0,
            f"unknown error codes: {', '.join(unknown)}",
            FailEffect.BLOCK_AUTO,
        )
    return Check("error_codes_valid", True, 2.0, f"{len(found)} codes verified")


def plan_entitlement(inp: TrustInput) -> Check:
    # Both the customer's question and our draft count: asking about a feature the
    # plan lacks is as much a reason for review as recommending one.
    body = f"{inp.inquiry_text}\n{_body(inp)}"
    mentioned = {
        f: p for f, p in rules.FEATURE_MIN_PLAN.items() if rules.FEATURE_PATTERNS[f].search(body)
    }
    if not mentioned:
        return Check("plan_entitlement", True, 1.0, "no plan-gated features mentioned")
    plan = inp.customer.plan.lower()
    if plan not in rules.PLAN_ORDER:
        return Check(
            "plan_entitlement",
            False,
            1.0,
            f"customer plan unknown; gated features: {', '.join(sorted(mentioned))}",
            FailEffect.FORCE_CONFIRM,
        )
    level = rules.PLAN_ORDER.index(plan)
    blocked = sorted(f for f, p in mentioned.items() if rules.PLAN_ORDER.index(p) > level)
    if blocked:
        return Check(
            "plan_entitlement",
            False,
            1.0,
            f"not on {plan} plan: {', '.join(blocked)}",
            FailEffect.FORCE_CONFIRM,
        )
    return Check("plan_entitlement", True, 1.0, f"features available on {plan}")


def no_commitments(inp: TrustInput) -> Check:
    body = _body(inp)
    hits = sorted({m.group(0).lower() for p in rules.COMMITMENT_PATTERNS for m in p.finditer(body)})
    if hits:
        return Check(
            "no_commitments",
            False,
            3.0,
            f"commitment language: {', '.join(hits)}",
            FailEffect.FORCE_HUMAN_ONLY,
        )
    return Check("no_commitments", True, 3.0, "no refund/SLA/time promises")


def severity_floor(inp: TrustInput) -> Check:
    text = inp.inquiry_text
    floor: Severity | None = None
    reason = ""
    if rules.DATA_LOSS_RE.search(text):
        floor, reason = Severity.CRITICAL, "data loss / security language"
    elif inp.customer.plan.lower() == "enterprise" and rules.ALL_AFFECTED_RE.search(text):
        floor, reason = Severity.HIGH, "enterprise customer, all users affected"
    if floor is None:
        return Check("severity_floor", True, 2.0, "no floor rule triggered")
    order = rules.SEVERITY_ORDER
    if order.index(inp.analysis.severity) >= order.index(floor):
        return Check("severity_floor", True, 2.0, f"{reason}: floor {floor.value} met", floor=floor)
    return Check(
        "severity_floor",
        False,
        2.0,
        f"{reason}: floor {floor.value}, model said {inp.analysis.severity.value}",
        FailEffect.RAISE_SEVERITY,
        floor,
    )


def pii_leak(inp: TrustInput) -> Check:
    body = _body(inp)
    if any(p.search(body) for p in rules.SECRET_PATTERNS):
        return Check(
            "pii_leak", False, 3.0, "credential-like token in draft", FailEffect.BLOCK_AUTO
        )

    def values(text: str) -> set[str]:
        return {m.group(0) for p in rules.SENSITIVE_VALUE_PATTERNS for m in p.finditer(text)}

    leaked = sorted((values(inp.log_text) - values(inp.inquiry_text)) & values(body))
    if leaked:
        return Check(
            "pii_leak",
            False,
            3.0,
            f"log values repeated in draft: {', '.join(leaked)}",
            FailEffect.BLOCK_AUTO,
        )
    return Check("pii_leak", True, 3.0, "no leaked values")


def process_state(inp: TrustInput) -> Check:
    state = inp.process_state
    if state is None:
        return Check("process_state", True, 1.0, "no multi-step flow")
    if state.claimed_step == state.recorded_step:
        return Check("process_state", True, 1.0, f"{state.flow}: step {state.recorded_step}")
    return Check(
        "process_state",
        False,
        1.0,
        f"{state.flow}: recorded step {state.recorded_step}, claimed {state.claimed_step}",
        FailEffect.FORCE_CONFIRM,
    )


ALL_CHECKS = (
    citations_exist,
    citations_retrieved,
    error_codes_valid,
    plan_entitlement,
    no_commitments,
    severity_floor,
    pii_leak,
    process_state,
)
