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


@app.command()
def analyze(
    inquiry: str = typer.Argument(..., help="Customer inquiry text to analyze"),
    knowledge_dir: str = typer.Option(None, "--kb", help="Path to knowledge directory"),
):
    """Analyze a customer inquiry and get TSE guidance."""
    engine = _get_engine(knowledge_dir)
    analyzer = InquiryAnalyzer(engine)
    result = analyzer.classify(inquiry)

    # Header
    severity_color = {
        "low": "green", "medium": "yellow", "high": "red", "critical": "bold red"
    }.get(result.severity.value, "white")

    console.print()
    console.print(Panel(
        f"[bold]{result.summary}[/bold]\n\n"
        f"Category: [cyan]{result.category.value}[/cyan]  |  "
        f"Severity: [{severity_color}]{result.severity.value.upper()}[/{severity_color}]  |  "
        f"Confidence: {result.confidence:.0%}",
        title="[bold blue]Inquiry Analysis[/bold blue]",
        border_style="blue",
    ))

    # Checklist
    console.print()
    console.print("[bold]Checklist:[/bold]")
    for i, item in enumerate(result.checklist, 1):
        console.print(f"  {i}. {item}")

    # Follow-up questions
    console.print()
    console.print("[bold]Suggested Follow-up Questions:[/bold]")
    for i, q in enumerate(result.follow_up_questions, 1):
        console.print(f"  {i}. {q}")

    # Relevant articles
    if result.relevant_articles:
        console.print()
        table = Table(title="Relevant Knowledge Base Articles")
        table.add_column("Title", style="cyan")
        table.add_column("Category", style="green")
        table.add_column("Score", justify="right")

        for article in result.relevant_articles[:5]:
            table.add_row(
                article.title,
                article.category,
                f"{article.score:.2f}",
            )
        console.print(table)

    # Escalation warning
    if result.confidence < 0.6:
        console.print()
        console.print(
            "[bold yellow]Low confidence — consider escalating to a senior TSE.[/bold yellow]"
        )


@app.command()
def logs(
    log_input: str = typer.Argument(
        ..., help="Log content or path to a log file"
    ),
    threshold: int = typer.Option(5000, "--threshold", "-t", help="Slow operation threshold (ms)"),
    knowledge_dir: str = typer.Option(None, "--kb", help="Path to knowledge directory"),
):
    """Parse and analyze log data."""
    # Check if input is a file path
    log_path = Path(log_input)
    if log_path.is_file():
        raw_logs = log_path.read_text(encoding="utf-8")
    else:
        raw_logs = log_input

    parser = LogParser()
    events = parser.parse(raw_logs)

    if not events:
        console.print("[yellow]No log events could be parsed from the input.[/yellow]")
        raise typer.Exit(1)

    # Summary
    summary = parser.generate_text_summary(events)
    console.print()
    console.print(Panel(summary, title="[bold blue]Log Analysis[/bold blue]", border_style="blue"))

    # Error codes — look up in knowledge base
    error_codes = parser.extract_error_codes(events)
    if error_codes:
        engine = _get_engine(knowledge_dir)
        console.print()
        console.print("[bold]Error Code Details:[/bold]")
        for code in error_codes:
            results = engine.search(code, top_k=1, category="error_code")
            if results:
                console.print(f"\n  [cyan]{code}[/cyan]: {results[0].title}")
                # Show first ~200 chars of content
                content_preview = results[0].content[:200]
                console.print(f"  {content_preview}...")
            else:
                console.print(f"\n  [cyan]{code}[/cyan]: No documentation found")


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
