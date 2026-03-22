"""Linear API client for ticket management."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

LINEAR_API_URL = "https://api.linear.app/graphql"


@dataclass
class LinearIssue:
    id: str
    identifier: str  # e.g., "ENG-123"
    title: str
    description: str = ""
    state: str = ""
    priority: int = 0
    assignee: str = ""
    labels: list[str] = field(default_factory=list)
    url: str = ""


class LinearClient:
    """Client for Linear GraphQL API."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.getenv("LINEAR_API_KEY", "")
        if not self._api_key:
            raise ValueError("LINEAR_API_KEY is not set")
        self._headers = {
            "Authorization": self._api_key,
            "Content-Type": "application/json",
        }

    def _query(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        with httpx.Client() as client:
            response = client.post(
                LINEAR_API_URL,
                headers=self._headers,
                json={"query": query, "variables": variables or {}},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            if "errors" in data:
                raise RuntimeError(f"Linear API error: {data['errors']}")
            return data.get("data", {})

    def get_issue(self, issue_id: str) -> LinearIssue:
        """Fetch a single issue by ID or identifier."""
        query = """
        query GetIssue($id: String!) {
            issue(id: $id) {
                id
                identifier
                title
                description
                state { name }
                priority
                assignee { name }
                labels { nodes { name } }
                url
            }
        }
        """
        data = self._query(query, {"id": issue_id})
        issue = data.get("issue", {})
        return self._parse_issue(issue)

    def search_issues(self, search_text: str, limit: int = 10) -> list[LinearIssue]:
        """Search issues by text."""
        query = """
        query SearchIssues($filter: IssueFilter, $first: Int) {
            issues(filter: $filter, first: $first) {
                nodes {
                    id
                    identifier
                    title
                    description
                    state { name }
                    priority
                    assignee { name }
                    labels { nodes { name } }
                    url
                }
            }
        }
        """
        variables = {
            "filter": {
                "or": [
                    {"title": {"containsIgnoreCase": search_text}},
                    {"description": {"containsIgnoreCase": search_text}},
                ]
            },
            "first": limit,
        }
        data = self._query(query, variables)
        nodes = data.get("issues", {}).get("nodes", [])
        return [self._parse_issue(n) for n in nodes]

    def create_issue(
        self,
        team_id: str,
        title: str,
        description: str = "",
        priority: int = 0,
        label_ids: list[str] | None = None,
    ) -> LinearIssue:
        """Create a new issue."""
        query = """
        mutation CreateIssue($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    identifier
                    title
                    description
                    state { name }
                    priority
                    url
                }
            }
        }
        """
        input_data: dict[str, Any] = {
            "teamId": team_id,
            "title": title,
            "description": description,
            "priority": priority,
        }
        if label_ids:
            input_data["labelIds"] = label_ids

        data = self._query(query, {"input": input_data})
        result = data.get("issueCreate", {})
        if not result.get("success"):
            raise RuntimeError("Failed to create Linear issue")
        return self._parse_issue(result.get("issue", {}))

    def add_comment(self, issue_id: str, body: str) -> str:
        """Add a comment to an issue. Returns comment ID."""
        query = """
        mutation AddComment($input: CommentCreateInput!) {
            commentCreate(input: $input) {
                success
                comment { id }
            }
        }
        """
        data = self._query(query, {"input": {"issueId": issue_id, "body": body}})
        result = data.get("commentCreate", {})
        if not result.get("success"):
            raise RuntimeError("Failed to add comment")
        return result.get("comment", {}).get("id", "")

    def get_teams(self) -> list[dict[str, str]]:
        """List all teams."""
        query = """
        query { teams { nodes { id name key } } }
        """
        data = self._query(query)
        return data.get("teams", {}).get("nodes", [])

    def _parse_issue(self, raw: dict[str, Any]) -> LinearIssue:
        return LinearIssue(
            id=raw.get("id", ""),
            identifier=raw.get("identifier", ""),
            title=raw.get("title", ""),
            description=raw.get("description", ""),
            state=raw.get("state", {}).get("name", "") if raw.get("state") else "",
            priority=raw.get("priority", 0),
            assignee=raw.get("assignee", {}).get("name", "") if raw.get("assignee") else "",
            labels=[l["name"] for l in raw.get("labels", {}).get("nodes", [])] if raw.get("labels") else [],
            url=raw.get("url", ""),
        )
