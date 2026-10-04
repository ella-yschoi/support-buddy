"""Briefing queue and policy endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.schemas import ApproveRequest, BriefingRequest, BriefingResponse, PolicyResponse
from src.config import BRIEFING_DB_PATH
from src.core.briefing.builder import BriefingBuilder
from src.core.briefing.factory import DEFAULT_POLICY_PATH, build_local_builder
from src.core.briefing.models import Briefing
from src.core.briefing.store import BriefingStore
from src.core.exceptions import BriefingError
from src.core.policy.loader import load_policy
from src.core.trust.models import Customer

router = APIRouter(prefix="/api/v1")

_store: BriefingStore | None = None
_builder: BriefingBuilder | None = None


def get_store() -> BriefingStore:
    global _store
    if _store is None:
        _store = BriefingStore(BRIEFING_DB_PATH)
    return _store


def get_builder() -> BriefingBuilder:
    global _builder
    if _builder is None:
        from src.api.server import get_engine  # lazy: server imports this router

        _builder = build_local_builder(get_engine())
    return _builder


def _response(briefing: Briefing) -> BriefingResponse:
    return BriefingResponse.model_validate(briefing.to_dict())


@router.post("/briefings", response_model=BriefingResponse, status_code=201)
def create_briefing(
    req: BriefingRequest,
    builder: BriefingBuilder = Depends(get_builder),
    store: BriefingStore = Depends(get_store),
) -> BriefingResponse:
    briefing = builder.build(req.inquiry, Customer(plan=req.plan), req.logs)
    store.add(briefing)
    return _response(briefing)


@router.get("/briefings", response_model=list[BriefingResponse])
def list_briefings(store: BriefingStore = Depends(get_store)) -> list[BriefingResponse]:
    return [_response(b) for b in store.list_queue()]


@router.get("/briefings/{briefing_id}", response_model=BriefingResponse)
def get_briefing(briefing_id: str, store: BriefingStore = Depends(get_store)) -> BriefingResponse:
    try:
        return _response(store.get(briefing_id))
    except BriefingError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/briefings/{briefing_id}/approve", response_model=BriefingResponse)
def approve_briefing(
    briefing_id: str, req: ApproveRequest, store: BriefingStore = Depends(get_store)
) -> BriefingResponse:
    try:
        return _response(store.approve(briefing_id, req.final_body))
    except BriefingError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/policy", response_model=PolicyResponse)
def get_policy() -> PolicyResponse:
    """Read-only view of the autonomy policy in force."""
    p = load_policy(DEFAULT_POLICY_PATH)
    return PolicyResponse(
        auto_send_enabled=p.auto_send_enabled,
        human_only_keywords=list(p.human_only_keywords),
        human_only_categories=[c.value for c in p.human_only_categories],
        human_only_min_severity=p.human_only_min_severity.value,
        human_only_score_below=p.human_only_score_below,
        confirm_plans=list(p.confirm_plans),
        confirm_min_severity=p.confirm_min_severity.value,
        auto_categories=[c.value for c in p.auto_categories],
        auto_max_severity=p.auto_max_severity.value,
        auto_min_score=p.auto_min_score,
    )
