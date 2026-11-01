"""CLI interface for PromptBeacon."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import sys
import warnings
import webbrowser
from collections.abc import Awaitable, Callable
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape as _markup_escape
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from promptbeacon.beacon import Beacon
from promptbeacon.core.config import (
    Provider,
    get_default_storage_path,
    get_promptbeacon_home,
    get_tavily_api_key,
    has_tavily_api_key,
)
from promptbeacon.core.exceptions import VisibilityAssertionError
from promptbeacon.reporting.formats import (
    describe_budget,
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
        "Does AI recommend your library or dev product? Measure it across "
        "ChatGPT, Claude, Gemini and local models, gate it in CI and show it as a "
        'README badge. Try it keyless: promptbeacon demo httpx -t "python http '
        'client". Set up a repository: promptbeacon init'
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


def _esc(error: object) -> str:
    """An exception's text, safe to embed in Rich markup ("[share]" stays visible)."""
    return _markup_escape(str(error))


_KEYLESS_HINT = (
    "Add --demo for a keyless run, or use a local model with --model "
    "litellm=ollama/llama3.2. `promptbeacon providers` shows what is configured."
)


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


PROVIDER_HELP = (
    "LLM providers to query (repeatable): openai, anthropic, google, mistral, "
    "cohere, perplexity, or litellm (any LiteLLM model, set with --model)"
)
MODEL_HELP = (
    "Model for a provider as provider=model_id (repeatable), e.g. "
    "anthropic=claude-sonnet-5-5, or litellm=ollama/llama3.2 for a local model. "
    "Providers named here are queried when --provider is not given. "
    "Default: $PROMPTBEACON_<PROVIDER>_MODEL, else the built-in default "
    "(see `promptbeacon providers`)"
)
_ModelsOption = Annotated[
    list[str] | None, typer.Option("--model", "-m", help=MODEL_HELP)
]
MAX_COST_HELP = (
    "Spending cap in US dollars, e.g. 0.05. The cost is estimated first (from "
    "LiteLLM's price map) and the scan refuses to start above the cap; during "
    "the scan no new request starts once the cap is reached, and the result is "
    "marked partial. Models with no known price (e.g. local) count as $0"
)
_MaxCostOption = Annotated[
    float | None, typer.Option("--max-cost", help=MAX_COST_HELP, min=0.000001)
]


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
            message = str(e)
            if "No API keys found" in message:
                message = message.split(" Or try keyless demo mode")[0]
                message = f"{message}\n{_KEYLESS_HINT}"
            err_console.print(f"[red]Error:[/red] {_esc(message)}")
            raise typer.Exit(1) from None
    _prompt_notice(report)
    return report


