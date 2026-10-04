"""Pre-computed briefings for the public demo, so it never needs an API key."""

from __future__ import annotations

import dataclasses
import json
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

from src.config import KNOWLEDGE_DIR
from src.core.briefing.factory import build_local_builder
from src.core.briefing.models import Briefing
from src.core.knowledge.engine import KnowledgeEngine
from src.core.trust.rules import SEVERITY_ORDER
from src.eval.cases import DEFAULT_GOLDEN_DIR, load_golden

# A varied slice of the golden set: every autonomy level, with and without logs.
DEMO_CASE_IDS: tuple[str, ...] = (
    "sync-quota-free",
    "sync-all-users-enterprise",
    "sync-conflict-pro",
    "perm-sso-outage-enterprise",
    "api-webhook-timeout-enterprise",
    "api-rate-limit-pro",
    "perf-dashboard-slow-pro",
    "acct-payment-failed-pro",
    "feat-auto-backup-pro",
    "feat-2fa-free",
    "feat-sso-okta-pro",
    "adv-suspected-breach-enterprise",
    "adv-refund-demand-pro",
    "adv-vague-free",
)

_QUEUE_START = datetime(2026, 10, 4, 2, 0, 0)
_SPACING = timedelta(minutes=17)


def generate_demo_briefings() -> list[Briefing]:
    """Run the free local pipeline over the demo cases. Deterministic."""
    by_id = {c.id: c for c in load_golden(DEFAULT_GOLDEN_DIR)}
    with tempfile.TemporaryDirectory() as tmp:
        engine = KnowledgeEngine(persist_dir=tmp)
        engine.ingest_directory(KNOWLEDGE_DIR)
        builder = build_local_builder(engine)

        briefings = []
        for index, case_id in enumerate(DEMO_CASE_IDS):
            case = by_id[case_id]
            built = builder.build(
                case.inquiry, case.customer, case.log_text, briefing_id=f"demo-{case_id}"
            )
            created = (_QUEUE_START + index * _SPACING).isoformat(timespec="seconds")
            briefings.append(dataclasses.replace(built, created_at=created))

    return sorted(
        briefings,
        key=lambda b: (-SEVERITY_ORDER.index(b.effective_severity), b.created_at),
    )


def write_demo_file(briefings: list[Briefing], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_on": date.today().isoformat(),
        "pipeline": "local",
        "briefings": [b.to_dict() for b in briefings],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
