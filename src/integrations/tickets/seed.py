"""Create and remove clearly labelled test tickets in a sandbox ticket tool.

Test data only: every created ticket carries the `seed` label, and cleanup deletes only
tickets carrying it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from src.core.models import Severity
from src.eval.cases import GoldenCase

SEED_LABEL = "seed"
MAX_TITLE = 80

# Linear priorities: 1 urgent, 2 high, 3 medium, 4 low
_PRIORITY = {Severity.CRITICAL: 1, Severity.HIGH: 2, Severity.MEDIUM: 3, Severity.LOW: 4}
_FIRST_SENTENCE = re.compile(r"^(.{15,}?[.?!])(?:\s|$)")


@dataclass(frozen=True)
class SeedTicket:
    title: str
    description: str
    labels: tuple[str, ...]
    priority: int


@dataclass
class SeedResult:
    created: list[str] = field(default_factory=list)  # ticket keys
    would_create: list[str] = field(default_factory=list)  # titles, dry run only
    skipped: int = 0


class LinearAdmin(Protocol):
    def get_teams(self) -> list[dict[str, str]]: ...
    def list_labels(self, team_id: str) -> list[dict[str, str]]: ...
    def create_label(self, team_id: str, name: str, color: str = ...) -> str: ...
    def create_issue(
        self,
        team_id: str,
        title: str,
        description: str = ...,
        priority: int = ...,
        label_ids: list[str] | None = ...,
    ) -> Any: ...
    def list_issues(
        self, updated_after: str | None = ..., team_key: str | None = ..., page_size: int = ...
    ) -> list[Any]: ...
    def delete_issue(self, issue_id: str) -> None: ...


def title_from_inquiry(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    sentence = _FIRST_SENTENCE.match(collapsed)
    title = sentence.group(1) if sentence else collapsed
    title = re.sub(r"[.,;:]+$", "", title)
    if len(title) > MAX_TITLE:
        cut = title[: MAX_TITLE + 1]
        space = cut.rfind(" ")
        title = cut[: space if space > 20 else MAX_TITLE].rstrip() + "…"
    return title


def seed_tickets_from_cases(cases: list[GoldenCase]) -> list[SeedTicket]:
    tickets = []
    for c in cases:
        description = c.inquiry
        if c.log_text.strip():
            description += f"\n\n```\n{c.log_text.strip()}\n```"
        labels = [SEED_LABEL]
        if c.customer.plan != "unknown":
            labels.append(f"plan:{c.customer.plan}")
        tickets.append(
            SeedTicket(
                title=title_from_inquiry(c.inquiry),
                description=description,
                labels=tuple(labels),
                priority=_PRIORITY[c.expected.min_severity],
            )
        )
    return tickets


def _team_id(admin: LinearAdmin, team_key: str) -> str:
    teams = admin.get_teams()
    for team in teams:
        if team.get("key") == team_key:
            return team["id"]
    available = ", ".join(t.get("key", "?") for t in teams) or "none"
    raise ValueError(f"team {team_key} not found; available: {available}")


def _is_seed(labels: list[str]) -> bool:
    return SEED_LABEL in {label.lower() for label in labels}


def seed_linear(
    admin: LinearAdmin,
    team_key: str,
    tickets: list[SeedTicket],
    *,
    dry_run: bool = False,
    limit: int | None = None,
) -> SeedResult:
    """Create the tickets that do not exist yet (matched by title among seeded issues)."""
    team_id = _team_id(admin, team_key)
    existing = {i.title for i in admin.list_issues(team_key=team_key) if _is_seed(i.labels)}
    result = SeedResult()

    todo = []
    for ticket in tickets:
        if ticket.title in existing:
            result.skipped += 1
        else:
            todo.append(ticket)
    if limit is not None:
        todo = todo[:limit]

    if dry_run:
        result.would_create = [t.title for t in todo]
        return result

    known = {label["name"].lower(): label["id"] for label in admin.list_labels(team_id)}
    for name in {label for t in todo for label in t.labels}:
        if name.lower() not in known:
            known[name.lower()] = admin.create_label(team_id, name)

    for ticket in todo:
        issue = admin.create_issue(
            team_id,
            ticket.title,
            description=ticket.description,
            priority=ticket.priority,
            label_ids=[known[label.lower()] for label in ticket.labels],
        )
        result.created.append(issue.identifier)
    return result


def cleanup_linear(admin: LinearAdmin, team_key: str, *, dry_run: bool = False) -> list[str]:
    """Delete only issues carrying the seed label. Returns their keys."""
    _team_id(admin, team_key)  # fail early on a wrong team
    seeded = [i for i in admin.list_issues(team_key=team_key) if _is_seed(i.labels)]
    if not dry_run:
        for issue in seeded:
            admin.delete_issue(issue.id)
    return [i.identifier for i in seeded]
