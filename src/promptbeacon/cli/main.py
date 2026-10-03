"""CLI interface for PromptBeacon."""

from __future__ import annotations

import asyncio
import contextlib
import json
import sys
import warnings
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
from promptbeacon.core.config import (
    Provider,
    get_default_storage_path,
    get_tavily_api_key,
    has_tavily_api_key,
)
from promptbeacon.core.exceptions import VisibilityAssertionError
from promptbeacon.reporting.formats import (
    describe_cost,
    to_csv,
    to_dashboard_html,
    to_html,
    to_json,
    to_markdown,
)

app = typer.Typer(
    name="promptbeacon",
    help=(
        "Does AI recommend your brand? Measure, track, and CI-test your "
        "visibility across ChatGPT, Claude, Gemini and more. Try keyless: "
        'promptbeacon demo "Nike"'
    ),
    no_args_is_help=True,
)
# Human-readable reports go to stdout; progress, banners, notices and errors go
# to stderr so that machine formats (json/csv/markdown/html) stay pipeable.
console = Console()
err_console = Console(stderr=True)


class OutputFormat(str, Enum):
    """Output format options."""

    text = "text"
    json = "json"
    markdown = "markdown"
    csv = "csv"
    html = "html"


def _emit(text: str) -> None:
    """Write a machine-readable document to stdout, verbatim (never wrapped)."""
    sys.stdout.write(text if text.endswith("\n") else text + "\n")
    sys.stdout.flush()


def _progress() -> Progress:
    """A transient spinner on stderr (never pollutes stdout)."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=err_console,
        transient=True,
    )


def _output_report(report, output_format: OutputFormat, text_printer) -> None:
    """Render a full scan report in the requested format."""
    if output_format == OutputFormat.json:
        _emit(to_json(report))
    elif output_format == OutputFormat.markdown:
        _emit(to_markdown(report))
    elif output_format == OutputFormat.csv:
        _emit(to_csv(report))
    elif output_format == OutputFormat.html:
        _emit(to_html(report))
    else:
        text_printer(report)


def _text_only_notice(output_format: OutputFormat, command: str) -> None:
    """Tell the user a format is not available for a command (falls back to text)."""
    if output_format not in (OutputFormat.text, OutputFormat.json):
        err_console.print(
            f"[yellow]{command} supports --format text or json; showing text.[/yellow]"
        )


# Shown when the user gave no competitors to the keyless demo. Clearly fictional
# so the demo never implies anything about a real company.
DEMO_PLACEHOLDER_COMPETITORS = ("Competitor A", "Competitor B")


def _run_scan(beacon: Beacon, description: str, *, stability: bool = False):
    """Run a scan with a stderr spinner, clean errors, and prompt-quality notices."""
    with _progress() as progress:
        progress.add_task(description=description, total=None)
        try:
            with warnings.catch_warnings():
                # The CLI explains missing categories itself (below).
                warnings.simplefilter("ignore", UserWarning)
                report = beacon.scan_stability() if stability else beacon.scan()
        except Exception as e:
            err_console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None
    _prompt_notice(report)
    return report


def _prompt_notice(report) -> None:
    """Explain on stderr how the prompts were chosen when it affects the result."""
    strategy = getattr(report, "prompt_strategy", None)
    if strategy == "generic":
        err_console.print(
            '[yellow]No --category given, so the prompts were generic ("What are '
            'the best general brands?") and the score says little.[/yellow]\n'
            f'[yellow]Re-run with --category, e.g. promptbeacon scan "{report.brand}" '
            '--category "running shoes", or add --competitor / --infer-category.'
            "[/yellow]"
        )
    elif strategy == "competitor_alternatives":
        err_console.print(
            '[dim]No --category given: asked "alternatives to <competitor>" '
            "questions. Add --category for buyer-intent prompts about your "
            "category.[/dim]"
        )
    elif strategy == "inferred_category" and report.categories:
        cat = report.categories[0]
        err_console.print(
            f"[cyan]Inferred category:[/cyan] {cat!r} (one extra LLM call). "
            f"Pin it with --category {cat!r} so future runs are comparable."
        )


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
        typer.Option(
            "--category",
            "-t",
            help='Category the prompts ask about, e.g. "running shoes" (repeatable)',
        ),
    ] = None,
    infer_category: Annotated[
        bool,
        typer.Option(
            "--infer-category",
            help="No category? Ask one model to name it (one extra LLM call; "
            "ignored in demo mode)",
        ),
    ] = False,
    prompt_count: Annotated[
        int | None,
        typer.Option("--prompts", "-n", help="Number of prompts per category"),
    ] = None,
    storage: Annotated[
        Path | None,
        typer.Option(
            "--storage",
            "-s",
            help="DuckDB history file (default: ~/.promptbeacon/data.db, or "
            "$PROMPTBEACON_HOME/data.db)",
        ),
    ] = None,
    save: Annotated[
        bool,
        typer.Option(
            "--save/--no-save",
            help="Save real scans to the history file so `promptbeacon history` "
            "can show trends (demo scans are only saved with an explicit --storage)",
        ),
    ] = True,
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
        promptbeacon scan "Nike" --category "running shoes" -c "Adidas" -p openai

        promptbeacon scan "Nike" -t "running shoes" --demo   # no API keys needed

        promptbeacon scan "Nike" --assert-min-score 50   # CI gate (exit 1 on fail)

        promptbeacon scan --protocol nike.json     # pinned, reproducible run
    """
    # Build beacon configuration — from a pinned protocol, or from CLI flags.
    if protocol is not None:
        from promptbeacon.protocol import build_beacon, load_protocol

        try:
            proto = load_protocol(protocol)
        except Exception as e:
            err_console.print(f"[red]Error loading protocol:[/red] {e}")
            raise typer.Exit(1) from None
        beacon = build_beacon(proto)
        if demo:
            beacon = beacon.demo()
        if storage:
            beacon = beacon.with_storage(storage)
        brand = proto.brand
        run_stability = proto.runs > 0
    else:
        if not brand:
            err_console.print("[red]Error:[/red] Provide a BRAND or use --protocol.")
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

        if infer_category:
            beacon = beacon.with_category_inference()

        if prompt_count is not None:
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

    # Real scans are saved to the default history file unless --no-save, so
    # `promptbeacon history` works out of the box. Demo data is never mixed in
    # unless --storage is given explicitly.
    history_path = storage
    if storage is None and save and not demo:
        history_path = get_default_storage_path()
        beacon = beacon.with_storage(history_path)
    if not save and storage is None:
        history_path = None

    report = _run_scan(
        beacon, f"Scanning visibility for {brand}...", stability=run_stability
    )
    beacon.close()
    if history_path is not None:
        err_console.print(
            f"[dim]Saved to history ({history_path}). "
            f'View trends: promptbeacon history "{brand}"[/dim]'
        )

    # Output results
    _output_report(report, output_format, _print_text_report)

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
            err_console.print("[green]✓ Visibility assertions passed.[/green]")
        except VisibilityAssertionError as e:
            err_console.print(f"[red]✗ Visibility assertion failed:[/red] {e}")
            raise typer.Exit(1) from None


