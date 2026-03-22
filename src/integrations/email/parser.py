"""Email parser — extract structured inquiry from email content."""

from __future__ import annotations

import email
import re
from dataclasses import dataclass, field
from email.message import Message
from html.parser import HTMLParser
from io import StringIO


@dataclass
class ParsedEmail:
    sender: str = ""
    recipient: str = ""
    subject: str = ""
    date: str = ""
    body: str = ""
    error_codes: list[str] = field(default_factory=list)

    def to_inquiry_text(self) -> str:
        """Combine subject and body into a single inquiry text for analysis."""
        parts = []
        if self.subject:
            parts.append(f"Subject: {self.subject}")
        if self.body:
            parts.append(self.body)
        return "\n\n".join(parts)


_ERROR_CODE_PATTERN = re.compile(
    r"(SYNC-\d{3}|AUTH-\d{3}|PERF-\d{3}|API-\d{3}|ACCT-\d{3})",
    re.IGNORECASE,
)


class _HTMLStripper(HTMLParser):
    """Simple HTML-to-text converter."""

    def __init__(self) -> None:
        super().__init__()
        self._text = StringIO()
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._skip = True
        elif tag in ("br", "p", "div", "li", "tr"):
            self._text.write("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip = False
        elif tag == "p":
            self._text.write("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._text.write(data)

    def get_text(self) -> str:
        return self._text.getvalue().strip()


def _strip_html(html: str) -> str:
    stripper = _HTMLStripper()
    stripper.feed(html)
    return stripper.get_text()


class EmailParser:
    """Parse raw email content into structured ParsedEmail."""

    def parse(self, raw_email: str) -> ParsedEmail:
        if not raw_email or not raw_email.strip():
            return ParsedEmail()

        msg = email.message_from_string(raw_email)
        body = self._extract_body(msg)
        all_text = f"{msg.get('Subject', '')} {body}"

        return ParsedEmail(
            sender=msg.get("From", ""),
            recipient=msg.get("To", ""),
            subject=msg.get("Subject", ""),
            date=msg.get("Date", ""),
            body=body,
            error_codes=self._extract_error_codes(all_text),
        )

    def _extract_body(self, msg: Message) -> str:
        if msg.is_multipart():
            # Prefer plain text over HTML
            plain_body = ""
            html_body = ""
            for part in msg.walk():
                content_type = part.get_content_type()
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                text = payload.decode("utf-8", errors="replace")
                if content_type == "text/plain":
                    plain_body = text.strip()
                elif content_type == "text/html":
                    html_body = _strip_html(text)
            return plain_body or html_body
        else:
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload is None:
                # Fallback: get_payload without decode for simple messages
                raw = msg.get_payload()
                if isinstance(raw, str):
                    text = raw.strip()
                else:
                    return ""
            else:
                text = payload.decode("utf-8", errors="replace").strip()

            if content_type == "text/html":
                return _strip_html(text)
            return text

    def _extract_error_codes(self, text: str) -> list[str]:
        return sorted(set(c.upper() for c in _ERROR_CODE_PATTERN.findall(text)))