def _prompt_notice(report) -> None:
    """Explain on stderr how the prompts were chosen when it affects the result."""
    strategy = getattr(report, "prompt_strategy", None)
    if strategy == "generic":
        err_console.print(
            '[yellow]No --category given, so the prompts asked about "general" '
            "and the score says little.[/yellow]\n"
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


def _saved_notice(path, brand: str) -> None:
    err_console.print(
        f"[dim]Saved to history ({path}). "
        f'View trends: promptbeacon history "{brand}"[/dim]'
    )


def _save_default_history(report, brand: str) -> None:
    """Save to the default history file; warn instead of failing."""
    from promptbeacon.storage.database import Database

    try:
        path = get_default_storage_path()
        db = Database(path)
        try:
            db.save_report(report)
        finally:
            db.close()
    except Exception as e:  # noqa: BLE001 — history is a convenience
        err_console.print(
            f"[yellow]Could not save to history ({_esc(e)}). The scan itself "
            "succeeded; use --storage PATH or set PROMPTBEACON_HOME.[/yellow]"
        )
        return
    _saved_notice(path, brand)


def provider_callback(value: list[str] | None) -> list[Provider] | None:
    """Convert provider strings to Provider enums."""
    if value is None:
        return None
    from promptbeacon.builder import parse_providers

    try:
        return parse_providers(value)
    except ValueError as e:
        raise typer.BadParameter(str(e)) from None


@app.command(rich_help_panel="Start here")
def scan(
    brand: Annotated[
        str | None,
        typer.Argument(
            help="The brand name to analyze (optional with --protocol or a project "
            "option such as --repo)"
        ),
    ] = None,
    repo: Annotated[
        str | None,
        typer.Option(
            "--repo",
            help="Scan a GitHub project, e.g. encode/httpx (reads public "
            "metadata to pick the category and competitors)",
        ),
    ] = None,
    pypi: Annotated[
        str | None, typer.Option("--pypi", help="Scan a PyPI package, e.g. httpx")
    ] = None,
    npm: Annotated[
        str | None, typer.Option("--npm", help="Scan an npm package, e.g. express")
    ] = None,
    crate: Annotated[
        str | None,
        typer.Option("--crate", help="Scan a Rust crate on crates.io, e.g. serde"),
    ] = None,
    hf: Annotated[
        str | None,
        typer.Option(
            "--hf",
            help="Scan a Hugging Face model (owner/name), dataset "
            "(datasets/owner/name) or Space (spaces/owner/name)",
        ),
    ] = None,
    project: Annotated[
        str | None,
        typer.Option(
            "--project", help="Scan any supported source as kind:ref, e.g. pypi:httpx"
        ),
    ] = None,
    competitors: Annotated[
        list[str] | None,
        typer.Option("--competitor", "-c", help="Competitor brands to compare"),
    ] = None,
    providers: Annotated[
        list[str] | None,
        typer.Option("--provider", "-p", help=PROVIDER_HELP),
    ] = None,
    models: _ModelsOption = None,
    max_cost: _MaxCostOption = None,
    estimate: Annotated[
        bool,
        typer.Option(
            "--estimate",
            help="Print the estimated cost of this scan and exit (sends nothing)",
        ),
    ] = False,
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
    """Measure whether AI assistants recommend a brand or project.

    Example:
        promptbeacon scan "Nike" --category "running shoes" -c "Adidas" -p openai

        promptbeacon scan "Nike" -t "running shoes" --demo   # no API keys needed

        promptbeacon scan "Nike" --assert-min-score 50   # CI gate (exit 1 on fail)

        promptbeacon scan --protocol nike.json     # pinned, reproducible run

        promptbeacon scan --pypi httpx --demo      # an open-source package

        promptbeacon scan --crate serde --demo     # a Rust crate

        promptbeacon scan --hf sentence-transformers/all-MiniLM-L6-v2 --demo

        promptbeacon scan "httpx" -t "python http client" -m openai=gpt-6-sol

        promptbeacon scan "httpx" -t "python http client" -m litellm=ollama/llama3.2

        promptbeacon scan "httpx" -t "python http client" --max-cost 0.05

        promptbeacon scan "httpx" -t "python http client" -p openai --estimate
    """
    # Build beacon configuration — from a pinned protocol, or from CLI flags.
    if protocol is not None:
        from promptbeacon.protocol import build_beacon, load_protocol

        try:
            proto = load_protocol(protocol)
        except Exception as e:
            err_console.print(f"[red]Error loading protocol:[/red] {_esc(e)}")
            raise typer.Exit(1) from None
        beacon = build_beacon(proto)
        if demo:
            beacon = beacon.demo()
        brand = proto.brand
        run_stability = proto.runs > 0
    else:
        project_ref = _project_ref(repo, pypi, npm, project, crate=crate, hf=hf)
        if not brand and not project_ref:
            err_console.print(
                "[red]Error:[/red] Provide a BRAND, a project "
                "(--repo/--pypi/--npm/--crate/--hf), or --protocol."
            )
            raise typer.Exit(1)

        beacon = _beacon_from_options(
            brand,
            project=project_ref,
            competitors=competitors,
            providers=providers,
            models=models,
            categories=categories,
            prompt_count=prompt_count,
            demo=demo,
            infer_category=infer_category,
        )
        brand = beacon.brand

        if smart:
            beacon = beacon.with_smart_extraction().with_smart_recommendations()

        if grounded:
            beacon = beacon.with_grounding()

        if stability > 0:
            beacon = beacon.with_stability(stability)

        run_stability = stability > 0

    if max_cost is not None:
        beacon = beacon.with_max_cost(max_cost)
    if estimate:
        _print_estimate(beacon, output_format, stability=run_stability)
        return

    # Real scans are saved to the default history file unless --no-save, so
    # `promptbeacon history` works out of the box. Demo data is only saved with
    # an explicit --storage. Saving the default history is best-effort: a
    # read-only home or a locked database never loses a scan you paid for.
    explicit_storage = storage is not None and save
    if storage is not None and save:
        beacon = beacon.with_storage(storage)

    report = _run_scan(
        beacon, f"Scanning visibility for {brand}...", stability=run_stability
    )
    beacon.close()
    if explicit_storage:
        _saved_notice(storage, brand)
    elif save and not demo:
        _save_default_history(report, brand)

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
            err_console.print(f"[red]✗ Visibility assertion failed:[/red] {_esc(e)}")
            raise typer.Exit(1) from None


@app.command(rich_help_panel="Analyse")
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
    beacon = _beacon_from_options(
        brand,
        categories=[category] if category else None,
        prompt_count=3,
        demo=demo,
    )

    report = _run_scan(beacon, f"Quick scan for {brand}...")

    _output_report(report, output_format, _print_text_report)


@app.command(rich_help_panel="Start here")
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
    err_console.print("[cyan]Running in DEMO mode — canned data, no API calls.[/cyan]")
    beacon = _beacon_from_options(
        brand,
        competitors=competitors or list(DEMO_PLACEHOLDER_COMPETITORS),
        categories=categories,
        demo=True,
    )
    if not competitors:
        err_console.print(
            "[dim]No --competitor given: comparing against placeholder "
            "competitors ('Competitor A', 'Competitor B'). Add -c to compare "
            "with your real rivals.[/dim]"
        )

    report = _run_scan(beacon, f"Demo scan for {brand}...")

    _output_report(report, output_format, _print_comparison_report)
    if output_format == OutputFormat.text:
        args = _shell_args(brand, categories, competitors)
        err_console.print(
            "\n[bold]Next:[/bold] price a real scan (sends nothing): "
            f"[cyan]promptbeacon scan {_esc(args)} --estimate[/cyan]\n"
            "Then set a provider key (e.g. OPENAI_API_KEY in a .env file) and run "
            "it without --estimate. Set up your repository: "
            "[cyan]promptbeacon init[/cyan]",
            highlight=False,
        )


@app.command(rich_help_panel="Share and track")
def dashboard(
    brand: Annotated[str, typer.Argument(help="The brand name to analyze")],
    competitors: Annotated[
        list[str] | None,
        typer.Option("--competitor", "-c", help="Competitor brands to compare"),
    ] = None,
    providers: Annotated[
        list[str] | None,
        typer.Option("--provider", "-p", help=PROVIDER_HELP),
    ] = None,
    models: _ModelsOption = None,
    max_cost: _MaxCostOption = None,
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
    beacon = _beacon_from_options(
        brand,
        competitors=competitors,
        providers=providers,
        models=models,
        categories=categories,
        demo=demo,
        max_cost=max_cost,
    )
    report = _run_scan(beacon, f"Building dashboard for {brand}...")

    output.write_text(to_dashboard_html(report), encoding="utf-8")
    err_console.print(f"[green]Dashboard written to[/green] {output}")
    if open_browser:
        with contextlib.suppress(Exception):
            webbrowser.open(output.resolve().as_uri())


@app.command(rich_help_panel="Analyse")
def compare(
    brand: Annotated[str, typer.Argument(help="The brand name to analyze")],
    against: Annotated[
        list[str],
        typer.Option("--against", "-a", help="Competitor brands to compare against"),
    ],
    providers: Annotated[
        list[str] | None,
        typer.Option("--provider", "-p", help=PROVIDER_HELP),
    ] = None,
    models: _ModelsOption = None,
    max_cost: _MaxCostOption = None,
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
    beacon = _beacon_from_options(
        brand,
        competitors=against,
        providers=providers,
        models=models,
        categories=categories,
        demo=demo,
        max_cost=max_cost,
    )

    report = _run_scan(beacon, f"Comparing {brand} with competitors...")

    _output_report(report, output_format, _print_comparison_report)


@app.command(rich_help_panel="Analyse")
def sources(
    brand: Annotated[str, typer.Argument(help="The brand name to analyze")],
    competitors: Annotated[
        list[str] | None,
        typer.Option("--competitor", "-c", help="Competitor brands"),
    ] = None,
    providers: Annotated[
        list[str] | None,
        typer.Option("--provider", "-p", help=PROVIDER_HELP),
    ] = None,
    models: _ModelsOption = None,
    max_cost: _MaxCostOption = None,
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
    beacon = _beacon_from_options(
        brand,
        competitors=competitors,
        providers=providers,
        models=models,
        categories=categories,
        prompt_count=prompt_count,
        demo=demo,
        grounded=grounded,
        max_cost=max_cost,
    )
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


@app.command(rich_help_panel="Analyse")
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
            err_console.print(f"[red]Error:[/red] {_esc(e)}")
            raise typer.Exit(1) from None

    if output_format == OutputFormat.json:
        _emit(report.model_dump_json(indent=2))
    else:
        _text_only_notice(output_format, "funnel")
        _print_funnel_report(report)


@app.command(rich_help_panel="Share and track")
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
        err_console.print(f"[red]Error:[/red] {_esc(e)}")
        raise typer.Exit(1) from None

    if output_format == OutputFormat.json:
        _emit(history_report.model_dump_json(indent=2))
    else:
        _text_only_notice(output_format, "history")
        _print_history_report(history_report)


@app.command(rich_help_panel="Start here")
def providers() -> None:
    """List providers, their key status, and the model each one will use."""
    from promptbeacon.core.config import (
        API_KEY_ENV_VARS,
        has_api_key,
        model_env_var,
        resolve_model,
    )

    table = Table(title="Available Providers")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("API key variable")
    table.add_column("Model (override variable)")

    for provider in Provider:
        model = resolve_model(provider) or "not set"
        if provider == Provider.LITELLM:
            ok = model != "not set"
            status = "✓ Model set" if ok else "– Set a model to use"
            key_vars = "read by LiteLLM"
        else:
            ok = has_api_key(provider)
            status = "✓ Configured" if ok else "✗ Not configured"
            key_vars = " or ".join(API_KEY_ENV_VARS[provider])
        style = "green" if ok else ("dim" if provider == Provider.LITELLM else "red")
        table.add_row(
            provider.value,
            f"[{style}]{status}[/{style}]",
            key_vars,
            f"{model} ({model_env_var(provider)})",
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
        "(get one at https://tavily.com). Choose a model per scan with "
        "--model provider=model_id; litellm=ollama/llama3.2 runs a local "
        "Ollama model.[/dim]"
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


def _shell_args(
    brand: str | None, categories: list[str] | None, competitors: list[str] | None
) -> str:
    """Brand, -t and -c options as a copy-pasteable command fragment."""
    import shlex

    parts = [shlex.quote(brand)] if brand else []
    for c in categories or []:
        parts += ["-t", shlex.quote(c)]
    for c in competitors or []:
        parts += ["-c", shlex.quote(c)]
    return " ".join(parts)


def _print_tier_banner(report) -> None:
    """Print an honest one-line label of how the scan was measured."""
    tier = getattr(report, "measurement_tier", "base_model")
    color, note = _TIER_NOTES.get(tier, ("white", ""))
    if note:
        console.print(f"[{color}]measurement: {tier}[/{color}] — {note}")
    _print_prompt_line(report)
    budget_text = describe_budget(report)
    if budget_text:
        style = "bold yellow" if report.partial else "dim"
        console.print(f"[{style}]budget: {budget_text}[/{style}]", highlight=False)


def _print_estimate(beacon: Beacon, output_format: OutputFormat, *, stability: bool):
    """``scan --estimate``: price the scan without sending anything."""
    from promptbeacon.budget import format_usd

    runs = (beacon._stability_runs or 5) if stability else 1
    try:
        est = beacon.estimate_cost(runs)
    except Exception as e:
        err_console.print(f"[red]Error:[/red] {_esc(e)}")
        raise typer.Exit(1) from None
    if output_format == OutputFormat.json:
        data = est.as_dict()
        data["max_cost_usd"] = beacon._max_cost
        data["within_budget"] = (
            None if beacon._max_cost is None else est.total_usd <= beacon._max_cost
        )
        _emit(json.dumps(data, indent=2))
        return
    _text_only_notice(output_format, "scan --estimate")
    table = Table(title=f"Estimated cost: {beacon.brand}")
    table.add_column("Model", style="cyan")
    table.add_column("Requests", justify="right")
    table.add_column("Estimate", justify="right")
    table.add_column("At most", justify="right")
    table.add_column("Note", style="dim")
    for line in est.lines:
        table.add_row(
            f"{line.provider}/{line.model}"
            if line.provider != "litellm"
            else line.model,
            str(line.requests),
            format_usd(line.usd) if line.priced else "$0 (no price)",
            format_usd(line.upper_usd) if line.priced else "–",
            line.note,
        )
    console.print(table)
    console.print(f"Total: [bold]{est.summary()}[/bold]", highlight=False)
    console.print(f"[dim]Assumes {est.assumptions}. Nothing was sent.[/dim]")
    if beacon._max_cost is not None:
        cap = format_usd(beacon._max_cost)
        if est.total_usd > beacon._max_cost:
            console.print(
                f"[red]Above the {cap} budget: this scan would not start.[/red]"
            )
        else:
            console.print(f"[green]Within the {cap} budget.[/green]")


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
    rank = "rank"


class ThemeOption(str, Enum):
    light = "light"
    dark = "dark"
    both = "both"


def _project_ref(
    repo: str | None = None,
    pypi: str | None = None,
    npm: str | None = None,
    project: str | None = None,
    *,
    crate: str | None = None,
    hf: str | None = None,
) -> str | None:
    """Combine the project options into one ``kind:ref`` (at most one allowed)."""
    refs = [
        f"github:{repo}" if repo else None,
        f"pypi:{pypi}" if pypi else None,
        f"npm:{npm}" if npm else None,
        f"crates:{crate}" if crate else None,
        f"hf:{hf}" if hf else None,
        project,
    ]
    given = [r for r in refs if r]
    if len(given) > 1:
        err_console.print(
            "[red]Error:[/red] Use only one of --repo, --pypi, --npm, --crate, "
            "--hf, --project."
        )
        raise typer.Exit(1)
    return given[0] if given else None


def _beacon_from_options(
    brand: str | None,
    *,
    project: str | None = None,
    competitors: list[str] | None = None,
    providers: list[str] | None = None,
    models: list[str] | None = None,
    categories: list[str] | None = None,
    prompt_count: int | None = None,
    demo: bool = False,
    grounded: bool = False,
    infer_category: bool = False,
    max_cost: float | None = None,
) -> Beacon:
    """CLI wrapper around :func:`promptbeacon.builder.configure_beacon`.

    Adds a spinner while project metadata is read, explains the project guesses,
    and turns configuration errors into clean exits.
    """
    from promptbeacon.builder import configure_beacon
    from promptbeacon.projects import (
        ProjectMetadataError,
        ProjectMetadataUnavailable,
        project_name_from_ref,
    )

    try:
        if project:
            try:
                with _progress() as progress:
                    progress.add_task(description=f"Reading {project}...", total=None)
                    beacon = configure_beacon(
                        brand,
                        project=project,
                        competitors=competitors,
                        providers=providers,
                        models=models,
                        categories=categories,
                        prompt_count=prompt_count,
                        demo=demo,
                        grounded=grounded,
                        infer_category=infer_category,
                        max_cost=max_cost,
                    )
            except ProjectMetadataUnavailable as e:
                if not demo:
                    raise
                # The keyless demo works offline: carry on with the name only.
                brand = brand or project_name_from_ref(project)
                err_console.print(
                    f"[yellow]Could not read {project} ({_esc(e)}). Demo continues "
                    f"offline with the name {brand!r}"
                    + (
                        "."
                        if categories
                        else "; add --category for meaningful prompts."
                    )
                    + "[/yellow]",
                    highlight=False,
                )
                project = None
            else:
                _project_notice(beacon, categories, competitors, infer_category, demo)
                return beacon
        return configure_beacon(
            brand,
            competitors=competitors,
            providers=providers,
            models=models,
            categories=categories,
            prompt_count=prompt_count,
            demo=demo,
            grounded=grounded,
            infer_category=infer_category,
            max_cost=max_cost,
        )
    except (ProjectMetadataError, ValueError) as e:
        err_console.print(f"[red]Error:[/red] {_esc(e)}")
        raise typer.Exit(1) from None


def _project_notice(
    beacon: Beacon,
    categories: list[str] | None,
    competitors: list[str] | None,
    infer: bool,
    demo: bool,
) -> None:
    """Explain (on stderr) what was read from the project and how to override."""
    profile = beacon.project
    if profile is None:
        return
    meta = profile.metadata
    err_console.print(
        f"[cyan]Project:[/cyan] {meta.name} ({meta.source}: {meta.ref})"
        + (f" — {meta.description}" if meta.description else ""),
        highlight=False,
    )
    guess = profile.category
    if categories:
        err_console.print(
            f"[dim]Category: {', '.join(categories)} (from --category)[/dim]"
        )
    elif infer and not demo:
        fallback = f"; offline guess {guess.category!r}" if guess.category else ""
        err_console.print(
            f"[dim]Category: asked one model (--infer-category){fallback}[/dim]"
        )
    elif guess.category:
        err_console.print(
            f"[dim]Category: {guess.category!r} (guessed from {guess.basis}, "
            f"{guess.confidence} confidence). Override with --category.[/dim]"
        )
    else:
        err_console.print(
            "[yellow]Could not guess a category from the project metadata. "
            "Pass --category (or --infer-category with an API key).[/yellow]"
        )
    if competitors:
        return
    if profile.competitors:
        err_console.print(
            f"[dim]Competitors: {', '.join(profile.competitors)} "
            f"({profile.competitor_basis}). Override with --competitor.[/dim]"
        )
    else:
        err_console.print(
            "[dim]No competitors found in the README; add --competitor to compare "
            "share of voice.[/dim]"
        )


def _report_for_share(
    report_path: Path | None,
    brand: str | None,
    description: str,
    project: str | None = None,
    **options,
):
    """Load a saved JSON report, or run a scan from the given options."""
    from promptbeacon.core.schemas import Report

    if report_path is not None:
        try:
            return Report.model_validate_json(report_path.read_text(encoding="utf-8"))
        except Exception as e:
            err_console.print(
                f"[red]Error reading report {report_path}:[/red] {_esc(e)}"
            )
            raise typer.Exit(1) from None
    if not brand and not project:
        err_console.print(
            "[red]Error:[/red] Provide a BRAND or project (--repo/--pypi/--npm/"
            "--crate/--hf) to scan, or --report with a saved "
            "`promptbeacon scan -f json` report."
        )
        raise typer.Exit(1)
    if options.get("demo"):
        err_console.print("[cyan]DEMO mode — canned data, labelled as demo.[/cyan]")
    return _run_scan(
        _beacon_from_options(brand, project=project, **options), description
    )


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
    list[str] | None, typer.Option("--provider", "-p", help=PROVIDER_HELP)
]
_ShareCategories = Annotated[
    list[str] | None,
    typer.Option("--category", "-t", help='Category, e.g. "running shoes"'),
]
_SharePrompts = Annotated[
    int | None, typer.Option("--prompts", "-n", help="Number of prompts per category")
]
_ShareRepo = Annotated[str | None, typer.Option("--repo", help="GitHub owner/name")]
_SharePyPI = Annotated[str | None, typer.Option("--pypi", help="PyPI package")]
_ShareNpm = Annotated[str | None, typer.Option("--npm", help="npm package")]
_ShareCrate = Annotated[str | None, typer.Option("--crate", help="crates.io crate")]
_ShareHF = Annotated[
    str | None,
    typer.Option("--hf", help="Hugging Face owner/name (datasets/... or spaces/...)"),
]
_ShareProject = Annotated[
    str | None, typer.Option("--project", help="kind:ref, e.g. pypi:httpx")
]
_ShareDemo = Annotated[
    bool, typer.Option("--demo", help="Keyless demo mode (output is labelled demo)")
]
_ShareGrounded = Annotated[
    bool, typer.Option("--grounded", help="Measure web-grounded answers")
]


@app.command(rich_help_panel="Share and track")
def badge(
    brand: _ShareBrand = None,
    report_path: _ShareReport = None,
    repo: _ShareRepo = None,
    pypi: _SharePyPI = None,
    npm: _ShareNpm = None,
    crate: _ShareCrate = None,
    hf: _ShareHF = None,
    project: _ShareProject = None,
    competitors: _ShareCompetitors = None,
    providers: _ShareProviders = None,
    models: _ModelsOption = None,
    max_cost: _MaxCostOption = None,
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
        str | None,
        typer.Option(
            "--label", help='Badge label (default "AI visibility", or "AI rank")'
        ),
    ] = None,
    metric: Annotated[
        BadgeMetricOption,
        typer.Option(
            "--metric",
            help="What the badge shows: both (score and share of voice), score, "
            'sov, or rank ("#2 of 9 · python http clients"; needs a category and '
            "at least two competitors)",
        ),
    ] = BadgeMetricOption.both,
) -> None:
    """Write a README badge (SVG, and optionally shields.io endpoint JSON).

    Example:
        promptbeacon badge "Nike" -t "running shoes" -c "Adidas" --demo

        promptbeacon scan "Nike" -t "running shoes" -f json > report.json
        promptbeacon badge --report report.json --endpoint .promptbeacon/badge.json

        promptbeacon badge --report report.json --metric rank -o rank.svg
    """
    from promptbeacon.share import (
        RankUnavailableError,
        badge_endpoint,
        render_badge_svg,
    )
    from promptbeacon.share.badge import default_label

    report = _report_for_share(
        report_path,
        brand,
        f"Scanning {brand or 'project'} for a badge...",
        project=_project_ref(repo, pypi, npm, project, crate=crate, hf=hf),
        competitors=competitors,
        providers=providers,
        models=models,
        categories=categories,
        prompt_count=prompt_count,
        demo=demo,
        grounded=grounded,
        max_cost=max_cost,
    )
    label = label or default_label(metric.value)
    try:
        svg = render_badge_svg(report, label=label, metric=metric.value)
    except RankUnavailableError as e:
        err_console.print(f"[red]Error:[/red] {_esc(e)}")
        raise typer.Exit(1) from None
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding="utf-8")
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
    elif report.partial:
        err_console.print(
            "[yellow]The scan was cut short by --max-cost, so the badge says "
            "'partial'.[/yellow]"
        )


@app.command(rich_help_panel="Share and track")
def card(
    brand: _ShareBrand = None,
    report_path: _ShareReport = None,
    repo: _ShareRepo = None,
    pypi: _SharePyPI = None,
    npm: _ShareNpm = None,
    crate: _ShareCrate = None,
    hf: _ShareHF = None,
    project: _ShareProject = None,
    competitors: _ShareCompetitors = None,
    providers: _ShareProviders = None,
    models: _ModelsOption = None,
    max_cost: _MaxCostOption = None,
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
            "'promptbeacon\\[share]')",
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
    trend_file: Annotated[
        Path | None,
        typer.Option(
            "--trend",
            help="JSON trend file (e.g. .promptbeacon/trend.json): this report is "
            "added to it (real scans only) and its scores drawn as a sparkline. "
            "For CI, where no local history persists. Default: the local history",
        ),
    ] = None,
    show_trend: Annotated[
        bool,
        typer.Option(
            "--show-trend/--no-trend",
            help="Draw a score sparkline when 3+ real scans measured the same way "
            "exist",
        ),
    ] = True,
    storage: Annotated[
        Path | None,
        typer.Option(
            "--storage",
            "-s",
            help="History file to read the trend from (default "
            "~/.promptbeacon/data.db)",
        ),
    ] = None,
) -> None:
    """Write a share-ready result card (1200x630 SVG, optional PNG).

    With 3 or more real scans of the same kind in your history (or in a --trend
    file), the card also shows a score sparkline. Demo data never does.

    Example:
        promptbeacon card "Nike" -t "running shoes" -c "Adidas" -c "Hoka" --demo

        promptbeacon card --report report.json --png card.png --theme both

        promptbeacon card --report report.json --trend .promptbeacon/trend.json
    """
    from promptbeacon.share import render_card_png, render_card_svg

    report = _report_for_share(
        report_path,
        brand,
        f"Scanning {brand or 'project'} for a card...",
        project=_project_ref(repo, pypi, npm, project, crate=crate, hf=hf),
        competitors=competitors,
        providers=providers,
        models=models,
        categories=categories,
        prompt_count=prompt_count,
        demo=demo,
        grounded=grounded,
        max_cost=max_cost,
    )
    trend = _card_trend(report, trend_file, storage) if show_trend else None
    themes = ["light", "dark"] if theme == ThemeOption.both else [theme.value]

    def themed(path: Path, name: str) -> Path:
        if theme == ThemeOption.both and name == "dark":
            return path.with_name(f"{path.stem}-dark{path.suffix}")
        return path

    for name in themes:
        target = themed(output, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            render_card_svg(report, name, trend=trend),  # type: ignore[arg-type]
            encoding="utf-8",
        )
        err_console.print(f"[green]Card written to[/green] {target}")
        if png is not None:
            try:
                data = render_card_png(report, name, trend=trend)  # type: ignore[arg-type]
            except ImportError as e:
                err_console.print(f"[red]Error:[/red] {_esc(e)}")
                raise typer.Exit(1) from None
            png_target = themed(png, name)
            png_target.parent.mkdir(parents=True, exist_ok=True)
            png_target.write_bytes(data)
            err_console.print(f"[green]PNG written to[/green] {png_target}")
    if report.measurement_tier == "demo":
        err_console.print(
            "[yellow]This card is from demo data and is labelled 'Demo data'.[/yellow]"
        )


def _card_trend(report, trend_file: Path | None, storage: Path | None):
    """Scores for the card's sparkline, or None (and say why on stderr)."""
    from promptbeacon.share.trend import (
        MIN_POINTS,
        comparable,
        history_points,
        trend_values,
        update_trend_file,
    )

    if report.measurement_tier == "demo":
        if trend_file is not None:
            err_console.print(
                f"[dim]Demo data is never added to {_esc(trend_file)} or drawn as a "
                "trend.[/dim]"
            )
        return None
    try:
        if trend_file is not None:
            points = update_trend_file(trend_file, report)
            source = str(trend_file)
        else:
            path = storage or (get_promptbeacon_home() / "data.db")
            points = history_points(Path(path).expanduser(), report)
            source = "history"
    except Exception as e:  # noqa: BLE001 — a trend is optional
        err_console.print(f"[yellow]No trend on the card: {_esc(e)}[/yellow]")
        return None
    values = trend_values(points, report)
    if values:
        err_console.print(
            f"[dim]Trend: the last {len(values)} comparable real scans ({source}).[/dim]"
        )
    else:
        have = len(comparable(points, report))
        err_console.print(
            f"[dim]No trend yet: it appears with {MIN_POINTS} real scans measured "
            f"the same way (found {have}, including this one).[/dim]"
        )
    return values


@app.command(rich_help_panel="Share and track")
def ci(
    report_path: Annotated[
        Path,
        typer.Option("--report", help="Report from `promptbeacon scan -f json`"),
    ],
    min_score: Annotated[
        float | None, typer.Option("--min-score", help="Minimum visibility score")
    ] = None,
    min_sov: Annotated[
        float | None, typer.Option("--min-sov", help="Minimum share of voice (0-1)")
    ] = None,
    min_presence: Annotated[
        float | None,
        typer.Option("--min-presence", help="Minimum presence rate (0-1)"),
    ] = None,
    min_stability: Annotated[
        float | None,
        typer.Option("--min-stability", help="Minimum stability score (0-100)"),
    ] = None,
    max_rank: Annotated[
        int | None, typer.Option("--max-rank", help="Worst acceptable SoV rank")
    ] = None,
    max_cost: Annotated[
        float | None,
        typer.Option(
            "--max-cost",
            help="Fail if the report's estimated cost (USD) is above this. A "
            "report cut short by its own --max-cost is shown as partial",
            min=0.000001,
        ),
    ] = None,
    comment_file: Annotated[
        Path | None,
        typer.Option(
            "--comment-file", help="Write a PR-comment body (with a hidden marker)"
        ),
    ] = None,
) -> None:
    """Summarise a report for CI: outputs, job summary, PR comment, and gates.

    Writes step outputs to $GITHUB_OUTPUT and a Markdown summary to
    $GITHUB_STEP_SUMMARY when those are set (GitHub Actions), prints the summary
    otherwise, and exits 1 if any threshold is missed — after writing
    everything, so a failing check still reports its numbers.

    Example:
        promptbeacon scan "Nike" -t "running shoes" -f json --no-save > report.json
        promptbeacon ci --report report.json --min-score 50 --min-sov 0.3

        promptbeacon ci --report report.json --max-cost 0.10
    """
    import os

    from promptbeacon.core.schemas import Report
    from promptbeacon.share.summary import ci_outputs, summary_markdown

    try:
        report = Report.model_validate_json(report_path.read_text(encoding="utf-8"))
    except Exception as e:
        err_console.print(f"[red]Error reading report {report_path}:[/red] {_esc(e)}")
        raise typer.Exit(1) from None

    thresholds = {
        name: value
        for name, value in (
            ("min score", min_score),
            ("min share of voice", min_sov),
            ("min presence", min_presence),
            ("min stability", min_stability),
            ("max rank", max_rank),
            ("max cost", max_cost),
        )
        if value is not None
    }
    failures: list[str] = []
    try:
        report.assert_visibility(
            min_score=min_score,
            min_share_of_voice=min_sov,
            min_presence_rate=min_presence,
            min_stability_score=min_stability,
            max_rank=max_rank,
        )
    except VisibilityAssertionError as e:
        failures = list(e.failures)
    if (
        max_cost is not None
        and report.total_cost_usd is not None
        and report.total_cost_usd > max_cost
    ):
        failures.append(f"cost ${report.total_cost_usd:.4f} > ${max_cost:g}")
    passed = not failures

    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as fh:
            for key, value in ci_outputs(report, passed).items():
                fh.write(f"{key}={value}\n")

    summary = summary_markdown(report, failures=failures, thresholds=thresholds)
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as fh:
            fh.write(summary + "\n")
    else:
        _emit(summary)

    if comment_file is not None:
        comment_file.parent.mkdir(parents=True, exist_ok=True)
        comment_file.write_text(
            summary_markdown(
                report, failures=failures, thresholds=thresholds, marker=True
            ),
            encoding="utf-8",
        )

    if failures:
        err_console.print(
            "[red]✗ Visibility check failed:[/red] " + "; ".join(failures)
        )
        raise typer.Exit(1)
    if thresholds:
        err_console.print("[green]✓ Visibility check passed.[/green]")


def _is_interactive() -> bool:
    """Whether init may ask questions (a terminal on stdin and stdout)."""
    return sys.stdin.isatty() and sys.stdout.isatty()


@app.command(rich_help_panel="Start here")
def init(
    path: Annotated[
        Path, typer.Argument(help="Project root (default: the current directory)")
    ] = Path("."),
    brand: Annotated[
        str | None,
        typer.Option(
            "--brand", "-b", help="Name to measure (default: the project name)"
        ),
    ] = None,
    categories: Annotated[
        list[str] | None,
        typer.Option(
            "--category", "-t", help='Category to ask about, e.g. "python http client"'
        ),
    ] = None,
    competitors: Annotated[
        list[str] | None,
        typer.Option("--competitor", "-c", help="Competitors (repeatable)"),
    ] = None,
    providers: Annotated[
        list[str] | None, typer.Option("--provider", "-p", help=PROVIDER_HELP)
    ] = None,
    models: _ModelsOption = None,
    max_cost: Annotated[
        float | None,
        typer.Option(
            "--max-cost",
            help="Cap per weekly run in US dollars (default: twice the estimate, "
            "rounded up to $0.05)",
            min=0.000001,
        ),
    ] = None,
    protocol: Annotated[
        bool,
        typer.Option(
            "--protocol",
            help="Also write .promptbeacon/protocol.json, pinning the prompts and "
            "models, and use it in the workflow",
        ),
    ] = False,
    workflow: Annotated[
        str,
        typer.Option("--workflow", help="Where to write the workflow"),
    ] = ".github/workflows/ai-visibility.yml",
    yes: Annotated[
        bool,
        typer.Option(
            "--yes", "-y", help="Write without asking (new files only; see --force)"
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", help="With --yes, also replace files that differ"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Only show what would be written"),
    ] = False,
    run_demo: Annotated[
        bool | None,
        typer.Option(
            "--demo/--no-demo",
            help="Run a keyless demo scan at the end (asked when interactive)",
        ),
    ] = None,
    output_format: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="text, or json (the plan, for tools)"),
    ] = OutputFormat.text,
) -> None:
    """Set this repository up: weekly AI-visibility workflow, badge and next steps.

    Reads pyproject.toml, package.json, Cargo.toml, the README and the git
    remote, proposes a category (with its basis), shows the files it would
    write and asks first. Never replaces a file without confirmation; running
    it again changes nothing unless the inputs changed. Works with no API keys.

    Example:
        promptbeacon init

        promptbeacon init --dry-run

        promptbeacon init -t "python http client" -c requests -c aiohttp --yes
    """
    from rich.text import Text

    from promptbeacon.core.config import has_api_key
    from promptbeacon.init_project import build_plan, detect_project, write_plan

    root = path.expanduser().resolve()
    if not root.is_dir():
        err_console.print(f"[red]Error:[/red] {path} is not a directory.")
        raise typer.Exit(1)
    machine = output_format == OutputFormat.json
    _text_only_notice(output_format, "init")
    interactive = _is_interactive() and not machine and not yes and not dry_run
    say = err_console.print if machine else console.print

    project = detect_project(root)
    category = categories[0] if categories else None
    if not machine:
        found = ", ".join(project.found) or "no project files"
        say(
            f"[cyan]Project:[/cyan] {project.name or '?'} ({found})"
            + (f" — {project.description}" if project.description else ""),
            highlight=False,
        )

    try:
        plan = build_plan(
            project,
            brand=brand,
            category=category,
            competitors=competitors,
            providers=providers,
            models=models,
            max_cost=max_cost,
            protocol=protocol,
            workflow_path=workflow,
        )
    except ValueError as e:
        err_console.print(f"[red]Error:[/red] {_esc(e)}")
        raise typer.Exit(1) from None

    # Let a person confirm or correct the two guesses that matter most.
    if interactive:
        if not categories and not project.protocol:
            hint = (
                f" (guessed from {plan.category_basis})"
                if plan.category
                else " (could not guess one)"
            )
            say(
                "[bold]Category[/bold]: what developers would ask AI about, "
                f'e.g. "python http client"{hint}.'
            )
            answer = typer.prompt("Category", default=plan.category or "").strip()
            if answer and answer != plan.category:
                category = answer
        if not competitors and not project.protocol:
            default = ", ".join(plan.competitors)
            answer = typer.prompt(
                "Competitors to compare with (comma-separated, Enter for none)",
                default=default,
                show_default=bool(default),
            ).strip()
            picked = [c.strip() for c in answer.split(",") if c.strip()]
            if picked != plan.competitors:
                competitors = picked or None
        if category != (categories[0] if categories else None) or competitors:
            plan = build_plan(
                project,
                brand=brand,
                category=category or plan.category,
                competitors=competitors,
                providers=providers,
                models=models,
                max_cost=max_cost,
                protocol=protocol,
                workflow_path=workflow,
            )

    if not plan.category and not plan.uses_protocol:
        err_console.print(
            "[red]Error:[/red] No category: PromptBeacon could not guess one from "
            'the project files. Pass --category, e.g. --category "python http '
            'client".'
        )
        raise typer.Exit(1)

    if machine:
        data = plan.as_dict()
        data["written"] = []
        if yes and not dry_run:
            paths = [
                f.path
                for f in plan.files
                if f.status == "create" or (f.status == "update" and force)
            ]
            data["written"] = [str(p) for p in write_plan(plan, paths)]
        _emit(json.dumps(data, indent=2))
        return

    if not categories and not interactive and plan.category:
        say(
            f"[dim]Category: {plan.category!r} (from {plan.category_basis}, "
            f"{plan.category_confidence} confidence). Override with --category.[/dim]",
            highlight=False,
        )
    if plan.competitors:
        say(
            f"[dim]Competitors: {', '.join(plan.competitors)} ({plan.competitor_basis})."
            "[/dim]",
            highlight=False,
        )
    else:
        say(
            "[dim]No competitors: add -c NAME (two or more also give a rank "
            "badge).[/dim]"
        )
    if plan.estimate_usd is not None:
        say(
            f"[dim]Estimated cost per weekly run: ${plan.estimate_usd:.4f} "
            f"(LiteLLM prices); capped at ${plan.max_cost:.2f} by max-cost.[/dim]"
        )

    # Preview.
    to_write: list[str] = []
    for planned in plan.files:
        if planned.status == "unchanged":
            say(f"[green]✓[/green] {planned.path} is up to date.")
            continue
        if planned.status == "create":
            say(f"\n[bold]create[/bold] {planned.path}")
            say(
                planned.content.rstrip("\n"),
                markup=False,
                highlight=False,
                soft_wrap=True,
            )
            to_write.append(planned.path)
        else:
            note = "" if planned.generated_before else " (not written by init)"
            say(f"\n[bold yellow]update[/bold yellow] {planned.path}{note}")
            for line in planned.diff().splitlines():
                style = (
                    "green"
                    if line.startswith("+") and not line.startswith("+++")
                    else "red"
                    if line.startswith("-") and not line.startswith("---")
                    else "dim"
                )
                say(Text(line, style=style), soft_wrap=True)
            to_write.append(planned.path)

    written = []
    if not to_write:
        say("\nNothing to write: the project is already set up.")
    elif dry_run:
        say("\n[cyan]Dry run: nothing was written.[/cyan]")
    elif not interactive and not yes:
        say(
            "\n[yellow]Not a terminal, so nothing was written. Re-run with --yes to "
            "write new files (and --force to replace changed ones), or --dry-run to "
            "only preview.[/yellow]"
        )
    else:
        chosen = []
        for planned in plan.files:
            if planned.path not in to_write:
                continue
            if planned.status == "update":
                if yes and not force:
                    say(
                        f"[yellow]Skipped {planned.path}: it exists and differs "
                        "(diff above). Re-run with --yes --force to replace it.[/yellow]"
                    )
                    continue
                if interactive and not typer.confirm(
                    f"Replace {planned.path}?", default=False
                ):
                    continue
            chosen.append(planned.path)
        updates = {f.path for f in plan.files if f.status == "update"}
        news = [f for f in chosen if f not in updates]
        if (
            interactive
            and news
            and not typer.confirm(f"Write {', '.join(news)}?", default=True)
        ):
            chosen = [f for f in chosen if f not in news]
        written = write_plan(plan, chosen)
        for target in written:
            say(f"[green]Wrote[/green] {target.relative_to(root).as_posix()}")
        if not written:
            say("Nothing was written.")

    # Keys: the workflow needs repository secrets; local keys only matter here.
    if plan.secrets:
        local = [p for p in plan.providers if has_api_key(p)]
        say("\n[bold]API keys[/bold]")
        say(
            "The workflow reads "
            + ", ".join(plan.secrets)
            + " from your repository secrets. Add "
            + ("it" if len(plan.secrets) == 1 else "them")
            + " with the GitHub CLI (it prompts for the value, so the key stays out "
            "of your shell history):"
        )
        for name in plan.secrets:
            say(f"  gh secret set {name}", highlight=False)
        if not local:
            say(
                "[dim]No provider key is set locally either. init and `promptbeacon "
                "demo` do not need one; for a real scan on this machine, put the key "
                "in a .env file or the environment.[/dim]"
            )

    say("\n[bold]README badge[/bold] (updates after the first workflow run):")
    say(plan.badge_markdown, markup=False, highlight=False, soft_wrap=True)
    if plan.rank_badge_markdown:
        say("[dim]Rank among the projects you compared:[/dim]")
        say(plan.rank_badge_markdown, markup=False, highlight=False, soft_wrap=True)

    if run_demo is None:
        run_demo = interactive and typer.confirm(
            "\nRun a keyless demo scan now to see the output?", default=True
        )
    if run_demo:
        say("\n[cyan]DEMO — canned answers, not a measurement.[/cyan]")
        beacon = _beacon_from_options(
            plan.brand,
            competitors=plan.competitors or list(DEMO_PLACEHOLDER_COMPETITORS),
            categories=[plan.category] if plan.category else None,
            demo=True,
        )
        report = _run_scan(beacon, f"Demo scan for {plan.brand}...")
        _print_tier_banner(report)
        sov = report.share_of_voice
        if sov and sov.aggregate:
            table = Table(title="Mentions per project (demo data)")
            table.add_column("Project", style="cyan")
            table.add_column("Answers mentioning it", justify="right")
            for entry in sorted(sov.aggregate.values(), key=lambda e: -e.appearances):
                name = entry.brand_name
                if name == report.brand:
                    name = f"[bold]{name}[/bold]"
                table.add_row(name, f"{entry.appearances}/{entry.total_prompts}")
            say(table)

    from promptbeacon.init_project import next_steps

    steps = next_steps(plan)
    if to_write and not written:
        command = "promptbeacon init"
        if path != Path("."):
            command += f" {path}"
        if not plan.uses_protocol:
            command += " " + _shell_args(
                None, [plan.category] if plan.category else None, plan.competitors
            )
        if not _is_interactive():
            command += " --yes"
            if any(f.status == "update" for f in plan.files):
                command += " --force  # replaces the changed file shown above"
        steps.insert(0, f"Write the files: {command.strip()}")
    say("\n[bold]Next steps[/bold]")
    for i, step in enumerate(steps, 1):
        say(f"  {i}. {step}", highlight=False, soft_wrap=True)


@app.command("mcp", rich_help_panel="Integrations")
def mcp_server() -> None:
    """Run the MCP server over stdio, for Claude Code, Cursor, VS Code and others.

    Needs the extra: pip install 'promptbeacon[mcp]'. Tools: providers,
    estimate, scan, project_scan, sources, compare, recommendations, history,
    funnel, init_preview, share_assets. Without provider keys, scans use the
    keyless demo and say so. Setup for each client:
    https://yotambraun.github.io/promptbeacon/mcp/

    Example:
        claude mcp add promptbeacon -- uvx --from 'promptbeacon[mcp]>=1.4.0' promptbeacon mcp
    """
    try:
        from promptbeacon.mcp_server import create_server
    except ImportError as e:  # pragma: no cover
        err_console.print(f"[red]Error:[/red] {_esc(e)}")
        raise typer.Exit(1) from None
    try:
        server = create_server()
    except ImportError as e:
        err_console.print(f"[red]Error:[/red] {_esc(e)}")
        raise typer.Exit(1) from None
    server.run("stdio")


def _version_callback(value: bool) -> None:
    if value:
        from promptbeacon import __version__

        typer.echo(f"promptbeacon {__version__}")
        raise typer.Exit()


class _CliLogHandler(logging.Handler):
    """Library warnings on stderr, styled, minus ones the CLI explains itself."""

    _EXPLAINED = ("No category set for",)

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if message.startswith(self._EXPLAINED):
            return
        err_console.print(f"[yellow]{_esc(message)}[/yellow]", highlight=False)


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the version and exit",
        ),
    ] = False,
) -> None:
    """PromptBeacon: does AI recommend your library or dev product?"""
    del version
    logger = logging.getLogger("promptbeacon")
    if not any(isinstance(h, _CliLogHandler) for h in logger.handlers):
        logger.addHandler(_CliLogHandler(level=logging.WARNING))


if __name__ == "__main__":
    app()
