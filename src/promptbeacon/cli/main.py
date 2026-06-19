"""CLI interface for PromptBeacon."""

from __future__ import annotations

import asyncio
import contextlib
import webbrowser
from collections.abc import Awaitable, Callable
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from promptbeacon.beacon import Beacon
from promptbeacon.core.config import Provider, get_tavily_api_key, has_tavily_api_key
from promptbeacon.core.exceptions import VisibilityAssertionError
from promptbeacon.reporting.formats import to_dashboard_html, to_json, to_markdown

app = typer.Typer(
    name="promptbeacon",
    help=(
        "Does AI recommend your brand? Measure, track, and CI-test your "
        "visibility across ChatGPT, Claude, Gemini and more. Try keyless: "
        'promptbeacon demo "Nike"'
    ),
    no_args_is_help=True,
)
console = Console()


class OutputFormat(str, Enum):
    """Output format options."""

    text = "text"
    json = "json"
    markdown = "markdown"


def provider_callback(value: list[str] | None) -> list[Provider] | None:
    """Convert provider strings to Provider enums."""
    if value is None:
        return None
    providers = []
    for v in value:
        try:
            providers.append(Provider(v.lower()))
        except ValueError:
            valid = ", ".join(p.value for p in Provider)
            raise typer.BadParameter(
                f"Invalid provider: {v}. Choose from: {valid}"
            ) from None
    return providers


