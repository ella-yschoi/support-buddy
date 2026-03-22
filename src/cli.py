"""CLI interface for Support Buddy."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from src.config import ANTHROPIC_API_KEY, KNOWLEDGE_DIR
from src.core.analyzer.inquiry import InquiryAnalyzer
from src.core.analyzer.log_parser import LogParser
from src.core.knowledge.engine import KnowledgeEngine
from src.core.models import InquiryResult

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
            "[bold yellow]Low confidence — consider escalating to a senior TSE.[/bold yellow]"
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

    # First analyze
    from src.core.analyzer.ai_inquiry import AIInquiryAnalyzer
    from src.core.responder.drafter import ResponseDrafter

    console.print("[dim]Analyzing inquiry...[/dim]")
    analyzer = AIInquiryAnalyzer(engine)
    analysis = analyzer.analyze(inquiry)

    _display_analysis(analysis, title="Analysis")

    # Then draft response
    console.print()
    console.print("[dim]Generating response draft...[/dim]")
    drafter = ResponseDrafter(engine)
    response = drafter.draft(inquiry, analysis)

    # Display draft
    escalation = "[bold red]YES — Escalation Recommended[/bold red]" if response.needs_escalation else "[green]No[/green]"

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
            title=f"[cyan]{i}. {r.title}[/cyan] ({r.category}) — score: {r.score:.2f}",
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


if __name__ == "__main__":
    app()
