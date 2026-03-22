"""GitHub integration — issue/PR reference via REST API."""

from src.integrations.github.client import GitHubClient, GitHubIssue

__all__ = ["GitHubClient", "GitHubIssue"]
