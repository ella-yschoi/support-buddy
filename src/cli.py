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
from src.core.i18n import Language, detect_language, t
from src.core.knowledge.engine import KnowledgeEngine
from src.core.models import InquiryResult

app = typer.Typer(
    name="support-buddy",
    help="AI-powered support tool for Technical Support Engineers",
)
console = Console()

# Module-level engine (lazy init)
_engine: KnowledgeEngine | None = None


def _resolve_lang(lang_option: str, text: str = "") -> Language:
    """Resolve language from --lang option or auto-detect from text."""
    if lang_option == "ko":
        return Language.KO
    if lang_option == "en":
        return Language.EN
    return detect_language(text) if text else Language.EN


def _get_engine(knowledge_dir: str | None = None, lang: Language = Language.EN) -> KnowledgeEngine:
    global _engine
    if _engine is None:
        _engine = KnowledgeEngine()
        kb_path = Path(knowledge_dir) if knowledge_dir else KNOWLEDGE_DIR
        if kb_path.is_dir():
            count = _engine.ingest_directory(kb_path)
            console.print(f"[dim]{t('loaded_chunks', lang).format(count=count, path=kb_path)}[/dim]")
        else:
            console.print(f"[yellow]{t('kb_not_found', lang).format(path=kb_path)}[/yellow]")
    return _engine


def _display_analysis(result: InquiryResult, title: str = "", lang: Language = Language.EN) -> None:
    """Display an InquiryResult with Rich formatting."""
    if not title:
        title = t("inquiry_analysis_title", lang)

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
    console.print(f"[bold]{t('checklist_title', lang)}[/bold]")
    for i, item in enumerate(result.checklist, 1):
        console.print(f"  {i}. {item}")

    console.print()
    console.print(f"[bold]{t('follow_up_title', lang)}[/bold]")
    for i, q in enumerate(result.follow_up_questions, 1):
        console.print(f"  {i}. {q}")

    if result.relevant_articles:
        console.print()
        table = Table(title=t("kb_articles_title", lang))
        table.add_column(t("col_title", lang), style="cyan")
        table.add_column(t("col_category", lang), style="green")
        table.add_column(t("col_score", lang), justify="right")

        for article in result.relevant_articles[:5]:
            table.add_row(article.title, article.category, f"{article.score:.2f}")
        console.print(table)

    if result.confidence < 0.6:
        console.print()
        console.print(
            f"[bold yellow]{t('low_confidence_warning', lang)}[/bold yellow]"
        )


@app.command()
def analyze(
    inquiry: str = typer.Argument(..., help="Customer inquiry text to analyze"),
    ai: bool = typer.Option(False, "--ai", help="Use Claude AI for enhanced analysis"),
    knowledge_dir: str = typer.Option(None, "--kb", help="Path to knowledge directory"),
    lang: str = typer.Option("auto", "--lang", "-l", help="Language: auto, en, ko"),
):
    """Analyze a customer inquiry and get TSE guidance."""
    resolved_lang = _resolve_lang(lang, inquiry)
    engine = _get_engine(knowledge_dir, resolved_lang)

    if ai:
        if not ANTHROPIC_API_KEY:
            console.print(f"[red]{t('api_key_missing', resolved_lang)}[/red]")
            raise typer.Exit(1)
        from src.core.analyzer.ai_inquiry import AIInquiryAnalyzer
        analyzer = AIInquiryAnalyzer(engine)
        console.print(f"[dim]{t('using_ai_analysis', resolved_lang)}[/dim]")
        result = analyzer.analyze(inquiry, lang=resolved_lang)
        _display_analysis(result, title=t("ai_inquiry_analysis_title", resolved_lang), lang=resolved_lang)
    else:
        analyzer = InquiryAnalyzer(engine)
        result = analyzer.classify(inquiry, lang=resolved_lang)
        _display_analysis(result, lang=resolved_lang)


