"""Folder-drop trigger: turn dropped .eml files into briefings."""

from __future__ import annotations

import hashlib
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
    The briefing id is derived from the file content, so a file left behind by a failed move
    is recognised on the next run instead of producing a duplicate. Returns the ids of the
    briefings created in this call.
    """
    processed_dir.mkdir(parents=True, exist_ok=True)
    parser = EmailParser()
    created: list[str] = []

    for eml in sorted(inbox_dir.glob("*.eml")):
        raw_bytes = eml.read_bytes()
        briefing_id = "eml-" + hashlib.sha256(raw_bytes).hexdigest()[:12]
        sidecar = eml.with_suffix(".log")

        if not store.exists(briefing_id):
            raw = raw_bytes.decode("utf-8", errors="replace")
            inquiry_text = parser.parse(raw).to_inquiry_text() or raw
            log_text = (
                sidecar.read_text(encoding="utf-8", errors="replace") if sidecar.exists() else ""
            )
            briefing = builder.build(
                inquiry_text, Customer(plan=default_plan), log_text, briefing_id=briefing_id
            )
            store.add(briefing)
            created.append(briefing.id)

        shutil.move(str(eml), processed_dir / eml.name)
        if sidecar.exists():
            shutil.move(str(sidecar), processed_dir / sidecar.name)
    return created