@app.command()
def scan(
    brand: Annotated[
        str | None,
        typer.Argument(help="The brand name to analyze (optional with --protocol)"),
    ] = None,
    competitors: Annotated[
        list[str] | None,
        typer.Option("--competitor", "-c", help="Competitor brands to compare"),
    ] = None,
    providers: Annotated[
        list[str] | None,
        typer.Option(
            "--provider", "-p", help="LLM providers to use (openai, anthropic, google)"
        ),
    ] = None,
    categories: Annotated[
        list[str] | None,
        typer.Option("--category", "-t", help="Categories/topics to analyze"),
    ] = None,
    prompt_count: Annotated[
        int,
        typer.Option("--prompts", "-n", help="Number of prompts per category"),
    ] = 10,
    storage: Annotated[
        Path | None,
        typer.Option("--storage", "-s", help="Path to DuckDB storage file"),
    ] = None,
    demo: Annotated[
        bool,
        typer.Option("--demo", help="Keyless demo mode (no API keys, canned data)"),
    ] = False,
    smart: Annotated[
        bool,
        typer.Option(
            "--smart",
            help="LLM-based extraction + recommendations (more accurate, costs more)",
        ),
    ] = False,
    grounded: Annotated[
        bool,
        typer.Option(
            "--grounded",
            help="Measure web-grounded answers (provider web search) instead of "
            "base-model memory — costs more, uses your API keys",
        ),
    ] = False,
    stability: Annotated[
        int,
        typer.Option(
            "--stability",
            "-r",
            help="Repeat the scan N times to measure stability (multiplies cost)",
        ),
    ] = 0,
    assert_min_score: Annotated[
        float | None,
        typer.Option("--assert-min-score", help="Fail (exit 1) if score is below this"),
    ] = None,
    assert_min_sov: Annotated[
        float | None,
        typer.Option(
            "--assert-min-sov", help="Fail if Share of Voice (0-1) is below this"
        ),
    ] = None,
    assert_min_stability: Annotated[
        float | None,
        typer.Option(
            "--assert-min-stability",
            help="Fail if stability score (0-100) is below this (needs --stability)",
        ),
    ] = None,
    protocol: Annotated[
        Path | None,
        typer.Option(
            "--protocol",
            help="Path to a pinned scan protocol JSON for reproducible runs "
            "(overrides the other config flags; see docs)",
        ),
    ] = None,
    output_format: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Output format"),
    ] = OutputFormat.text,
) -> None:
    """Scan LLM visibility for a brand.

    Example:
        promptbeacon scan "Nike" --competitor "Adidas" --provider openai

        promptbeacon scan "Nike" --demo            # no API keys needed

        promptbeacon scan "Nike" --assert-min-score 50   # CI gate (exit 1 on fail)

        promptbeacon scan --protocol nike.json     # pinned, reproducible run
    """
    # Build beacon configuration — from a pinned protocol, or from CLI flags.
    if protocol is not None:
        from promptbeacon.protocol import build_beacon, load_protocol

        try:
            proto = load_protocol(protocol)
        except Exception as e:
            console.print(f"[red]Error loading protocol:[/red] {e}")
            raise typer.Exit(1) from None
        beacon = build_beacon(proto)
        if demo:
            beacon = beacon.demo()
        brand = proto.brand
        run_stability = proto.runs > 0
    else:
        if not brand:
            console.print("[red]Error:[/red] Provide a BRAND or use --protocol.")
            raise typer.Exit(1)

        beacon = Beacon(brand)

        if competitors:
            beacon = beacon.with_competitors(*competitors)

        if providers:
            provider_enums = provider_callback(providers)
            if provider_enums:
                beacon = beacon.with_providers(*provider_enums)

        if categories:
            beacon = beacon.with_categories(*categories)

        if prompt_count != 10:
            beacon = beacon.with_prompt_count(prompt_count)

        if storage:
            beacon = beacon.with_storage(storage)

        if demo:
            beacon = beacon.demo()

        if smart:
            beacon = beacon.with_smart_extraction().with_smart_recommendations()

        if grounded:
            beacon = beacon.with_grounding()

        if stability > 0:
            beacon = beacon.with_stability(stability)

        run_stability = stability > 0

    # Run scan with progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(description=f"Scanning visibility for {brand}...", total=None)
        try:
            report = beacon.scan_stability() if run_stability else beacon.scan()
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

    # Output results
    if output_format == OutputFormat.json:
        console.print(to_json(report))
    elif output_format == OutputFormat.markdown:
        console.print(to_markdown(report))
    else:
        _print_text_report(report)

    # CI assertions (exit non-zero on failure)
    if any(
        v is not None for v in (assert_min_score, assert_min_sov, assert_min_stability)
    ):
        try:
            report.assert_visibility(
                min_score=assert_min_score,
                min_share_of_voice=assert_min_sov,
                min_stability_score=assert_min_stability,
            )
            console.print("[green]✓ Visibility assertions passed.[/green]")
        except VisibilityAssertionError as e:
            console.print(f"[red]✗ Visibility assertion failed:[/red] {e}")
            raise typer.Exit(1) from None


@app.command()
def quick(
    brand: Annotated[str, typer.Argument(help="The brand name to analyze")],
    demo: Annotated[
        bool,
        typer.Option("--demo", help="Keyless demo mode (no API keys needed)"),
    ] = False,
    output_format: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Output format"),
    ] = OutputFormat.text,
) -> None:
    """Run a fast 3-prompt scan with the cheapest available provider.

    Great for a quick check before running a full scan.

    Example:
        promptbeacon quick "Nike"
    """
    beacon = Beacon(brand).with_prompt_count(3)
    if demo:
        beacon = beacon.demo()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(description=f"Quick scan for {brand}...", total=None)
        try:
            report = beacon.scan()
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

    if output_format == OutputFormat.json:
        console.print(to_json(report))
    elif output_format == OutputFormat.markdown:
        console.print(to_markdown(report))
    else:
        _print_text_report(report)


