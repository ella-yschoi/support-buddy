"""Tests for Linear client (mocked HTTP)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.integrations.linear.client import LinearClient, LinearIssue


@pytest.fixture
def mock_httpx():
    with patch("src.integrations.linear.client.httpx") as mock:
        yield mock


def _make_response(data: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {"data": data}
    resp.raise_for_status.return_value = None
    return resp


class TestLinearClient:
    def test_init_raises_without_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="LINEAR_API_KEY"):
                LinearClient(api_key="")

    def test_get_issue(self, mock_httpx):
        mock_httpx.Client.return_value.__enter__.return_value.post.return_value = _make_response({
            "issue": {
                "id": "abc-123",
                "identifier": "ENG-42",
                "title": "Sync not working",
                "description": "Files fail to sync",
                "state": {"name": "In Progress"},
                "priority": 2,
                "assignee": {"name": "Alice"},
                "labels": {"nodes": [{"name": "bug"}]},
                "url": "https://linear.app/team/ENG-42",
            }
        })

        client = LinearClient(api_key="test-key")
        issue = client.get_issue("abc-123")

        assert issue.identifier == "ENG-42"
        assert issue.title == "Sync not working"
        assert issue.state == "In Progress"
        assert issue.assignee == "Alice"
        assert "bug" in issue.labels

    def test_search_issues(self, mock_httpx):
        mock_httpx.Client.return_value.__enter__.return_value.post.return_value = _make_response({
            "issues": {
                "nodes": [
                    {
                        "id": "1", "identifier": "ENG-1", "title": "Sync bug",
                        "description": "", "state": {"name": "Open"},
                        "priority": 1, "assignee": None, "labels": {"nodes": []},
                        "url": "",
                    },
                    {
                        "id": "2", "identifier": "ENG-2", "title": "Another sync issue",
                        "description": "", "state": {"name": "Open"},
                        "priority": 2, "assignee": None, "labels": {"nodes": []},
                        "url": "",
                    },
                ]
            }
        })

        client = LinearClient(api_key="test-key")
        issues = client.search_issues("sync")

        assert len(issues) == 2
        assert issues[0].identifier == "ENG-1"

    def test_create_issue(self, mock_httpx):
        mock_httpx.Client.return_value.__enter__.return_value.post.return_value = _make_response({
            "issueCreate": {
                "success": True,
                "issue": {
                    "id": "new-1", "identifier": "ENG-99", "title": "New ticket",
                    "description": "Created by Support Buddy",
                    "state": {"name": "Backlog"},
                    "priority": 1, "url": "https://linear.app/team/ENG-99",
                },
            }
        })

        client = LinearClient(api_key="test-key")
        issue = client.create_issue("team-1", "New ticket", "Created by Support Buddy")

        assert issue.identifier == "ENG-99"
        assert issue.title == "New ticket"

    def test_add_comment(self, mock_httpx):
        mock_httpx.Client.return_value.__enter__.return_value.post.return_value = _make_response({
            "commentCreate": {
                "success": True,
                "comment": {"id": "comment-1"},
            }
        })

        client = LinearClient(api_key="test-key")
        comment_id = client.add_comment("issue-1", "Analysis from Support Buddy")

        assert comment_id == "comment-1"

    def test_api_error_raises(self, mock_httpx):
        resp = MagicMock()
        resp.json.return_value = {"errors": [{"message": "Unauthorized"}]}
        resp.raise_for_status.return_value = None
        mock_httpx.Client.return_value.__enter__.return_value.post.return_value = resp

        client = LinearClient(api_key="test-key")
        with pytest.raises(RuntimeError, match="Linear API error"):
            client.get_issue("bad-id")
