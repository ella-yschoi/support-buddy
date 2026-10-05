"""Tests for seeding and cleaning up labelled test tickets (fake Linear admin API)."""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from src.cli import app
from src.core.models import InquiryCategory, Severity
from src.core.policy.models import AutonomyLevel
from src.core.trust.models import Customer
from src.eval.cases import Expected, GoldenCase
from src.integrations.linear.client import LinearIssue
from src.integrations.tickets.seed import (
    SEED_LABEL,
    cleanup_linear,
    seed_linear,
    seed_tickets_from_cases,
    title_from_inquiry,
)


def case(
    case_id="c1",
    inquiry="Files will not sync. SYNC-002 shows up.",
    plan="pro",
    severity=Severity.MEDIUM,
    log_text="",
) -> GoldenCase:
    return GoldenCase(
        id=case_id,
        inquiry=inquiry,
        customer=Customer(plan=plan),
        expected=Expected(InquiryCategory.SYNC, severity, AutonomyLevel.CONFIRM),
        log_text=log_text,
    )


@dataclass
class FakeAdmin:
    """Just enough of the Linear client for seeding."""

    teams: list[dict] = field(
        default_factory=lambda: [{"id": "team-1", "key": "SUP", "name": "Support"}]
    )
    labels: dict[str, str] = field(default_factory=dict)  # name -> id
    issues: dict[str, LinearIssue] = field(default_factory=dict)
    writes: list[str] = field(default_factory=list)

    def get_teams(self):
        return self.teams

    def get_organization(self):
        return "sandbox-org"

    def list_labels(self, team_id):
        return [{"id": i, "name": n} for n, i in self.labels.items()]

    def create_label(self, team_id, name, color="#6b6f76"):
        self.writes.append(f"label:{name}")
        self.labels[name] = f"label-{len(self.labels) + 1}"
        return self.labels[name]

    def create_issue(self, team_id, title, description="", priority=0, label_ids=None):
        self.writes.append(f"issue:{title}")
        names = [n for n, i in self.labels.items() if i in (label_ids or [])]
        issue = LinearIssue(
            id=f"issue-{len(self.issues) + 1}",
            identifier=f"SUP-{len(self.issues) + 1}",
            title=title,
            description=description,
            priority=priority,
            labels=names,
            state_type="unstarted",
        )
        self.issues[issue.id] = issue
        return issue

    def list_issues(self, updated_after=None, team_key=None, page_size=50):
        return list(self.issues.values())

    def delete_issue(self, issue_id):
        self.writes.append(f"delete:{issue_id}")
        del self.issues[issue_id]


class TestTitleFromInquiry:
    def test_uses_the_first_sentence(self):
        assert title_from_inquiry("Files will not sync. Please help.") == "Files will not sync"

    def test_keeps_a_question_mark(self):
        assert title_from_inquiry("How do I enable 2FA? Thanks") == "How do I enable 2FA?"

    def test_cuts_long_titles_at_a_word_boundary(self):
        title = title_from_inquiry("word " * 40)
        assert len(title) <= 81 and title.endswith("…")

    def test_collapses_whitespace(self):
        assert title_from_inquiry("  a   b \n c  ") == "a b c"


class TestSeedTicketsFromCases:
    def test_labels_include_seed_and_plan(self):
        (ticket,) = seed_tickets_from_cases([case(plan="enterprise")])
        assert ticket.labels == (SEED_LABEL, "plan:enterprise")

    def test_unknown_plan_gets_no_plan_label(self):
        (ticket,) = seed_tickets_from_cases([case(plan="unknown")])
        assert ticket.labels == (SEED_LABEL,)

    def test_logs_become_a_fenced_block_in_the_description(self):
        (ticket,) = seed_tickets_from_cases([case(log_text='[{"level": "ERROR"}]')])
        assert '```\n[{"level": "ERROR"}]\n```' in ticket.description

    def test_no_logs_means_no_fence(self):
        (ticket,) = seed_tickets_from_cases([case()])
        assert "```" not in ticket.description

    @pytest.mark.parametrize(
        ("severity", "priority"),
        [(Severity.CRITICAL, 1), (Severity.HIGH, 2), (Severity.MEDIUM, 3), (Severity.LOW, 4)],
    )
    def test_priority_follows_expected_severity(self, severity, priority):
        (ticket,) = seed_tickets_from_cases([case(severity=severity)])
        assert ticket.priority == priority