@app.command()
def demo(
    brand: Annotated[str, typer.Argument(help="The brand name to analyze")] = "Nike",
    competitors: Annotated[
        list[str] | None,
        typer.Option("--competitor", "-c", help="Competitor brands to compare"),
    ] = None,
    output_format: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Output format"),
    ] = OutputFormat.text,
) -> None:
    """Run a keyless demo scan with realistic canned data (no API keys).

    The fastest way to see what PromptBeacon does. Uses an offline mock, so it
    works the moment you `pip install promptbeacon`.

    Example:
        promptbeacon demo "Nike" --competitor "Adidas"
    """
    beacon = Beacon(brand).demo()
    if competitors:
        beacon = beacon.with_competitors(*competitors)
    else:
        beacon = beacon.with_competitors("Adidas", "Puma")

    console.print("[cyan]Running in DEMO mode — canned data, no API calls.[/cyan]")
    report = beacon.scan()

    if output_format == OutputFormat.json:
        console.print(to_json(report))
    elif output_format == OutputFormat.markdown:
        console.print(to_markdown(report))
    else:
        _print_comparison_report(report)


@app.command()
def dashboard(
    brand: Annotated[str, typer.Argument(help="The brand name to analyze")],
    competitors: Annotated[
        list[str] | None,
        typer.Option("--competitor", "-c", help="Competitor brands to compare"),
    ] = None,
    providers: Annotated[
        list[str] | None,
        typer.Option("--provider", "-p", help="LLM providers to use"),
    ] = None,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Where to write the HTML dashboard"),
    ] = Path("promptbeacon-report.html"),
    demo: Annotated[
        bool, typer.Option("--demo", help="Keyless demo mode (no API keys needed)")
    ] = False,
    open_browser: Annotated[
        bool, typer.Option("--open/--no-open", help="Open the dashboard in a browser")
    ] = True,
) -> None:
    """Generate a shareable HTML dashboard for a brand.

    Example:
        promptbeacon dashboard "Nike" --competitor "Adidas" --demo
    """
    beacon = Beacon(brand)
    if competitors:
        beacon = beacon.with_competitors(*competitors)
    if providers:
        provider_enums = provider_callback(providers)
        if provider_enums:
            beacon = beacon.with_providers(*provider_enums)
    if demo:
        beacon = beacon.demo()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(description=f"Building dashboard for {brand}...", total=None)
        try:
            report = beacon.scan()
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

    output.write_text(to_dashboard_html(report), encoding="utf-8")
    console.print(f"[green]Dashboard written to[/green] {output}")
    if open_browser:
        with contextlib.suppress(Exception):
            webbrowser.open(output.resolve().as_uri())


@app.command()
def compare(
    brand: Annotated[str, typer.Argument(help="The brand name to analyze")],
    against: Annotated[
        list[str],
        typer.Option("--against", "-a", help="Competitor brands to compare against"),
    ],
    providers: Annotated[
        list[str] | None,
        typer.Option("--provider", "-p", help="LLM providers to use"),
    ] = None,
    output_format: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Output format"),
    ] = OutputFormat.text,
) -> None:
    """Compare brand visibility against competitors.

    Example:
        promptbeacon compare "Nike" --against "Adidas" --against "Puma"
    """
    beacon = Beacon(brand).with_competitors(*against)

    if providers:
        provider_enums = provider_callback(providers)
        if provider_enums:
            beacon = beacon.with_providers(*provider_enums)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(
            description=f"Comparing {brand} with competitors...", total=None
        )
        try:
            report = beacon.scan()
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

    if output_format == OutputFormat.json:
        console.print(to_json(report))
    elif output_format == OutputFormat.markdown:
        console.print(to_markdown(report))
    else:
        _print_comparison_report(report)


