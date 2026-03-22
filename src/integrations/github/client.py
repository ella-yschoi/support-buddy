"""GitHub API client for issue/PR reference."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx

GITHUB_API_URL = "https://api.github.com"


@dataclass
class GitHubIssue:
    number: int
    title: str
    body: str = ""
    state: str = ""
    labels: list[str] = field(default_factory=list)
    url: str = ""
    is_pull_request: bool = False


class GitHubClient:
    """Client for GitHub REST API."""

    def __init__(self, token: str | None = None, owner: str = "", repo: str = ""):
        self._token = token or os.getenv("GITHUB_TOKEN", "")
        if not self._token:
            raise ValueError("GITHUB_TOKEN is not set")
        self._owner = owner or os.getenv("GITHUB_OWNER", "")
        self._repo = repo or os.getenv("GITHUB_REPO", "")
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        with httpx.Client() as client:
            response = client.get(
                f"{GITHUB_API_URL}{path}",
                headers=self._headers,
                params=params or {},
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    def _post(self, path: str, json_data: dict[str, Any]) -> Any:
        with httpx.Client() as client:
            response = client.post(
                f"{GITHUB_API_URL}{path}",
                headers=self._headers,
                json=json_data,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    def get_issue(self, number: int) -> GitHubIssue:
        """Get a single issue or PR by number."""
        data = self._get(f"/repos/{self._owner}/{self._repo}/issues/{number}")
        return self._parse_issue(data)

    def search_issues(self, query: str, limit: int = 10) -> list[GitHubIssue]:
        """Search issues and PRs in the repository."""
        search_query = f"{query} repo:{self._owner}/{self._repo}"
        data = self._get("/search/issues", {"q": search_query, "per_page": limit})
        items = data.get("items", [])
        return [self._parse_issue(item) for item in items]

    def search_related_issues(
        self, error_code: str, limit: int = 5
    ) -> list[GitHubIssue]:
        """Search for issues related to a specific error code."""
        return self.search_issues(error_code, limit=limit)

    def add_comment(self, issue_number: int, body: str) -> int:
        """Add a comment to an issue. Returns comment ID."""
        data = self._post(
            f"/repos/{self._owner}/{self._repo}/issues/{issue_number}/comments",
            {"body": body},
        )
        return data.get("id", 0)

    def _parse_issue(self, raw: dict[str, Any]) -> GitHubIssue:
        labels = [l.get("name", "") for l in raw.get("labels", [])]
        return GitHubIssue(
            number=raw.get("number", 0),
            title=raw.get("title", ""),
            body=raw.get("body", "") or "",
            state=raw.get("state", ""),
            labels=labels,
            url=raw.get("html_url", ""),
            is_pull_request="pull_request" in raw,
        )
