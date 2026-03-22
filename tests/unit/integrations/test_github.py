"""Tests for GitHub client (mocked HTTP)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.integrations.github.client import GitHubClient, GitHubIssue


@pytest.fixture
def mock_httpx():
    with patch("src.integrations.github.client.httpx") as mock:
        yield mock


def _make_response(data) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = data
    resp.raise_for_status.return_value = None
    return resp


class TestGitHubClient:
    def test_init_raises_without_token(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="GITHUB_TOKEN"):
                GitHubClient(token="")

    def test_get_issue(self, mock_httpx):
        mock_httpx.Client.return_value.__enter__.return_value.get.return_value = _make_response({
            "number": 42,
            "title": "SYNC-002 upload failure",
            "body": "Upload fails with quota error",
            "state": "open",
            "labels": [{"name": "bug"}, {"name": "sync"}],
            "html_url": "https://github.com/org/repo/issues/42",
        })

        client = GitHubClient(token="test", owner="org", repo="repo")
        issue = client.get_issue(42)

        assert issue.number == 42
        assert issue.title == "SYNC-002 upload failure"
        assert "bug" in issue.labels
        assert issue.is_pull_request is False

    def test_search_issues(self, mock_httpx):
        mock_httpx.Client.return_value.__enter__.return_value.get.return_value = _make_response({
            "items": [
                {
                    "number": 10, "title": "Fix sync error",
                    "body": "", "state": "closed",
                    "labels": [], "html_url": "",
                },
                {
                    "number": 20, "title": "Sync performance",
                    "body": "", "state": "open",
                    "labels": [{"name": "enhancement"}], "html_url": "",
                    "pull_request": {"url": "..."},
                },
            ]
        })

        client = GitHubClient(token="test", owner="org", repo="repo")
        issues = client.search_issues("sync")

        assert len(issues) == 2
        assert issues[0].number == 10
        assert issues[0].is_pull_request is False
        assert issues[1].is_pull_request is True

    def test_add_comment(self, mock_httpx):
        mock_httpx.Client.return_value.__enter__.return_value.post.return_value = _make_response({
            "id": 999,
        })

        client = GitHubClient(token="test", owner="org", repo="repo")
        comment_id = client.add_comment(42, "Analysis from Support Buddy")

        assert comment_id == 999

    def test_search_related_issues(self, mock_httpx):
        mock_httpx.Client.return_value.__enter__.return_value.get.return_value = _make_response({
            "items": [
                {"number": 5, "title": "SYNC-002 fix", "body": "", "state": "closed",
                 "labels": [], "html_url": ""},
            ]
        })

        client = GitHubClient(token="test", owner="org", repo="repo")
        issues = client.search_related_issues("SYNC-002")

        assert len(issues) == 1
        assert "SYNC-002" in issues[0].title