@app.command()
def sources(
    brand: Annotated[str, typer.Argument(help="The brand name to analyze")],
    competitors: Annotated[
        list[str] | None,
        typer.Option("--competitor", "-c", help="Competitor brands"),
    ] = None,
    providers: Annotated[
        list[str] | None,
        typer.Option("--provider", "-p", help="LLM providers to use"),
    ] = None,
    categories: Annotated[
        list[str] | None,
        typer.Option("--category", "-t", help="Categories/topics to analyze"),
    ] = None,
    prompt_count: Annotated[
        int,
        typer.Option("--prompts", "-n", help="Number of prompts per category"),
    ] = 10,
    demo: Annotated[
        bool,
        typer.Option("--demo", help="Keyless demo mode (no API keys needed)"),
    ] = False,
    grounded: Annotated[
        bool,
        typer.Option(
            "--grounded",
            help="Web-grounded measurement with real citations (uses your keys)",
        ),
    ] = False,
    output_format: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Output format"),
    ] = OutputFormat.text,
) -> None:
    """Show which source domains AI engines cite for your brand/category.

    Web-grounded answers cite their sources; this ranks those domains so you
    can see which sites feed your AI visibility — the actionable GEO lever
    ("get cited on these sites"). Pair with --grounded for real citations, or
    --demo to preview the output.

    Example:
        promptbeacon sources "Nike" --competitor "Adidas" --grounded

        promptbeacon sources "Nike" --demo
    """
    beacon = Beacon(brand)
    if competitors:
        beacon = beacon.with_competitors(*competitors)
    if providers:
        provider_enums = provider_callback(providers)
        if provider_enums:
            beacon = beacon.with_providers(*provider_enums)
    if categories:
        beacon = beacon.with_categories(*categories)
    if prompt_count != 10:
        beacon = beacon.with_prompt_count(prompt_count)
    if demo:
        beacon = beacon.demo()
    if grounded:
        beacon = beacon.with_grounding()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(description=f"Finding sources for {brand}...", total=None)
        try:
            report = beacon.scan()
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

    sa = report.source_attribution
    if output_format == OutputFormat.json:
        console.print(sa.model_dump_json(indent=2) if sa else "{}")
        return

    _print_tier_banner(report)
    if not sa or not sa.entries:
        console.print(
            "[yellow]No citations found.[/yellow] "
            "Try --grounded to measure web-grounded sources."
        )
        return
    _print_source_attribution(report)
    if sa.target_cited_domains:
        console.print(
            f"\n[green]Domains that cite {brand}:[/green] "
            + ", ".join(sa.target_cited_domains)
        )
    else:
        console.print(
            f"\n[yellow]No cited source was associated with {brand} "
            "in this scan.[/yellow]"
        )