class TestSeedLinear:
    def test_creates_labels_once_and_issues_with_those_labels(self):
        admin = FakeAdmin()
        tickets = seed_tickets_from_cases(
            [case("a", "First problem."), case("b", "Second problem.")]
        )
        result = seed_linear(admin, "SUP", tickets)
        assert len(result.created) == 2
        assert sorted(n for n in admin.labels) == ["plan:pro", SEED_LABEL]
        assert all(set(i.labels) == {SEED_LABEL, "plan:pro"} for i in admin.issues.values())

    def test_reuses_existing_labels_case_insensitively(self):
        admin = FakeAdmin(labels={"Seed": "label-x", "plan:pro": "label-y"})
        seed_linear(admin, "SUP", seed_tickets_from_cases([case()]))
        assert not any(w.startswith("label:") for w in admin.writes)

    def test_running_twice_creates_nothing_the_second_time(self):
        admin = FakeAdmin()
        tickets = seed_tickets_from_cases(
            [case("a", "First problem."), case("b", "Second problem.")]
        )
        seed_linear(admin, "SUP", tickets)
        second = seed_linear(admin, "SUP", tickets)
        assert second.created == []
        assert second.skipped == 2
        assert len(admin.issues) == 2

    def test_dry_run_writes_nothing(self):
        admin = FakeAdmin()
        result = seed_linear(admin, "SUP", seed_tickets_from_cases([case()]), dry_run=True)
        assert admin.writes == []
        assert len(result.would_create) == 1

    def test_limit_caps_how_many_are_created(self):
        admin = FakeAdmin()
        tickets = seed_tickets_from_cases([case(str(i), f"Problem number {i}.") for i in range(5)])
        result = seed_linear(admin, "SUP", tickets, limit=2)
        assert len(result.created) == 2

    def test_unknown_team_is_refused_with_the_available_keys(self):
        with pytest.raises(ValueError, match="SUP"):
            seed_linear(FakeAdmin(), "NOPE", seed_tickets_from_cases([case()]))


class TestCleanup:
    def test_deletes_only_issues_carrying_the_seed_label(self):
        admin = FakeAdmin()
        seed_linear(admin, "SUP", seed_tickets_from_cases([case()]))
        admin.issues["real"] = LinearIssue(
            id="real", identifier="SUP-99", title="Real", labels=["bug"]
        )
        deleted = cleanup_linear(admin, "SUP")
        assert deleted == ["SUP-1"]
        assert list(admin.issues) == ["real"]

    def test_dry_run_deletes_nothing(self):
        admin = FakeAdmin()
        seed_linear(admin, "SUP", seed_tickets_from_cases([case()]))
        before = len(admin.writes)
        assert cleanup_linear(admin, "SUP", dry_run=True) == ["SUP-1"]
        assert len(admin.writes) == before


runner = CliRunner()


class TestSeedCli:
    def test_without_yes_nothing_is_written_and_the_target_is_shown(self):
        admin = FakeAdmin()
        with (
            patch("src.cli.LINEAR_API_KEY", "k"),
            patch("src.cli.make_linear_admin", return_value=admin),
        ):
            result = runner.invoke(app, ["seed-linear", "--team", "SUP", "--limit", "2"])
        assert result.exit_code == 1
        assert "sandbox-org" in result.output and "SUP" in result.output
        assert "--yes" in result.output
        assert admin.writes == []

    def test_with_yes_it_creates_the_tickets(self):
        admin = FakeAdmin()
        with (
            patch("src.cli.LINEAR_API_KEY", "k"),
            patch("src.cli.make_linear_admin", return_value=admin),
        ):
            result = runner.invoke(app, ["seed-linear", "--team", "SUP", "--limit", "2", "--yes"])
        assert result.exit_code == 0, result.output
        assert len(admin.issues) == 2

    def test_cleanup_requires_yes(self):
        admin = FakeAdmin()
        seed_linear(admin, "SUP", seed_tickets_from_cases([case()]))
        with (
            patch("src.cli.LINEAR_API_KEY", "k"),
            patch("src.cli.make_linear_admin", return_value=admin),
        ):
            result = runner.invoke(app, ["cleanup-linear", "--team", "SUP"])
        assert result.exit_code == 1
        assert len(admin.issues) == 1

    def test_team_is_required(self):
        with patch("src.cli.LINEAR_API_KEY", "k"):
            result = runner.invoke(app, ["seed-linear", "--yes"])
        assert result.exit_code != 0


class TestShippedGoldenSet:
    def test_every_golden_case_gets_a_distinct_title(self):
        # Seeding is idempotent by title, so two cases must never collide.
        from src.eval.cases import DEFAULT_GOLDEN_DIR, load_golden

        titles = [t.title for t in seed_tickets_from_cases(load_golden(DEFAULT_GOLDEN_DIR))]
        assert len(titles) == len(set(titles))
