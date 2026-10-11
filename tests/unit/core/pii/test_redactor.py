"""Tests for PII redactor - must pass before implementing redactor.py."""

from __future__ import annotations

import pytest

from src.core.pii.redactor import PIIRedactor, RedactedText


class TestRedactedText:
    def test_redacted_text_holds_text_and_map(self) -> None:
        rt = RedactedText(text="hello [EMAIL_1]", reverse_map={"[EMAIL_1]": "user@example.com"})
        assert rt.text == "hello [EMAIL_1]"
        assert rt.reverse_map["[EMAIL_1]"] == "user@example.com"

    def test_restore_replaces_placeholders(self) -> None:
        rt = RedactedText(
            text="contact [EMAIL_1] or [EMAIL_2]",
            reverse_map={"[EMAIL_1]": "a@b.com", "[EMAIL_2]": "c@d.com"},
        )
        assert rt.restore() == "contact a@b.com or c@d.com"

    def test_restore_idempotent_when_no_placeholders(self) -> None:
        rt = RedactedText(text="nothing to restore", reverse_map={})
        assert rt.restore() == "nothing to restore"


class TestEmailRedaction:
    def test_redacts_simple_email(self) -> None:
        r = PIIRedactor()
        rt = r.redact("Please contact user@example.com for help.")
        assert "user@example.com" not in rt.text
        assert "[EMAIL_1]" in rt.text

    def test_redacts_multiple_emails(self) -> None:
        r = PIIRedactor()
        rt = r.redact("From alice@corp.io to bob@corp.io.")
        assert "alice@corp.io" not in rt.text
        assert "bob@corp.io" not in rt.text
        assert len(rt.reverse_map) == 2

    def test_same_email_reuses_placeholder(self) -> None:
        r = PIIRedactor()
        rt = r.redact("user@example.com and again user@example.com")
        assert rt.text.count("[EMAIL_1]") == 2
        assert len(rt.reverse_map) == 1

    def test_restore_recovers_email(self) -> None:
        r = PIIRedactor()
        rt = r.redact("Email: user@example.com")
        assert rt.restore() == "Email: user@example.com"


class TestIPRedaction:
    def test_redacts_ipv4(self) -> None:
        r = PIIRedactor()
        rt = r.redact("Server at 192.168.1.100 is down.")
        assert "192.168.1.100" not in rt.text
        assert "[IP_1]" in rt.text

    def test_does_not_redact_version_numbers(self) -> None:
        """Version strings like 1.2.3.4 with segments >255 are not IPs."""
        r = PIIRedactor()
        rt = r.redact("Using version 1.2.300.4 of the SDK.")
        assert "1.2.300.4" in rt.text

    def test_redacts_valid_ip_octet_ranges(self) -> None:
        r = PIIRedactor()
        rt = r.redact("IP 10.0.0.1 and 255.255.255.0 are valid.")
        assert "10.0.0.1" not in rt.text
        assert "255.255.255.0" not in rt.text


class TestAPIKeyRedaction:
    def test_redacts_anthropic_api_key(self) -> None:
        r = PIIRedactor()
        rt = r.redact("Key is sk-ant-api03-ABCDEF1234567890abcdef.")
        assert "sk-ant-api03-ABCDEF1234567890abcdef" not in rt.text
        assert "[API_KEY_1]" in rt.text

    def test_redacts_linear_api_key(self) -> None:
        r = PIIRedactor()
        rt = r.redact("Token: lin_api_abc123XYZ456.")
        assert "lin_api_abc123XYZ456" not in rt.text
        assert "[API_KEY_1]" in rt.text

    def test_redacts_generic_bearer_token(self) -> None:
        r = PIIRedactor()
        rt = r.redact("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc.def")
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in rt.text

    def test_redacts_long_hex_token(self) -> None:
        """Hex strings >= 32 chars that look like secrets."""
        r = PIIRedactor()
        rt = r.redact("secret=aabbccddeeff00112233445566778899")
        assert "aabbccddeeff00112233445566778899" not in rt.text


class TestPhoneRedaction:
    def test_redacts_us_phone_with_dashes(self) -> None:
        r = PIIRedactor()
        rt = r.redact("Call us at 555-867-5309.")
        assert "555-867-5309" not in rt.text
        assert "[PHONE_1]" in rt.text

    def test_redacts_us_phone_with_dots(self) -> None:
        r = PIIRedactor()
        rt = r.redact("Phone: 555.867.5309")
        assert "555.867.5309" not in rt.text

    def test_redacts_international_phone(self) -> None:
        r = PIIRedactor()
        rt = r.redact("Call +1 (555) 867-5309 for support.")
        assert "+1 (555) 867-5309" not in rt.text


class TestMixedPII:
    def test_redacts_multiple_pii_types(self) -> None:
        r = PIIRedactor()
        text = "Email user@corp.com at IP 10.0.0.1 using key sk-ant-api03-XXXX1234567890xxxxABCDEFGHIJKLMNOP."
        rt = r.redact(text)
        assert "user@corp.com" not in rt.text
        assert "10.0.0.1" not in rt.text
        assert "sk-ant-api03-XXXX1234567890xxxxABCDEFGHIJKLMNOP" not in rt.text

    def test_plain_text_unchanged(self) -> None:
        r = PIIRedactor()
        text = "The API rate limit is 1000 requests per hour."
        rt = r.redact(text)
        assert rt.text == text
        assert rt.reverse_map == {}

    def test_restore_full_round_trip(self) -> None:
        r = PIIRedactor()
        original = "Contact alice@example.com at 192.168.0.1."
        rt = r.redact(original)
        assert rt.restore() == original


class TestCounterReset:
    def test_each_redact_call_has_independent_counters(self) -> None:
        r = PIIRedactor()
        rt1 = r.redact("a@b.com")
        rt2 = r.redact("c@d.com")
        assert "[EMAIL_1]" in rt1.text
        assert "[EMAIL_1]" in rt2.text