@app.command()
def funnel(
    brand: Annotated[str, typer.Argument(help="The brand name to analyze")],
    prompt: Annotated[
        str | None,
        typer.Option("--prompt", "-q", help="Buyer-intent prompt to fan out"),
    ] = None,
    category: Annotated[
        str | None,
        typer.Option(
            "--category", "-t", help="Category (builds a prompt if --prompt omitted)"
        ),
    ] = None,
    competitors: Annotated[
        list[str] | None,
        typer.Option("--competitor", "-c", help="Competitor brands"),
    ] = None,
    demo: Annotated[
        bool,
        typer.Option("--demo", help="Keyless demo mode (mock search backend)"),
    ] = False,
    sub_queries: Annotated[
        int,
        typer.Option("--sub-queries", help="Fan-out width (sub-queries per prompt)"),
    ] = 8,
    smart: Annotated[
        bool,
        typer.Option(
            "--smart",
            help="Use an LLM planner + LLM-judge reranker (needs an LLM key; "
            "not in demo mode)",
        ),
    ] = False,
    output_format: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Output format"),
    ] = OutputFormat.text,
) -> None:
    """Glass-box: see where your brand drops out of the agentic-search funnel.

    Most tools only see the final citation. This fans a prompt into sub-queries,
    runs its own observable retrieve -> rerank -> cite pipeline, and reports
    where the brand survives or dies (coverage, rerank survival, citation).

    It is a local *model* of agentic search, not the consumer product. Use
    --demo for a keyless run, or set TAVILY_API_KEY for live web search.

    Example:
        promptbeacon funnel "Nike" --category "running shoes" --demo
    """
    from promptbeacon.funnel import (
        MockSearchBackend,
        SearchBackend,
        TavilyBackend,
        run_funnel,
    )

    if prompt:
        query = prompt
    elif category:
        query = f"What are the best {category}?"
    else:
        query = f"What are the best alternatives to {brand}?"

    backend: SearchBackend
    if demo:
        backend = MockSearchBackend(brand, competitors or [])
    else:
        api_key = get_tavily_api_key()
        if not api_key:
            console.print(
                "[red]Error:[/red] funnel needs --demo, or a Tavily API key for "
                "live web search.\n"
                "Get a free key at https://tavily.com, then set [bold]TAVILY_API_KEY[/bold] "
                "(an environment variable or a .env file in this directory)."
            )
            raise typer.Exit(1) from None
        backend = TavilyBackend(api_key)

    complete_fn: Callable[[str], Awaitable[str]] | None = None
    if smart and not demo:
        from promptbeacon.providers.litellm_client import (
            LiteLLMClient,
            get_available_providers,
        )

        available = get_available_providers()
        if not available:
            console.print(
                "[red]Error:[/red] --smart needs an LLM provider key "
                "(e.g. OPENAI_API_KEY). Run 'promptbeacon providers' to check."
            )
            raise typer.Exit(1) from None
        _llm = LiteLLMClient(available[0])

        async def complete_fn(text: str) -> str:
            resp = await _llm.complete(text, temperature=0.2, max_tokens=400)
            return resp.content

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(description=f"Tracing the funnel for {brand}...", total=None)
        try:
            report = asyncio.run(
                run_funnel(
                    brand,
                    query,
                    backend=backend,
                    competitors=competitors or [],
                    n_sub_queries=sub_queries,
                    complete=complete_fn,
                )
            )
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

    if output_format == OutputFormat.json:
        console.print(report.model_dump_json(indent=2))
    else:
        _print_funnel_report(report)


@app.command()
def history(
    brand: Annotated[str, typer.Argument(help="The brand name")],
    days: Annotated[
        int,
        typer.Option("--days", "-d", help="Number of days of history"),
    ] = 30,
    storage: Annotated[
        Path | None,
        typer.Option("--storage", "-s", help="Path to DuckDB storage file"),
    ] = None,
    output_format: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Output format"),
    ] = OutputFormat.text,
) -> None:
    """View historical visibility data for a brand.

    Example:
        promptbeacon history "Nike" --days 30 --storage ~/.promptbeacon/data.db
    """
    if not storage:
        storage = Path.home() / ".promptbeacon" / "data.db"

    beacon = Beacon(brand).with_storage(storage)

    try:
        history_report = beacon.get_history(days)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    if output_format == OutputFormat.json:
        console.print(history_report.model_dump_json(indent=2))
    else:
        _print_history_report(history_report)


@app.command()
def providers() -> None:
    """List available providers and search backends, and their key status."""
    from promptbeacon.core.config import has_api_key

    table = Table(title="Available Providers")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Environment Variable")

    env_vars = {
        Provider.OPENAI: "OPENAI_API_KEY",
        Provider.ANTHROPIC: "ANTHROPIC_API_KEY",
        Provider.GOOGLE: "GOOGLE_API_KEY",
        Provider.MISTRAL: "MISTRAL_API_KEY",
        Provider.COHERE: "COHERE_API_KEY",
        Provider.PERPLEXITY: "PERPLEXITY_API_KEY",
    }

    for provider in Provider:
        status = "✓ Configured" if has_api_key(provider) else "✗ Not configured"
        status_style = "green" if has_api_key(provider) else "red"
        table.add_row(
            provider.value,
            f"[{status_style}]{status}[/{status_style}]",
            env_vars.get(provider, ""),
        )

    # Tavily powers the funnel's live web search (not an LLM provider).
    tav = has_tavily_api_key()
    tav_status = "✓ Configured" if tav else "✗ Not configured"
    tav_style = "green" if tav else "red"
    table.add_row(
        "tavily (funnel search)",
        f"[{tav_style}]{tav_status}[/{tav_style}]",
        "TAVILY_API_KEY",
    )

    console.print(table)
    console.print(
        "[dim]Keys load from the environment or a .env file. LLM keys power "
        "scan/--grounded; TAVILY_API_KEY powers funnel live search "
        "(get one at https://tavily.com).[/dim]"
    )


