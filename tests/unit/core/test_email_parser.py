"""Tests for email parser."""

from __future__ import annotations

import pytest

from src.integrations.email.parser import EmailParser, ParsedEmail


SAMPLE_PLAIN_EMAIL = """\
From: john.doe@acmecorp.com
To: support@cloudsync.io
Subject: Files not syncing since this morning
Date: Mon, 15 Jan 2024 10:30:00 +0000

Hi Support Team,

Since this morning, my files are not syncing between my Mac and Windows laptop.
I keep getting an error code SYNC-002 when trying to upload large files.

I've already tried restarting the sync agent but the problem persists.

Could you please help?

Thanks,
John Doe
Acme Corp
"""

SAMPLE_HTML_EMAIL = """\
From: jane@example.com
To: support@cloudsync.io
Subject: Permission denied on shared folder
Date: Tue, 16 Jan 2024 09:15:00 +0000
Content-Type: text/html

<html>
<body>
<p>Hello,</p>
<p>I'm getting <strong>AUTH-002</strong> permission denied when trying to access
the shared folder "Q4 Reports" that my manager shared with me yesterday.</p>
<p>My account email is jane@example.com and I'm on the Pro plan.</p>
<p>Regards,<br>Jane</p>
</body>
</html>
"""

SAMPLE_MULTIPART_EMAIL = """\
From: bob@company.com
To: support@cloudsync.io
Subject: Webhook not firing
Date: Wed, 17 Jan 2024 14:00:00 +0000
MIME-Version: 1.0
Content-Type: multipart/alternative; boundary="boundary123"

--boundary123
Content-Type: text/plain

Our webhook endpoint at https://api.company.com/webhook is not receiving events.
We updated our SSL certificate yesterday.
Error: API-002

--boundary123
Content-Type: text/html

<html><body><p>Our webhook endpoint at https://api.company.com/webhook is not receiving events.</p>
<p>We updated our SSL certificate yesterday.</p>
<p>Error: API-002</p></body></html>
--boundary123--
"""


class TestEmailParser:
    def test_parse_plain_text_email(self):
        parser = EmailParser()
        result = parser.parse(SAMPLE_PLAIN_EMAIL)

        assert result.sender == "john.doe@acmecorp.com"
        assert result.subject == "Files not syncing since this morning"
        assert "SYNC-002" in result.body
        assert "not syncing" in result.body

    def test_parse_html_email_strips_tags(self):
        parser = EmailParser()
        result = parser.parse(SAMPLE_HTML_EMAIL)

        assert result.sender == "jane@example.com"
        assert "AUTH-002" in result.body
        assert "<strong>" not in result.body
        assert "permission denied" in result.body.lower()

    def test_parse_multipart_prefers_plain(self):
        parser = EmailParser()
        result = parser.parse(SAMPLE_MULTIPART_EMAIL)

        assert result.sender == "bob@company.com"
        assert "API-002" in result.body
        assert "<html>" not in result.body

    def test_extract_error_codes(self):
        parser = EmailParser()
        result = parser.parse(SAMPLE_PLAIN_EMAIL)

        assert "SYNC-002" in result.error_codes

    def test_extract_error_codes_from_html(self):
        parser = EmailParser()
        result = parser.parse(SAMPLE_HTML_EMAIL)

        assert "AUTH-002" in result.error_codes

    def test_empty_input(self):
        parser = EmailParser()
        result = parser.parse("")

        assert result.sender == ""
        assert result.subject == ""
        assert result.body == ""

    def test_parsed_email_to_inquiry_text(self):
        parser = EmailParser()
        result = parser.parse(SAMPLE_PLAIN_EMAIL)
        inquiry = result.to_inquiry_text()

        assert "Files not syncing" in inquiry
        assert "SYNC-002" in inquiry
