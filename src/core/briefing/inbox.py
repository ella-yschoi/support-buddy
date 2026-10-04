"""Folder-drop trigger: turn dropped .eml files into briefings."""

from __future__ import annotations

import shutil
from pathlib import Path

from src.core.briefing.builder import BriefingBuilder
from src.core.briefing.store import BriefingStore
from src.core.trust.models import Customer
from src.integrations.email.parser import EmailParser


def process_inbox(
    builder: BriefingBuilder,
    store: BriefingStore,
    inbox_dir: Path,
    processed_dir: Path,
    default_plan: str = "unknown",
) -> list[str]:
    """Build and store a briefing per .eml file, then move it (and its .log sidecar) away.

    A file that cannot be parsed cleanly still produces a briefing, so no ticket is lost.
    """
    processed_dir.mkdir(parents=True, exist_ok=True)
    parser = EmailParser()
    ids: list[str] = []

    for eml in sorted(inbox_dir.glob("*.eml")):
        raw = eml.read_bytes().decode("utf-8", errors="replace")
        inquiry_text = parser.parse(raw).to_inquiry_text() or raw

        sidecar = eml.with_suffix(".log")
        log_text = sidecar.read_text(encoding="utf-8", errors="replace") if sidecar.exists() else ""

        briefing = builder.build(inquiry_text, Customer(plan=default_plan), log_text)
        store.add(briefing)
        ids.append(briefing.id)

        shutil.move(str(eml), processed_dir / eml.name)
        if sidecar.exists():
            shutil.move(str(sidecar), processed_dir / sidecar.name)
    return ids
