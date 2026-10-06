"""CLI interface for Support Buddy."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from src.config import ANTHROPIC_API_KEY, BRIEFING_DB_PATH, KNOWLEDGE_DIR, LINEAR_API_KEY
from src.core.analyzer.inquiry import InquiryAnalyzer
from src.core.analyzer.log_parser import LogParser
from src.core.briefing.factory import build_local_builder
from src.core.briefing.store import BriefingStore
from src.core.briefing.watch import run_watch
from src.core.exceptions import ConfigError, TicketSourceError
from src.core.knowledge.engine import KnowledgeEngine
from src.core.models import InquiryResult
from src.eval.demo import generate_demo_briefings, write_demo_file
from src.eval.run import (
    run_claude_eval,
    run_local_eval,
    select_registries,
    write_reports,
)

app = typer.Typer(
    name="support-buddy",
    help="AI-powered support tool for Technical Support Engineers",
)
console = Console()

# Module-level engine (lazy init)
_engine: KnowledgeEngine | None = None


def _get_engine(knowledge_dir: str | None = None) -> KnowledgeEngine:
    global _engine
    if _engine is None:
        _engine = KnowledgeEngine()
        kb_path = Path(knowledge_dir) if knowledge_dir else KNOWLEDGE_DIR
        if kb_path.is_dir():
            count = _engine.ingest_directory(kb_path)
            console.print(f"[dim]Loaded {count} knowledge chunks from {kb_path}[/dim]")
        else:
            console.print(f"[yellow]Warning: Knowledge directory not found: {kb_path}[/yellow]")
    return _engine


def _display_analysis(result: InquiryResult, title: str = "Inquiry Analysis") -> None:
    """Display an InquiryResult with Rich formatting."""
    severity_color = {
        "low": "green", "medium": "yellow", "high": "red", "critical": "bold red"
    }.get(result.severity.value, "white")

    console.print()
    console.print(Panel(
        f"[bold]{result.summary}[/bold]\n\n"
        f"Category: [cyan]{result.category.value}[/cyan]  |  "
        f"Severity: [{severity_color}]{result.severity.value.upper()}[/{severity_color}]  |  "
        f"Confidence: {result.confidence:.0%}",
        title=f"[bold blue]{title}[/bold blue]",
        border_style="blue",
    ))

    console.print()
    console.print("[bold]Checklist:[/bold]")
    for i, item in enumerate(result.checklist, 1):
        console.print(f"  {i}. {item}")

    console.print()
    console.print("[bold]Suggested Follow-up Questions:[/bold]")
    for i, q in enumerate(result.follow_up_questions, 1):
        console.print(f"  {i}. {q}")

    if result.relevant_articles:
        console.print()
        table = Table(title="Relevant Knowledge Base Articles")
        table.add_column("Title", style="cyan")
        table.add_column("Category", style="green")
        table.add_column("Score", justify="right")

        for article in result.relevant_articles[:5]:
            table.add_row(article.title, article.category, f"{article.score:.2f}")
        console.print(table)

    if result.confidence < 0.6:
        console.print()
        console.print(
            "[bold yellow]Low confidence - consider escalating to a senior TSE.[/bold yellow]"
        )


@app.command()
def analyze(
    inquiry: str = typer.Argument(..., help="Customer inquiry text to analyze"),
    ai: bool = typer.Option(False, "--ai", help="Use Claude AI for enhanced analysis"),
    knowledge_dir: str = typer.Option(None, "--kb", help="Path to knowledge directory"),
):
    """Analyze a customer inquiry and get TSE guidance."""
    engine = _get_engine(knowledge_dir)

    if ai:
        if not ANTHROPIC_API_KEY:
            console.print("[red]Error: ANTHROPIC_API_KEY not set. Use without --ai or set the key.[/red]")
            raise typer.Exit(1)
        from src.core.analyzer.ai_inquiry import AIInquiryAnalyzer
        analyzer = AIInquiryAnalyzer(engine)
        console.print("[dim]Using Claude AI for analysis...[/dim]")
        result = analyzer.analyze(inquiry)
        _display_analysis(result, title="AI-Powered Inquiry Analysis")
    else:
        analyzer = InquiryAnalyzer(engine)
        result = analyzer.classify(inquiry)
        _display_analysis(result)


@app.command()
def logs(
    log_input: str = typer.Argument(..., help="Log content or path to a log file"),
    ai: bool = typer.Option(False, "--ai", help="Use Claude AI for enhanced log analysis"),
    threshold: int = typer.Option(5000, "--threshold", "-t", help="Slow operation threshold (ms)"),
    knowledge_dir: str = typer.Option(None, "--kb", help="Path to knowledge directory"),
):
    """Parse and analyze log data."""
    log_path = Path(log_input)
    if log_path.is_file():
        raw_logs = log_path.read_text(encoding="utf-8")
    else:
        raw_logs = log_input

    if ai:
        if not ANTHROPIC_API_KEY:
            console.print("[red]Error: ANTHROPIC_API_KEY not set. Use without --ai or set the key.[/red]")
            raise typer.Exit(1)
        from src.core.analyzer.log_analyzer import AILogAnalyzer
        engine = _get_engine(knowledge_dir)
        ai_analyzer = AILogAnalyzer(engine)
        console.print("[dim]Using Claude AI for log analysis...[/dim]")
        insight = ai_analyzer.analyze(raw_logs)

        console.print()
        console.print(Panel(
            f"[bold]Summary:[/bold]\n{insight.summary}\n\n"
            f"[bold]Root Cause Hypothesis:[/bold]\n{insight.root_cause_hypothesis}",
            title="[bold blue]AI Log Analysis[/bold blue]",
            border_style="blue",
        ))

        if insight.anomalies:
            console.print()
            console.print("[bold]Anomalies Detected:[/bold]")
            for a in insight.anomalies:
                console.print(f"  - {a}")

        if insight.errors:
            console.print()
            console.print(f"[bold]{len(insight.errors)} Error(s):[/bold]")
            for e in insight.errors:
                console.print(f"  [{e.timestamp}] {e.message}")

        if insight.slow_operations:
            console.print()
            console.print(f"[bold]{len(insight.slow_operations)} Slow Operation(s):[/bold]")
            for s in insight.slow_operations:
                dur = s.metadata.get("duration_ms", "?")
                console.print(f"  [{s.timestamp}] {s.message} ({dur}ms)")
    else:
        parser = LogParser()
        events = parser.parse(raw_logs)

        if not events:
            console.print("[yellow]No log events could be parsed from the input.[/yellow]")
            raise typer.Exit(1)

        summary = parser.generate_text_summary(events)
        console.print()
        console.print(Panel(summary, title="[bold blue]Log Analysis[/bold blue]", border_style="blue"))

        error_codes = parser.extract_error_codes(events)
        if error_codes:
            engine = _get_engine(knowledge_dir)
            console.print()
            console.print("[bold]Error Code Details:[/bold]")
            for code in error_codes:
                results = engine.search(code, top_k=1, category="error_code")
                if results:
                    console.print(f"\n  [cyan]{code}[/cyan]: {results[0].title}")
                    console.print(f"  {results[0].content[:200]}...")
                else:
                    console.print(f"\n  [cyan]{code}[/cyan]: No documentation found")


@app.command()
def draft(
    inquiry: str = typer.Argument(..., help="Customer inquiry text"),
    knowledge_dir: str = typer.Option(None, "--kb", help="Path to knowledge directory"),
):
    """Generate a draft response for a customer inquiry (requires AI)."""
    if not ANTHROPIC_API_KEY:
        console.print("[red]Error: ANTHROPIC_API_KEY not set.[/red]")
        raise typer.Exit(1)

    engine = _get_engine(knowledge_dir)

    from src.core.analyzer.ai_inquiry import AIInquiryAnalyzer
    from src.core.responder.drafter import ResponseDrafter

    console.print("[dim]Analyzing inquiry...[/dim]")
    analyzer = AIInquiryAnalyzer(engine)
    analysis = analyzer.analyze(inquiry)

    _display_analysis(analysis, title="Analysis")

    console.print()
    console.print("[dim]Generating response draft...[/dim]")
    drafter = ResponseDrafter(engine)
    response = drafter.draft(inquiry, analysis)

    escalation = "[bold red]YES - Escalation Recommended[/bold red]" if response.needs_escalation else "[green]No[/green]"

    console.print()
    console.print(Panel(
        response.body,
        title=f"[bold green]Draft Response[/bold green] (confidence: {response.confidence:.0%})",
        border_style="green",
    ))

    console.print()
    console.print(f"  Needs escalation: {escalation}")

    if response.suggested_internal_note:
        console.print()
        console.print(Panel(
            response.suggested_internal_note,
            title="[bold yellow]Internal Note (not sent to customer)[/bold yellow]",
            border_style="yellow",
        ))

    if response.citations:
        console.print()
        console.print("[bold]Sources:[/bold]")
        for c in response.citations:
            console.print(f"  - {c.title} ({c.category})")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    category: str = typer.Option(None, "--category", "-c", help="Filter by category"),
    top_k: int = typer.Option(5, "--top", "-k", help="Number of results"),
    knowledge_dir: str = typer.Option(None, "--kb", help="Path to knowledge directory"),
):
    """Search the knowledge base."""
    engine = _get_engine(knowledge_dir)
    results = engine.search(query, top_k=top_k, category=category)

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        raise typer.Exit(0)

    console.print()
    for i, r in enumerate(results, 1):
        console.print(Panel(
            f"{r.content[:300]}{'...' if len(r.content) > 300 else ''}",
            title=f"[cyan]{i}. {r.title}[/cyan] ({r.category}) - score: {r.score:.2f}",
            border_style="dim",
        ))


@app.command()
def ingest(
    path: str = typer.Argument(..., help="Path to a directory or file to ingest"),
):
    """Ingest knowledge documents into the knowledge base."""
    p = Path(path)
    engine = _get_engine()

    if p.is_dir():
        count = engine.ingest_directory(p)
        console.print(f"[green]Ingested {count} document chunks from {p}[/green]")
    elif p.is_file():
        count = engine.ingest_file(p)
        console.print(f"[green]Ingested {count} document chunks from {p}[/green]")
    else:
        console.print(f"[red]Path not found: {p}[/red]")
        raise typer.Exit(1)


@app.command(name="eval")
def eval_command(
    pipeline: str = typer.Option("local", help="'local' (free baseline) or 'claude' (paid API)"),
    configs: Path | None = typer.Option(None, help="Model configs YAML (claude pipeline)"),
    names: str | None = typer.Option(None, help="Comma-separated config names to compare"),
    out: Path = typer.Option(Path("reports/eval"), help="Directory for the report files"),
    yes: bool = typer.Option(False, "--yes", help="Skip the cost confirmation"),
) -> None:
    """Run the golden set and write a Markdown + JSON eval report."""
    if pipeline == "local":
        runs = run_local_eval()
    elif pipeline == "claude":
        if not ANTHROPIC_API_KEY:
            console.print("[red]ANTHROPIC_API_KEY is not set[/red]")
            raise typer.Exit(1)
        try:
            registries = select_registries(configs, names.split(",") if names else None)
        except ConfigError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1) from exc
        console.print(
            f"This calls the paid Claude API (about 2 calls per case) for "
            f"{len(registries)} config(s): {', '.join(r.name for r in registries)}."
        )
        if not yes and not typer.confirm("Continue?"):
            raise typer.Exit(1)
        runs = run_claude_eval(registries, ANTHROPIC_API_KEY)
    else:
        console.print(f"[red]Unknown pipeline: {pipeline}[/red]")
        raise typer.Exit(1)

    md_path, json_path = write_reports(runs, out)
    for run in runs:
        m = run.metrics
        console.print(
            f"[bold]{run.name}[/bold]: auto-resolvable {m.auto_resolvable_rate:.1%} "
            f"(n={m.n}), unsafe passes {m.unsafe_pass_count}, "
            f"routing agreement {m.routing_agreement:.1%}"
        )
    console.print(f"Report: {md_path}\nData:   {json_path}")


@app.command(name="demo-data")
def demo_data_command(
    out: Path = typer.Option(
        Path("web/public/demo/briefings.json"), help="Where to write the pre-computed briefings"
    ),
) -> None:
    """Pre-compute briefings for the public demo (free, no API calls)."""
    briefings = generate_demo_briefings()
    path = write_demo_file(briefings, out)
    console.print(f"Wrote {len(briefings)} demo briefings to {path}")


def build_source(name: str, team: str | None):  # noqa: ANN201
    """The ticket source for a tool name. Only tools that are actually connected are listed."""
    from src.integrations.linear.client import LinearClient
    from src.integrations.tickets.linear import LinearTicketSource

    if name == "linear":
        return LinearTicketSource(LinearClient(), team_key=team)
    raise ValueError(f"unknown ticket source: {name}")


SUPPORTED_SOURCES = ("linear",)


def make_linear_admin():  # noqa: ANN201
    from src.integrations.linear.client import LinearClient

    return LinearClient()


def _require_linear_key() -> None:
    if not LINEAR_API_KEY:
        console.print("[red]LINEAR_API_KEY is not set. Put it in .env[/red]")
        raise typer.Exit(1)


@app.command(name="seed-linear")
def seed_linear_command(
    team: str = typer.Option(..., help="Linear team key of the SANDBOX workspace, e.g. SUP"),
    limit: int | None = typer.Option(None, help="Create at most this many tickets"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be created only"),
    yes: bool = typer.Option(False, "--yes", help="Confirm writing to the workspace shown"),
) -> None:
    """Create labelled test tickets from the golden set in a sandbox Linear workspace."""
    from src.eval.cases import DEFAULT_GOLDEN_DIR, load_golden
    from src.integrations.tickets.seed import seed_linear, seed_tickets_from_cases

    _require_linear_key()
    admin = make_linear_admin()
    tickets = seed_tickets_from_cases(load_golden(DEFAULT_GOLDEN_DIR))
    count = min(len(tickets), limit) if limit is not None else len(tickets)
    console.print(f"Target workspace: [bold]{admin.get_organization()}[/bold], team {team}")
    if not yes and not dry_run:
        console.print(
            f"Nothing written. Up to {count} labelled test tickets would be created. "
            "Check the workspace above is a sandbox, then re-run with --yes."
        )
        raise typer.Exit(1)
    try:
        result = seed_linear(admin, team, tickets, dry_run=dry_run, limit=limit)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    if dry_run:
        console.print(f"Dry run: would create {len(result.would_create)}, {result.skipped} exist")
    else:
        keys = ", ".join(result.created)
        console.print(f"Created {len(result.created)} ({keys}); {result.skipped} existed")


@app.command(name="cleanup-linear")
def cleanup_linear_command(
    team: str = typer.Option(..., help="Linear team key of the SANDBOX workspace"),
    dry_run: bool = typer.Option(False, "--dry-run", help="List what would be deleted only"),
    yes: bool = typer.Option(False, "--yes", help="Confirm deleting the seed-labelled tickets"),
) -> None:
    """Delete the tickets labelled `seed` (and nothing else) from the sandbox workspace."""
    from src.integrations.tickets.seed import cleanup_linear

    _require_linear_key()
    admin = make_linear_admin()
    console.print(f"Target workspace: [bold]{admin.get_organization()}[/bold], team {team}")
    if not yes and not dry_run:
        console.print("Nothing deleted. Re-run with --yes to delete tickets labelled 'seed'.")
        raise typer.Exit(1)
    try:
        deleted = cleanup_linear(admin, team, dry_run=dry_run)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    verb = "Would delete" if dry_run else "Deleted"
    console.print(f"{verb} {len(deleted)}: {', '.join(deleted) or 'none'}")


@app.command(name="watch")
def watch_command(
    source: str = typer.Option("linear", help="Ticket tool to read from"),
    team: str | None = typer.Option(None, help="Only this team (Linear team key, e.g. SUP)"),
    label: str | None = typer.Option(None, help="Only tickets carrying this label"),
    interval: float = typer.Option(60.0, help="Seconds between polls"),
    once: bool = typer.Option(False, "--once", help="Poll one time and exit"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be created only"),
    include_closed: bool = typer.Option(False, "--include-closed", help="Also brief closed"),
) -> None:
    """Read new tickets from a ticket tool and prepare a briefing for each (read-only)."""
    if source not in SUPPORTED_SOURCES:
        supported = ", ".join(SUPPORTED_SOURCES)
        console.print(f"[red]Unknown source '{source}'. Supported: {supported}[/red]")
        raise typer.Exit(1)
    if source == "linear" and not LINEAR_API_KEY:
        console.print("[red]LINEAR_API_KEY is not set. Put it in .env[/red]")
        raise typer.Exit(1)

    import tempfile

    from src.integrations.tickets.cursors import CursorStore

    ticket_source = build_source(source, team)
    cursor_key = f"{source}:{team or 'all'}"
    console.print(
        f"Watching {source} (team: {team or 'all'}, label: {label or 'any'}) "
        f"{'once' if once else f'every {interval:g}s'}{' [dry run]' if dry_run else ''}"
    )
    with tempfile.TemporaryDirectory() as tmp:
        engine = KnowledgeEngine(persist_dir=tmp)
        engine.ingest_directory(KNOWLEDGE_DIR)
        try:
            run_watch(
                ticket_source,
                build_local_builder(engine),
                BriefingStore(BRIEFING_DB_PATH),
                CursorStore(BRIEFING_DB_PATH),
                interval=interval,
                once=once,
                cursor_key=cursor_key,
                label=label,
                include_closed=include_closed,
                dry_run=dry_run,
                report=console.print,
            )
        except TicketSourceError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1) from exc


if __name__ == "__main__":
    app()
