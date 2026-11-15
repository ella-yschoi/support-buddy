"""Write briefing notes to Intercom as private notes. A human always sends the reply."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from src.core.briefing.models import Briefing
from src.integrations.intercom.client import IntercomClient


def _marker(briefing_id: str) -> str:
    # Visible text on purpose: Intercom may strip HTML comments, and we need to find it again.
    return f"Support Buddy briefing {briefing_id}"


def _paragraphs(text: str) -> str:
    return "".join(f"<p>{escape(p).replace(chr(10), '<br/>')}</p>" for p in text.split("\n\n") if p)


def format_note(briefing: Briefing) -> str:
    parts = [
        "<p><b>Support Buddy briefing</b></p>",
        f"<p><b>Summary:</b> {escape(briefing.summary)}<br/>"
        f"<b>Severity:</b> {briefing.effective_severity.value} | "
        f"<b>Category:</b> {briefing.category.value} | "
        f"<b>Routing:</b> {briefing.autonomy.value}</p>",
    ]
    if briefing.autonomy_reasons:
        items = "".join(f"<li>{escape(r)}</li>" for r in briefing.autonomy_reasons)
        parts.append(f"<p><b>Routing reasons:</b></p><ul>{items}</ul>")
    if briefing.citations:
        items = "".join(f"<li>{escape(c.title)}</li>" for c in briefing.citations)
        parts.append(f"<p><b>KB references:</b></p><ul>{items}</ul>")
    failed = [c for c in briefing.checks if not c.passed]
    if failed:
        items = "".join(f"<li>{escape(c.name)}: {escape(c.detail)}</li>" for c in failed)
        parts.append(f"<p><b>Failed checks:</b></p><ul>{items}</ul>")
    if briefing.draft_body:
        parts.append("<p><b>Draft reply (not sent):</b></p>" + _paragraphs(briefing.draft_body))
    else:
        parts.append("<p><i>No draft available.</i></p>")
    parts.append(
        f"<p><i>{_marker(briefing.id)} · score {briefing.verification_score:.2f}</i></p>"
    )
    return "".join(parts)


@dataclass
class IntercomWriteBackResult:
    dry_run: bool
    already_posted: bool = False
    note_id: str | None = None
    preview: str | None = None


class IntercomWriteBack:
    def __init__(self, client: IntercomClient, admin_id: str) -> None:
        if not admin_id:
            raise ValueError("INTERCOM_ADMIN_ID is not set")
        self._client = client
        self._admin_id = admin_id

    def _already_posted(self, conversation_id: str, briefing_id: str) -> bool:
        marker = _marker(briefing_id)
        conversation = self._client.get_conversation(conversation_id)
        parts = (conversation.get("conversation_parts") or {}).get("conversation_parts") or []
        return any(marker in (p.get("body") or "") for p in parts)

    def post_briefing_note(
        self, conversation_id: str, briefing: Briefing, dry_run: bool = True
    ) -> IntercomWriteBackResult:
        """Add the briefing as a private note. Dry run by default; idempotent per briefing."""
        if self._already_posted(conversation_id, briefing.id):
            return IntercomWriteBackResult(dry_run=dry_run, already_posted=True)
        body = format_note(briefing)
        if dry_run:
            return IntercomWriteBackResult(dry_run=True, preview=body)
        response = self._client.add_note(conversation_id, self._admin_id, body)
        return IntercomWriteBackResult(dry_run=False, note_id=str(response.get("id")), preview=body)