@app.command()
def logs(
    log_input: str = typer.Argument(..., help="Log content or path to a log file"),
    ai: bool = typer.Option(False, "--ai", help="Use Claude AI for enhanced log analysis"),
    threshold: int = typer.Option(5000, "--threshold", "-t", help="Slow operation threshold (ms)"),
    knowledge_dir: str = typer.Option(None, "--kb", help="Path to knowledge directory"),
    lang: str = typer.Option("auto", "--lang", "-l", help="Language: auto, en, ko"),
):
    """Parse and analyze log data."""
    resolved_lang = _resolve_lang(lang)
    log_path = Path(log_input)
    if log_path.is_file():
        raw_logs = log_path.read_text(encoding="utf-8")
    else:
        raw_logs = log_input

    if ai:
        if not ANTHROPIC_API_KEY:
            console.print(f"[red]{t('api_key_missing', resolved_lang)}[/red]")
            raise typer.Exit(1)
        from src.core.analyzer.log_analyzer import AILogAnalyzer
        engine = _get_engine(knowledge_dir, resolved_lang)
        ai_analyzer = AILogAnalyzer(engine)
        console.print(f"[dim]{t('using_ai_log_analysis', resolved_lang)}[/dim]")
        insight = ai_analyzer.analyze(raw_logs, lang=resolved_lang)

        console.print()
        console.print(Panel(
            f"[bold]{t('summary_label', resolved_lang)}[/bold]\n{insight.summary}\n\n"
            f"[bold]{t('root_cause_label', resolved_lang)}[/bold]\n{insight.root_cause_hypothesis}",
            title=f"[bold blue]{t('ai_log_analysis_title', resolved_lang)}[/bold blue]",
            border_style="blue",
        ))

        if insight.anomalies:
            console.print()
            console.print(f"[bold]{t('anomalies_label', resolved_lang)}[/bold]")
            for a in insight.anomalies:
                console.print(f"  - {a}")

        if insight.errors:
            console.print()
            console.print(f"[bold]{t('errors_found', resolved_lang).format(count=len(insight.errors))}[/bold]")
            for e in insight.errors:
                console.print(f"  [{e.timestamp}] {e.message}")

        if insight.slow_operations:
            console.print()
            console.print(f"[bold]{t('slow_ops_found', resolved_lang).format(count=len(insight.slow_operations))}[/bold]")
            for s in insight.slow_operations:
                dur = s.metadata.get("duration_ms", "?")
                console.print(f"  [{s.timestamp}] {s.message} ({dur}ms)")
    else:
        parser = LogParser()
        events = parser.parse(raw_logs)

        if not events:
            console.print(f"[yellow]{t('no_log_events', resolved_lang)}[/yellow]")
            raise typer.Exit(1)

        summary = parser.generate_text_summary(events, lang=resolved_lang)
        console.print()
        console.print(Panel(summary, title=f"[bold blue]{t('log_analysis_title', resolved_lang)}[/bold blue]", border_style="blue"))

        error_codes = parser.extract_error_codes(events)
        if error_codes:
            engine = _get_engine(knowledge_dir, resolved_lang)
            console.print()
            console.print(f"[bold]{t('error_code_details', resolved_lang)}[/bold]")
            for code in error_codes:
                results = engine.search(code, top_k=1, category="error_code")
                if results:
                    console.print(f"\n  [cyan]{code}[/cyan]: {results[0].title}")
                    console.print(f"  {results[0].content[:200]}...")
                else:
                    console.print(f"\n  [cyan]{code}[/cyan]: {t('no_documentation_found', resolved_lang)}")


@app.command()
def draft(
    inquiry: str = typer.Argument(..., help="Customer inquiry text"),
    knowledge_dir: str = typer.Option(None, "--kb", help="Path to knowledge directory"),
    lang: str = typer.Option("auto", "--lang", "-l", help="Language: auto, en, ko"),
):
    """Generate a draft response for a customer inquiry (requires AI)."""
    resolved_lang = _resolve_lang(lang, inquiry)

    if not ANTHROPIC_API_KEY:
        console.print(f"[red]{t('api_key_missing', resolved_lang)}[/red]")
        raise typer.Exit(1)

    engine = _get_engine(knowledge_dir, resolved_lang)

    # First analyze
    from src.core.analyzer.ai_inquiry import AIInquiryAnalyzer
    from src.core.responder.drafter import ResponseDrafter

    console.print(f"[dim]{t('analyzing_inquiry', resolved_lang)}[/dim]")
    analyzer = AIInquiryAnalyzer(engine)
    analysis = analyzer.analyze(inquiry, lang=resolved_lang)

    _display_analysis(analysis, title=t("inquiry_analysis_title", resolved_lang), lang=resolved_lang)

    # Then draft response
    console.print()
    console.print(f"[dim]{t('generating_draft', resolved_lang)}[/dim]")
    drafter = ResponseDrafter(engine)
    response = drafter.draft(inquiry, analysis, lang=resolved_lang)

    # Display draft
    escalation_text = (
        f"[bold red]{t('needs_escalation_yes', resolved_lang)}[/bold red]"
        if response.needs_escalation
        else f"[green]{t('needs_escalation_no', resolved_lang)}[/green]"
    )

    console.print()
    console.print(Panel(
        response.body,
        title=f"[bold green]{t('draft_response_title', resolved_lang)}[/bold green] (confidence: {response.confidence:.0%})",
        border_style="green",
    ))

    console.print()
    console.print(f"  {t('needs_escalation_label', resolved_lang)}{escalation_text}")

    if response.suggested_internal_note:
        console.print()
        console.print(Panel(
            response.suggested_internal_note,
            title=f"[bold yellow]{t('internal_note_title', resolved_lang)}[/bold yellow]",
            border_style="yellow",
        ))

    if response.citations:
        console.print()
        console.print(f"[bold]{t('sources_title', resolved_lang)}[/bold]")
        for c in response.citations:
            console.print(f"  - {c.title} ({c.category})")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    category: str = typer.Option(None, "--category", "-c", help="Filter by category"),
    top_k: int = typer.Option(5, "--top", "-k", help="Number of results"),
    knowledge_dir: str = typer.Option(None, "--kb", help="Path to knowledge directory"),
    lang: str = typer.Option("auto", "--lang", "-l", help="Language: auto, en, ko"),
):
    """Search the knowledge base."""
    resolved_lang = _resolve_lang(lang, query)
    engine = _get_engine(knowledge_dir, resolved_lang)
    results = engine.search(query, top_k=top_k, category=category)

    if not results:
        console.print(f"[yellow]{t('no_results', resolved_lang)}[/yellow]")
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
    lang: str = typer.Option("auto", "--lang", "-l", help="Language: auto, en, ko"),
):
    """Ingest knowledge documents into the knowledge base."""
    resolved_lang = _resolve_lang(lang)
    p = Path(path)
    engine = _get_engine(lang=resolved_lang)

    if p.is_dir():
        count = engine.ingest_directory(p)
        console.print(f"[green]{t('ingested_chunks', resolved_lang).format(count=count, path=p)}[/green]")
    elif p.is_file():
        count = engine.ingest_file(p)
        console.print(f"[green]{t('ingested_chunks', resolved_lang).format(count=count, path=p)}[/green]")
    else:
        console.print(f"[red]{t('path_not_found', resolved_lang).format(path=p)}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
