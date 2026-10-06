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


class TestLinearAdminCalls:
    def _post(self, mock_httpx):
        return mock_httpx.Client.return_value.__enter__.return_value.post

    def test_get_organization(self, mock_httpx):
        self._post(mock_httpx).return_value = _make_response({"organization": {"name": "sandbox"}})
        assert LinearClient(api_key="k").get_organization() == "sandbox"

    def test_list_labels_keeps_team_and_workspace_labels_only(self, mock_httpx):
        self._post(mock_httpx).return_value = _make_response({
            "issueLabels": {"nodes": [
                {"id": "1", "name": "mine", "team": {"id": "t1"}},
                {"id": "2", "name": "workspace", "team": None},
                {"id": "3", "name": "other team", "team": {"id": "t2"}},
            ]}
        })
        labels = LinearClient(api_key="k").list_labels("t1")
        assert [l["name"] for l in labels] == ["mine", "workspace"]

    def test_create_label_returns_the_new_id(self, mock_httpx):
        post = self._post(mock_httpx)
        post.return_value = _make_response({
            "issueLabelCreate": {"success": True, "issueLabel": {"id": "lab-9"}}
        })
        assert LinearClient(api_key="k").create_label("t1", "seed") == "lab-9"
        sent = post.call_args.kwargs["json"]["variables"]["input"]
        assert sent["name"] == "seed" and sent["teamId"] == "t1"

    def test_create_label_failure_raises(self, mock_httpx):
        self._post(mock_httpx).return_value = _make_response({"issueLabelCreate": {"success": False}})
        with pytest.raises(RuntimeError, match="seed"):
            LinearClient(api_key="k").create_label("t1", "seed")

    def test_delete_issue_succeeds_and_fails_loudly(self, mock_httpx):
        post = self._post(mock_httpx)
        post.return_value = _make_response({"issueDelete": {"success": True}})
        LinearClient(api_key="k").delete_issue("i1")
        post.return_value = _make_response({"issueDelete": {"success": False}})
        with pytest.raises(RuntimeError, match="i1"):
            LinearClient(api_key="k").delete_issue("i1")

    def test_list_issues_sends_the_filters_and_parses_timestamps(self, mock_httpx):
        post = self._post(mock_httpx)
        post.return_value = _make_response({"issues": {
            "nodes": [{
                "id": "1", "identifier": "SUP-1", "title": "T", "description": "d",
                "state": {"name": "Todo", "type": "unstarted"}, "priority": 0,
                "labels": {"nodes": []}, "url": "u",
                "createdAt": "2026-10-05T01:00:00.000Z", "updatedAt": "2026-10-05T02:00:00.000Z",
            }],
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        }})
        issues = LinearClient(api_key="k").list_issues(
            updated_after="2026-10-05T00:00:00.000Z", team_key="SUP"
        )
        sent = post.call_args.kwargs["json"]["variables"]["filter"]["and"]
        assert {"updatedAt": {"gt": "2026-10-05T00:00:00.000Z"}} in sent
        assert {"team": {"key": {"eq": "SUP"}}} in sent
        assert issues[0].updated_at == "2026-10-05T02:00:00.000Z"
        assert issues[0].state_type == "unstarted"