_TIER_NOTES = {
    "demo": ("yellow", "Demo data — canned responses, not a real measurement."),
    "base_model": (
        "yellow",
        "Base-model tier: measures the model's training memory, NOT live AI "
        "search. Add --grounded to measure web-grounded answers.",
    ),
    "api_grounded": (
        "cyan",
        "Web-grounded tier: provider web search. Approximates — but does NOT "
        "equal — the consumer product (ChatGPT.com etc.).",
    ),
}


def _print_tier_banner(report) -> None:
    """Print an honest one-line label of how the scan was measured."""
    tier = getattr(report, "measurement_tier", "base_model")
    color, note = _TIER_NOTES.get(tier, ("white", ""))
    if note:
        console.print(f"[{color}]measurement: {tier}[/{color}] — {note}")


def _print_source_attribution(report) -> None:
    """Print the ranked source-domain table (which sites the engines cite)."""
    sa = getattr(report, "source_attribution", None)
    if not sa or not sa.entries:
        return
    console.print(
        f"\n[bold]Top Source Domains[/bold] "
        f"({sa.total_citations} citations across {len(sa.entries)} sources)"
    )
    table = Table(title="Which sites the engines cite")
    table.add_column("Domain", style="cyan")
    table.add_column("Type")
    table.add_column("Citations")
    table.add_column("Share")
    table.add_column(f"Cites {report.brand}?")
    for entry in sa.entries[:10]:
        table.add_row(
            entry.domain,
            entry.source_type,
            str(entry.citations),
            f"{entry.share:.0%}",
            "[green]yes[/green]" if entry.cites_target else "[dim]no[/dim]",
        )
    console.print(table)


