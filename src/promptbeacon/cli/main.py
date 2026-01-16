"""CLI interface for PromptBeacon."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from promptbeacon.beacon import Beacon
from promptbeacon.core.config import Provider
from promptbeacon.reporting.formats import to_json, to_markdown

app = typer.Typer(
    name="promptbeacon",
    help="LLM visibility monitoring for brands - track how your brand appears in AI-generated responses.",
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
            raise typer.BadParameter(
                f"Invalid provider: {v}. Choose from: openai, anthropic, google"
            )
    return providers


@app.command()
def scan(
    brand: Annotated[str, typer.Argument(help="The brand name to analyze")],
    competitors: Annotated[
        Optional[list[str]],
        typer.Option("--competitor", "-c", help="Competitor brands to compare"),
    ] = None,
    providers: Annotated[
        Optional[list[str]],
        typer.Option("--provider", "-p", help="LLM providers to use (openai, anthropic, google)"),
    ] = None,
    categories: Annotated[
        Optional[list[str]],
        typer.Option("--category", "-t", help="Categories/topics to analyze"),
    ] = None,
    prompt_count: Annotated[
        int,
        typer.Option("--prompts", "-n", help="Number of prompts per category"),
    ] = 10,
    storage: Annotated[
        Optional[Path],
        typer.Option("--storage", "-s", help="Path to DuckDB storage file"),
    ] = None,
    output_format: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Output format"),
    ] = OutputFormat.text,
) -> None:
    """Scan LLM visibility for a brand.

    Example:
        promptbeacon scan "Nike" --competitor "Adidas" --provider openai
    """
    # Build beacon configuration
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

    # Run scan with progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(description=f"Scanning visibility for {brand}...", total=None)
        try:
            report = beacon.scan()
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    # Output results
    if output_format == OutputFormat.json:
        console.print(to_json(report))
    elif output_format == OutputFormat.markdown:
        console.print(to_markdown(report))
    else:
        _print_text_report(report)


@app.command()
def compare(
    brand: Annotated[str, typer.Argument(help="The brand name to analyze")],
    against: Annotated[
        list[str],
        typer.Option("--against", "-a", help="Competitor brands to compare against"),
    ],
    providers: Annotated[
        Optional[list[str]],
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
        progress.add_task(description=f"Comparing {brand} with competitors...", total=None)
        try:
            report = beacon.scan()
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    if output_format == OutputFormat.json:
        console.print(to_json(report))
    elif output_format == OutputFormat.markdown:
        console.print(to_markdown(report))
    else:
        _print_comparison_report(report)


@app.command()
def history(
    brand: Annotated[str, typer.Argument(help="The brand name")],
    days: Annotated[
        int,
        typer.Option("--days", "-d", help="Number of days of history"),
    ] = 30,
    storage: Annotated[
        Optional[Path],
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
        raise typer.Exit(1)

    if output_format == OutputFormat.json:
        console.print(history_report.model_dump_json(indent=2))
    else:
        _print_history_report(history_report)


@app.command()
def providers() -> None:
    """List available LLM providers and their status."""
    from promptbeacon.core.config import has_api_key

    table = Table(title="Available Providers")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Environment Variable")

    env_vars = {
        Provider.OPENAI: "OPENAI_API_KEY",
        Provider.ANTHROPIC: "ANTHROPIC_API_KEY",
        Provider.GOOGLE: "GOOGLE_API_KEY",
    }

    for provider in Provider:
        status = "✓ Configured" if has_api_key(provider) else "✗ Not configured"
        status_style = "green" if has_api_key(provider) else "red"
        table.add_row(
            provider.value,
            f"[{status_style}]{status}[/{status_style}]",
            env_vars.get(provider, ""),
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
