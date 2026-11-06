"""The Intercom paths of the `watch` and `write-back` commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from src.cli import app
from src.core.briefing.models import Origin
from src.core.briefing.store import BriefingStore
from tests.unit.integrations.test_write_back import _make_briefing

runner = CliRunner()


def test_watch_intercom_without_a_token_explains_what_to_do(monkeypatch):
    monkeypatch.delenv("INTERCOM_ACCESS_TOKEN", raising=False)
    result = runner.invoke(app, ["watch", "--source", "intercom", "--once"])
    assert result.exit_code == 1
    assert "INTERCOM_ACCESS_TOKEN" in result.output


def test_watch_intercom_builds_the_intercom_source(monkeypatch):
    monkeypatch.setenv("INTERCOM_ACCESS_TOKEN", "t")
    source = MagicMock()
    source.fetch_updated.return_value = []
    with patch("src.cli.build_source", return_value=source) as build:
        result = runner.invoke(app, ["watch", "--source", "intercom", "--once", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert build.call_args.args[0] == "intercom"


def _store_with_intercom_briefing(tmp_path):
    db = tmp_path / "b.db"
    store = BriefingStore(str(db))
    store.add(_make_briefing(origin=Origin("intercom", "777", "777", "https://x/conversation/777")))
    return db


def test_write_back_to_intercom_needs_an_admin_id(tmp_path, monkeypatch):
    db = _store_with_intercom_briefing(tmp_path)
    monkeypatch.setenv("INTERCOM_ACCESS_TOKEN", "t")
    monkeypatch.delenv("INTERCOM_ADMIN_ID", raising=False)
    with patch("src.cli.BRIEFING_DB_PATH", str(db)):
        result = runner.invoke(app, ["write-back", "brief-1"])
    assert result.exit_code == 1
    assert "INTERCOM_ADMIN_ID" in result.output


def test_write_back_to_intercom_previews_by_default(tmp_path, monkeypatch):
    db = _store_with_intercom_briefing(tmp_path)
    monkeypatch.setenv("INTERCOM_ACCESS_TOKEN", "t")
    monkeypatch.setenv("INTERCOM_ADMIN_ID", "admin-9")
    fake = MagicMock()
    fake.get_conversation.return_value = {"conversation_parts": {"conversation_parts": []}}
    with (
        patch("src.cli.BRIEFING_DB_PATH", str(db)),
        patch("src.integrations.intercom.client.IntercomClient", return_value=fake),
    ):
        result = runner.invoke(app, ["write-back", "brief-1"])
    assert result.exit_code == 0, result.output
    assert "Dry run" in result.output
    fake.add_note.assert_not_called()