@app.command()
def quick(
    brand: Annotated[str, typer.Argument(help="The brand name to analyze")],
    category: Annotated[
        str | None,
        typer.Option("--category", "-t", help='Category, e.g. "running shoes"'),
    ] = None,
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
        promptbeacon quick "Nike" --category "running shoes"
    """
    beacon = Beacon(brand).with_prompt_count(3)
    if category:
        beacon = beacon.with_category(category)
    if demo:
        beacon = beacon.demo()

    report = _run_scan(beacon, f"Quick scan for {brand}...")

    _output_report(report, output_format, _print_text_report)


@app.command()
def demo(
    brand: Annotated[str, typer.Argument(help="The brand name to analyze")] = "Nike",
    competitors: Annotated[
        list[str] | None,
        typer.Option("--competitor", "-c", help="Competitor brands to compare"),
    ] = None,
    categories: Annotated[
        list[str] | None,
        typer.Option(
            "--category", "-t", help='Category the prompts ask about, e.g. "crm"'
        ),
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
        promptbeacon demo "Nike" --category "running shoes" --competitor "Adidas"
    """
    beacon = Beacon(brand).demo()
    if categories:
        beacon = beacon.with_categories(*categories)

    err_console.print("[cyan]Running in DEMO mode — canned data, no API calls.[/cyan]")
    if competitors:
        beacon = beacon.with_competitors(*competitors)
    else:
        beacon = beacon.with_competitors(*DEMO_PLACEHOLDER_COMPETITORS)
        err_console.print(
            "[dim]No --competitor given: comparing against placeholder "
            "competitors ('Competitor A', 'Competitor B'). Add -c to compare "
            "with your real rivals.[/dim]"
        )

    report = _run_scan(beacon, f"Demo scan for {brand}...")

    _output_report(report, output_format, _print_comparison_report)


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
    categories: Annotated[
        list[str] | None,
        typer.Option("--category", "-t", help='Category, e.g. "running shoes"'),
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
        promptbeacon dashboard "Nike" -t "running shoes" -c "Adidas" --demo
    """
    beacon = Beacon(brand)
    if categories:
        beacon = beacon.with_categories(*categories)
    if competitors:
        beacon = beacon.with_competitors(*competitors)
    if providers:
        provider_enums = provider_callback(providers)
        if provider_enums:
            beacon = beacon.with_providers(*provider_enums)
    if demo:
        beacon = beacon.demo()

    report = _run_scan(beacon, f"Building dashboard for {brand}...")

    output.write_text(to_dashboard_html(report), encoding="utf-8")
    err_console.print(f"[green]Dashboard written to[/green] {output}")
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
    categories: Annotated[
        list[str] | None,
        typer.Option("--category", "-t", help='Category, e.g. "running shoes"'),
    ] = None,
    demo: Annotated[
        bool,
        typer.Option("--demo", help="Keyless demo mode (no API keys needed)"),
    ] = False,
    output_format: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Output format"),
    ] = OutputFormat.text,
) -> None:
    """Compare brand visibility against competitors.

    Example:
        promptbeacon compare "Nike" -t "running shoes" --against "Adidas" -a "Puma"
    """
    beacon = Beacon(brand).with_competitors(*against)
    if categories:
        beacon = beacon.with_categories(*categories)
    if demo:
        beacon = beacon.demo()

    if providers:
        provider_enums = provider_callback(providers)
        if provider_enums:
            beacon = beacon.with_providers(*provider_enums)

    report = _run_scan(beacon, f"Comparing {brand} with competitors...")

    _output_report(report, output_format, _print_comparison_report)


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
        int | None,
        typer.Option("--prompts", "-n", help="Number of prompts per category"),
    ] = None,
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
        promptbeacon sources "Nike" -t "running shoes" -c "Adidas" --grounded

        promptbeacon sources "Nike" -t "running shoes" --demo
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
    if prompt_count is not None:
        beacon = beacon.with_prompt_count(prompt_count)
    if demo:
        beacon = beacon.demo()
    if grounded:
        beacon = beacon.with_grounding()

    report = _run_scan(beacon, f"Finding sources for {brand}...")

    sa = report.source_attribution
    if output_format == OutputFormat.json:
        _emit(sa.model_dump_json(indent=2) if sa else "{}")
        return
    _text_only_notice(output_format, "sources")

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
            err_console.print(
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
            err_console.print(
                "[red]Error:[/red] --smart needs an LLM provider key "
                "(e.g. OPENAI_API_KEY). Run 'promptbeacon providers' to check."
            )
            raise typer.Exit(1) from None
        _llm = LiteLLMClient(available[0])

        async def complete_fn(text: str) -> str:
            resp = await _llm.complete(text, temperature=0.2, max_tokens=400)
            return resp.content

    with _progress() as progress:
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
            err_console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1) from None

    if output_format == OutputFormat.json:
        _emit(report.model_dump_json(indent=2))
    else:
        _text_only_notice(output_format, "funnel")
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
        promptbeacon history "Nike" --days 30
    """
    if not storage:
        storage = get_default_storage_path()

    if not Path(storage).expanduser().exists():
        if output_format == OutputFormat.json:
            _emit(
                json.dumps(
                    {"brand": brand, "data_points": [], "storage": str(storage)},
                    indent=2,
                )
            )
            return
        console.print(
            f"No history yet for {brand} ({storage}).\n"
            "Real scans are saved automatically, e.g.:\n"
            f'  promptbeacon scan "{brand}" --category "<your category>"'
        )
        return

    beacon = Beacon(brand).with_storage(storage)

    try:
        history_report = beacon.get_history(days)
    except Exception as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None

    if output_format == OutputFormat.json:
        _emit(history_report.model_dump_json(indent=2))
    else:
        _text_only_notice(output_format, "history")
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
    _print_prompt_line(report)


_STRATEGY_LABELS = {
    "category": "category",
    "inferred_category": "inferred category",
    "competitor_alternatives": "alternatives-to-competitor questions (no category)",
    "custom": "your custom prompts",
    "generic": "generic prompts (no category set)",
}


def _print_prompt_line(report) -> None:
    """One line saying what the prompts asked about."""
    strategy = getattr(report, "prompt_strategy", None)
    if not strategy:
        return
    count = len({r.prompt for r in report.provider_results})
    label = _STRATEGY_LABELS.get(strategy, strategy)
    cats = getattr(report, "categories", None) or []
    detail = f"{label}: {', '.join(cats)}" if cats else label
    console.print(f"[dim]prompts: {count} · {detail}[/dim]")


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
    cost_text = describe_cost(report)
    if cost_text:
        table.add_row("Estimated Cost", cost_text)

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

    sa = getattr(report, "source_attribution", None)
    if sa and sa.entries:
        # Source-domain attribution (which sites the engines cite).
        _print_source_attribution(report)
    elif report.citation_summary and report.citation_summary.total_citations > 0:
        # No domain table (e.g. name-only citations): list unique sources once.
        console.print("\n[bold]Sources Cited:[/bold]")
        seen: set[str] = set()
        for cit in report.citation_summary.citations:
            source = cit.url or cit.source_name
            if source in seen:
                continue
            seen.add(source)
            brand_tag = f" [{cit.brand_associated}]" if cit.brand_associated else ""
            console.print(f"  [cyan]•[/cyan] {source}{brand_tag}")
            if len(seen) >= 10:
                break


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
        console.print(
            "[yellow]No historical data found.[/yellow] Real scans are saved "
            f'automatically: promptbeacon scan "{history_report.brand}" '
            '--category "<your category>"'
        )
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


# --- shareable outputs ---------------------------------------------------------

_SHARE_LINK = "https://github.com/yotambraun/promptbeacon"


class BadgeMetricOption(str, Enum):
    both = "both"
    score = "score"
    sov = "sov"


class ThemeOption(str, Enum):
    light = "light"
    dark = "dark"
    both = "both"


def _beacon_from_options(
    brand: str,
    *,
    competitors: list[str] | None = None,
    providers: list[str] | None = None,
    categories: list[str] | None = None,
    prompt_count: int | None = None,
    demo: bool = False,
    grounded: bool = False,
    infer_category: bool = False,
) -> Beacon:
    """Build a Beacon from the common scan options (one source of truth)."""
    beacon = Beacon(brand)
    if competitors:
        beacon = beacon.with_competitors(*competitors)
    if providers:
        provider_enums = provider_callback(providers)
        if provider_enums:
            beacon = beacon.with_providers(*provider_enums)
    if categories:
        beacon = beacon.with_categories(*categories)
    if infer_category:
        beacon = beacon.with_category_inference()
    if prompt_count is not None:
        beacon = beacon.with_prompt_count(prompt_count)
    if demo:
        beacon = beacon.demo()
    if grounded:
        beacon = beacon.with_grounding()
    return beacon


def _report_for_share(
    report_path: Path | None, brand: str | None, description: str, **options
):
    """Load a saved JSON report, or run a scan from the given options."""
    from promptbeacon.core.schemas import Report

    if report_path is not None:
        try:
            return Report.model_validate_json(report_path.read_text(encoding="utf-8"))
        except Exception as e:
            err_console.print(f"[red]Error reading report {report_path}:[/red] {e}")
            raise typer.Exit(1) from None
    if not brand:
        err_console.print(
            "[red]Error:[/red] Provide a BRAND to scan, or --report with a saved "
            "`promptbeacon scan -f json` report."
        )
        raise typer.Exit(1)
    if options.get("demo"):
        err_console.print("[cyan]DEMO mode — canned data, labelled as demo.[/cyan]")
    return _run_scan(_beacon_from_options(brand, **options), description)


_ShareBrand = Annotated[
    str | None,
    typer.Argument(help="Brand to scan (omit when using --report)"),
]
_ShareReport = Annotated[
    Path | None,
    typer.Option(
        "--report", help="Render from a saved `scan -f json` report instead of scanning"
    ),
]
_ShareCompetitors = Annotated[
    list[str] | None, typer.Option("--competitor", "-c", help="Competitor brands")
]
_ShareProviders = Annotated[
    list[str] | None, typer.Option("--provider", "-p", help="LLM providers to use")
]
_ShareCategories = Annotated[
    list[str] | None,
    typer.Option("--category", "-t", help='Category, e.g. "running shoes"'),
]
_SharePrompts = Annotated[
    int | None, typer.Option("--prompts", "-n", help="Number of prompts per category")
]
_ShareDemo = Annotated[
    bool, typer.Option("--demo", help="Keyless demo mode (output is labelled demo)")
]
_ShareGrounded = Annotated[
    bool, typer.Option("--grounded", help="Measure web-grounded answers")
]


@app.command()
def badge(
    brand: _ShareBrand = None,
    report_path: _ShareReport = None,
    competitors: _ShareCompetitors = None,
    providers: _ShareProviders = None,
    categories: _ShareCategories = None,
    prompt_count: _SharePrompts = None,
    demo: _ShareDemo = False,
    grounded: _ShareGrounded = False,
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Where to write the SVG badge")
    ] = Path("promptbeacon-badge.svg"),
    endpoint: Annotated[
        Path | None,
        typer.Option(
            "--endpoint",
            help="Also write a shields.io endpoint JSON here (for img.shields.io)",
        ),
    ] = None,
    label: Annotated[
        str, typer.Option("--label", help="Badge label")
    ] = "AI visibility",
    metric: Annotated[
        BadgeMetricOption,
        typer.Option("--metric", help="What the badge shows: both, score, or sov"),
    ] = BadgeMetricOption.both,
) -> None:
    """Write a README badge (SVG, and optionally shields.io endpoint JSON).

    Example:
        promptbeacon badge "Nike" -t "running shoes" -c "Adidas" --demo

        promptbeacon scan "Nike" -t "running shoes" -f json > report.json
        promptbeacon badge --report report.json --endpoint .promptbeacon/badge.json
    """
    from promptbeacon.share import badge_endpoint, render_badge_svg

    report = _report_for_share(
        report_path,
        brand,
        f"Scanning {brand} for a badge...",
        competitors=competitors,
        providers=providers,
        categories=categories,
        prompt_count=prompt_count,
        demo=demo,
        grounded=grounded,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_badge_svg(report, label=label, metric=metric.value), encoding="utf-8"
    )
    err_console.print(f"[green]Badge written to[/green] {output}")
    if endpoint is not None:
        endpoint.parent.mkdir(parents=True, exist_ok=True)
        endpoint.write_text(
            json.dumps(
                badge_endpoint(report, label=label, metric=metric.value), indent=2
            )
            + "\n",
            encoding="utf-8",
        )
        err_console.print(
            f"[green]shields.io endpoint JSON written to[/green] {endpoint}"
        )
    err_console.print("[dim]Add it to your README:[/dim]")
    err_console.print(
        f"[![{label}]({output.as_posix()})]({_SHARE_LINK})",
        markup=False,
        soft_wrap=True,
    )
    if report.measurement_tier == "demo":
        err_console.print(
            "[yellow]This badge is from demo data and says so. Run without --demo "
            "for a real measurement.[/yellow]"
        )


@app.command()
def card(
    brand: _ShareBrand = None,
    report_path: _ShareReport = None,
    competitors: _ShareCompetitors = None,
    providers: _ShareProviders = None,
    categories: _ShareCategories = None,
    prompt_count: _SharePrompts = None,
    demo: _ShareDemo = False,
    grounded: _ShareGrounded = False,
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Where to write the SVG card")
    ] = Path("promptbeacon-card.svg"),
    png: Annotated[
        Path | None,
        typer.Option(
            "--png",
            help="Also write a PNG (for X, LinkedIn, Slack; needs "
            "'promptbeacon[share]')",
        ),
    ] = None,
    theme: Annotated[
        ThemeOption,
        typer.Option(
            "--theme",
            help="light, dark, or both (both writes a '-dark' variant next to "
            "each file)",
        ),
    ] = ThemeOption.light,
) -> None:
    """Write a share-ready result card (1200x630 SVG, optional PNG).

    Example:
        promptbeacon card "Nike" -t "running shoes" -c "Adidas" -c "Hoka" --demo

        promptbeacon card --report report.json --png card.png --theme both
    """
    from promptbeacon.share import render_card_png, render_card_svg

    report = _report_for_share(
        report_path,
        brand,
        f"Scanning {brand} for a card...",
        competitors=competitors,
        providers=providers,
        categories=categories,
        prompt_count=prompt_count,
        demo=demo,
        grounded=grounded,
    )
    themes = ["light", "dark"] if theme == ThemeOption.both else [theme.value]

    def themed(path: Path, name: str) -> Path:
        if theme == ThemeOption.both and name == "dark":
            return path.with_name(f"{path.stem}-dark{path.suffix}")
        return path

    for name in themes:
        target = themed(output, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_card_svg(report, name), encoding="utf-8")  # type: ignore[arg-type]
        err_console.print(f"[green]Card written to[/green] {target}")
        if png is not None:
            try:
                data = render_card_png(report, name)  # type: ignore[arg-type]
            except ImportError as e:
                err_console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1) from None
            png_target = themed(png, name)
            png_target.parent.mkdir(parents=True, exist_ok=True)
            png_target.write_bytes(data)
            err_console.print(f"[green]PNG written to[/green] {png_target}")
    if report.measurement_tier == "demo":
        err_console.print(
            "[yellow]This card is from demo data and is labelled 'Demo data'.[/yellow]"
        )


@app.callback()
def main() -> None:
    """PromptBeacon - LLM visibility monitoring for brands."""
    pass


if __name__ == "__main__":
    app()