def _print_text_report(report) -> None:
    """Print a text report to the console."""
    # Score color
    if report.visibility_score >= 70:
        score_style = "green bold"
    elif report.visibility_score >= 40:
        score_style = "yellow bold"
    else:
        score_style = "red bold"

    # Header panel
    console.print(
        Panel(
            f"[{score_style}]{report.visibility_score:.1f}[/{score_style}] / 100",
            title=f"Visibility Score: {report.brand}",
            subtitle=f"Generated: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        )
    )

    _print_tier_banner(report)

    # Metrics table
    table = Table(title="Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Mentions", str(report.mention_count))
    table.add_row("Positive Sentiment", f"{report.sentiment_breakdown.positive:.1%}")
    table.add_row("Neutral Sentiment", f"{report.sentiment_breakdown.neutral:.1%}")
    table.add_row("Negative Sentiment", f"{report.sentiment_breakdown.negative:.1%}")
    table.add_row("Providers Used", ", ".join(report.providers_used))
    table.add_row("Scan Duration", f"{report.scan_duration_seconds:.1f}s")
    if report.total_cost_usd:
        table.add_row("Estimated Cost", f"${report.total_cost_usd:.4f}")

    console.print(table)

    # Share of Voice
    sov = getattr(report, "share_of_voice", None)
    if sov and sov.aggregate:
        console.print(
            f"\n[bold]Share of Voice:[/bold] [cyan]{sov.target_share:.0%}[/cyan] "
            f"(rank {sov.target_rank}, {sov.target_presence_rate:.0%} of prompts)"
        )
        sov_table = Table(title="Share of Voice")
        sov_table.add_column("Brand", style="cyan")
        sov_table.add_column("Appears In")
        sov_table.add_column("Presence")
        sov_table.add_column("Share of Voice")
        ordered = sorted(
            sov.aggregate.values(), key=lambda e: e.appearances, reverse=True
        )
        for entry in ordered:
            is_target = entry.brand_name == report.brand
            name = f"[bold]{entry.brand_name}[/bold]" if is_target else entry.brand_name
            sov_table.add_row(
                name,
                f"{entry.appearances}/{entry.total_prompts}",
                f"{entry.presence_rate:.0%}",
                f"{entry.share_of_voice:.0%}",
            )
        console.print(sov_table)

    # Stability
    stability = getattr(report, "stability", None)
    if stability:
        rating_color = {
            "stable": "green",
            "moderate": "yellow",
            "volatile": "red",
        }.get(stability.volatility.stability_rating, "white")
        lo, hi = stability.score_confidence_interval
        console.print(
            f"\n[bold]Stability[/bold] ({stability.runs} runs): "
            f"[{rating_color}]{stability.stability_score:.0f}/100 "
            f"({stability.volatility.stability_rating})[/{rating_color}]  "
            f"95% CI [{lo:.0f}, {hi:.0f}]  "
            f"{stability.flip_flop_count} flip-flopping prompt(s)"
        )
        blo, bhi = stability.score_bootstrap_interval
        console.print(f"  Bootstrap 95% CI [{blo:.0f}, {bhi:.0f}] (distribution-free)")
        if stability.source_stability:
            flips = sum(1 for s in stability.source_stability if s.flip_flopped)
            console.print(
                f"  Source stability: {len(stability.source_stability)} domains cited, "
                f"{flips} flip-flopping across runs"
            )

    # Score breakdown
    bd = getattr(report.metrics, "score_breakdown", None) if report.metrics else None
    if bd:
        bd_table = Table(title="Score Breakdown (0-100 per factor, before weighting)")
        bd_table.add_column("Factor", style="cyan")
        bd_table.add_column("Score", style="green")
        bd_table.add_row("Mention Frequency", f"{bd.mention_frequency:.1f}")
        bd_table.add_row("Sentiment", f"{bd.sentiment:.1f}")
        bd_table.add_row("Position / Prominence", f"{bd.position:.1f}")
        bd_table.add_row("Recommendation Rate", f"{bd.recommendation:.1f}")
        console.print(bd_table)

    # Explanations
    if report.explanations:
        console.print("\n[bold]Key Insights:[/bold]")
        for exp in report.explanations[:5]:
            impact_color = {"high": "red", "medium": "yellow", "low": "green"}.get(
                exp.impact, "white"
            )
            console.print(f"  [{impact_color}]●[/{impact_color}] {exp.message}")

    # Recommendations
    if report.recommendations:
        console.print("\n[bold]Recommendations:[/bold]")
        for rec in report.recommendations[:5]:
            priority_color = {"high": "red", "medium": "yellow", "low": "green"}.get(
                rec.priority, "white"
            )
            console.print(
                f"  [{priority_color}][{rec.priority.upper()}][/{priority_color}] {rec.action}"
            )

    # Sources Cited
    if report.citation_summary and report.citation_summary.total_citations > 0:
        console.print("\n[bold]Sources Cited:[/bold]")
        for cit in report.citation_summary.citations[:10]:
            source = cit.url or cit.source_name
            brand_tag = f" [{cit.brand_associated}]" if cit.brand_associated else ""
            console.print(f"  [cyan]•[/cyan] {source}{brand_tag}")

    # Source-domain attribution (which sites the engines cite)
    _print_source_attribution(report)


def _print_comparison_report(report) -> None:
    """Print a comparison report to the console."""
    _print_text_report(report)

    if report.competitor_comparison:
        console.print("\n")
        table = Table(title="Competitor Comparison")
        table.add_column("Brand", style="cyan")
        table.add_column("Visibility Score")
        table.add_column("Mentions")
        table.add_column("Positive %")

        # Add main brand
        table.add_row(
            f"[bold]{report.brand}[/bold]",
            f"[bold]{report.visibility_score:.1f}[/bold]",
            f"[bold]{report.mention_count}[/bold]",
            f"[bold]{report.sentiment_breakdown.positive:.0%}[/bold]",
        )

        # Add competitors
        for name, score in report.competitor_comparison.items():
            table.add_row(
                name,
                f"{score.visibility_score:.1f}",
                str(score.mention_count),
                f"{score.sentiment.positive:.0%}",
            )

        console.print(table)


def _print_funnel_report(report) -> None:
    """Print the agentic-search funnel report to the console."""
    console.print(
        f"[cyan]measurement: {report.measurement_tier}[/cyan] — "
        "a local model of agentic search, not the consumer product"
    )
    console.print(
        Panel(
            f"[dim]prompt:[/dim] {report.prompt}",
            title=f"Agentic Funnel: {report.brand}",
            subtitle=f"{report.sub_query_count} sub-queries",
        )
    )

    def pct(value: float) -> str:
        return f"{value:.0%}"

    console.print(
        f"Coverage (brand retrieved):   [cyan]{pct(report.sub_query_coverage)}[/cyan]"
    )
    console.print(f"Rerank survival:              {pct(report.rerank_survival_rate)}")
    console.print(
        f"Retrieval → citation:         {pct(report.retrieval_to_citation_ratio)}"
    )
    fail_color = "green" if report.stage_failure == "none" else "yellow"
    console.print(
        f"Dominant drop-off stage:      [{fail_color}]{report.stage_failure}[/{fail_color}]"
    )

    table = Table(title="Per sub-query funnel")
    table.add_column("Sub-query", style="cyan")
    table.add_column("Retrieved")
    table.add_column("Reranked")
    table.add_column("Cited")

    def mark(flag: bool) -> str:
        return "[green]✓[/green]" if flag else "[dim]·[/dim]"

    for sq in report.sub_query_results:
        table.add_row(
            sq.sub_query,
            mark(sq.target_retrieved),
            mark(sq.target_after_rerank),
            mark(sq.target_cited),
        )
    console.print(table)


def _print_history_report(history_report) -> None:
    """Print a history report to the console."""
    console.print(
        Panel(
            f"[bold]{history_report.brand}[/bold]",
            title="Historical Visibility Data",
        )
    )

    if not history_report.data_points:
        console.print("[yellow]No historical data found.[/yellow]")
        return

    # Summary stats
    if history_report.average_score:
        console.print(f"Average Score: [bold]{history_report.average_score:.1f}[/bold]")

    if history_report.trend_direction:
        trend_icon = {"up": "↑", "down": "↓", "stable": "→"}.get(
            history_report.trend_direction, ""
        )
        trend_color = {"up": "green", "down": "red", "stable": "yellow"}.get(
            history_report.trend_direction, "white"
        )
        console.print(
            f"Trend: [{trend_color}]{trend_icon} {history_report.trend_direction}[/{trend_color}]"
        )

    if history_report.volatility:
        console.print(f"Volatility: {history_report.volatility:.2f}")

    # Data points table
    console.print("\n")
    table = Table(title="Historical Data Points")
    table.add_column("Date", style="cyan")
    table.add_column("Score")
    table.add_column("Mentions")
    table.add_column("Sentiment")

    for dp in history_report.data_points[-10:]:  # Last 10 points
        sentiment_str = f"+{dp.sentiment.positive:.0%} / -{dp.sentiment.negative:.0%}"
        table.add_row(
            dp.timestamp.strftime("%Y-%m-%d"),
            f"{dp.visibility_score:.1f}",
            str(dp.mention_count),
            sentiment_str,
        )

    console.print(table)


@app.callback()
def main() -> None:
    """PromptBeacon - LLM visibility monitoring for brands."""
    pass


if __name__ == "__main__":
    app()
