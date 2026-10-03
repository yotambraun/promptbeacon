# CI & Examples

Gating and tracking AI visibility in CI, then practical end-to-end scripts.

## Contents

- [GitHub Action](#github-action)
- [Other CI systems: `promptbeacon ci`](#other-ci-systems-promptbeacon-ci)
- [pytest plugin](#pytest-plugin)
- [Python assertion API](#python-assertion-api)
- [Keyless demo](#keyless-demo)
- [Share of voice comparison](#share-of-voice-comparison)
- [Stability scan](#stability-scan)
- [HTML dashboard](#html-dashboard)
- [Brand monitoring dashboard](#brand-monitoring-dashboard)
- [Competitive intelligence system](#competitive-intelligence-system)
- [PR campaign impact tracking](#pr-campaign-impact-tracking)
- [Multi-brand portfolio management](#multi-brand-portfolio-management)
- [Automated alerting system](#automated-alerting-system)
- [Weekly report generation](#weekly-report-generation)
- [BeaconGuard: brand safety](#beaconguard-brand-safety)

---

## GitHub Action

`yotambraun/promptbeacon@v1` installs PromptBeacon, runs a scan, writes a job summary,
exposes the numbers as step outputs, can write a badge and card, can keep one sticky PR
comment up to date, and applies your thresholds last.

```yaml
- name: Measure AI visibility
  id: beacon
  uses: yotambraun/promptbeacon@v1
  with:
    brand: "Nike"
    category: "running shoes"
    competitors: |
      Adidas
      New Balance
    providers: "openai anthropic"
    min-score: "40"
    min-share-of-voice: "0.15"
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

- run: echo "Score ${{ steps.beacon.outputs.score }}, SoV ${{ steps.beacon.outputs.share-of-voice }}"
```

### Inputs

| Input | Default | Description |
| --- | --- | --- |
| `brand` | (required) | Brand to measure |
| `category` | | Category the prompts ask about; spaces allowed (`running shoes`) |
| `categories` | | Several categories, one per line |
| `competitors` | | Competitors, one per line |
| `providers` | `openai` | Space-separated providers |
| `prompts` | `10` | Prompts per category |
| `min-score` | `0` | Fail below this visibility score (0 = no gate) |
| `min-share-of-voice` | `0` | Fail below this share of voice, 0-1 (0 = no gate) |
| `stability` | `0` | Repeat the scan N times and report stability |
| `min-stability` | `0` | Fail below this stability score (needs `stability`) |
| `demo` | `false` | Keyless demo mode, for smoke tests |
| `grounded` | `false` | Web-grounded scan (provider web search) |
| `badge-path` | | Write an SVG badge here, e.g. `.promptbeacon/badge.svg` |
| `badge-endpoint-path` | | Write a shields.io endpoint JSON here |
| `card-path` | | Write a 1200x630 SVG card here |
| `comment-on-pr` | `false` | Keep one sticky comment on the pull request |
| `github-token` | `${{ github.token }}` | Token for the PR comment |
| `version` | `promptbeacon` | Package spec to install, e.g. `promptbeacon==1.3.0` |

For backward compatibility, a single-line `categories` or `competitors` value is split
on spaces; use one item per line for multi-word names.

### Outputs

| Output | Description |
| --- | --- |
| `score` | Visibility score (0-100) |
| `share-of-voice` | Share of voice (0-1) |
| `rank` | Share-of-voice rank (1 = leader) |
| `presence` | Fraction of answers that mention the brand |
| `stability` | Stability score, when `stability` > 0 |
| `tier` | `demo`, `base_model` or `api_grounded` |
| `passed` | `true` if every threshold passed |
| `report-path` | Path to the full JSON report |

### Job summary

Every run appends a short Markdown report to the job summary: score, share of voice and
rank, a brand table, the thresholds and whether they passed, and how the scan was
measured (tier, models, prompts, estimated cost).

### Sticky PR comment

With `comment-on-pr: "true"` the Action posts the same summary as a pull-request
comment, then edits that comment in place on later pushes (it is found by a hidden
marker). It only runs on `pull_request` events, needs `pull-requests: write`, and never
fails the job: on forks without write permission it logs a warning instead.

```yaml
on:
  pull_request:

permissions:
  contents: read
  pull-requests: write

jobs:
  visibility:
    runs-on: ubuntu-latest
    steps:
      - uses: yotambraun/promptbeacon@v1
        with:
          brand: "Your Product"
          category: "your category"
          min-share-of-voice: "0.2"
          comment-on-pr: "true"
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

### Templates

- [ai-visibility-weekly.yml](https://github.com/yotambraun/promptbeacon/blob/main/examples/workflows/ai-visibility-weekly.yml)
  — weekly scan that commits a refreshed badge, badge JSON and card
  (`permissions: contents: write`). See [Badges & share cards](share.md).
- [ai-visibility-pr.yml](https://github.com/yotambraun/promptbeacon/blob/main/examples/workflows/ai-visibility-pr.yml)
  — pull-request check with a sticky comment.

Each real run is billed to the key in your secrets. `demo: "true"` gives a free dry run.

---

## Other CI systems: `promptbeacon ci`

The Action is a thin wrapper around two CLI calls that work anywhere:

```bash
promptbeacon scan "Nike" -t "running shoes" -c "Adidas" -f json --no-save > report.json
promptbeacon ci --report report.json --min-score 40 --min-sov 0.15
```

`ci` prints the Markdown summary (or writes it to `$GITHUB_STEP_SUMMARY` and outputs to
`$GITHUB_OUTPUT` on GitHub), writes a PR-comment body with `--comment-file`, and exits 1
if a threshold is missed, after writing everything. In one step, `scan` also accepts
`--assert-min-score`, `--assert-min-sov` and `--assert-min-stability`.

---

## pytest plugin

The plugin registers automatically (no conftest needed):

```python
# tests/test_brand_visibility.py
import pytest


@pytest.mark.visibility(
    brand="Nike",
    categories=["running shoes"],
    competitors=["Adidas", "Puma"],
    min_score=40,
    min_share_of_voice=0.15,
)
def test_nike_visibility_thresholds():
    pass
```

```bash
PROMPTBEACON_DEMO=1 pytest tests/test_brand_visibility.py -v   # keyless
pytest tests/test_brand_visibility.py -v                        # real keys
```

Without keys and without `PROMPTBEACON_DEMO=1` (or `demo=True` on the marker), marked
tests are skipped. A missed threshold is reported as a normal test failure. The marker
also accepts `providers`, `prompt_count`, `stability`, `min_presence_rate`,
`min_stability_score` and `max_rank`; the `beacon` fixture builds a configured Beacon.

---

## Python assertion API

```python
import sys

from promptbeacon import Beacon, Provider
from promptbeacon.core.exceptions import VisibilityAssertionError

report = (
    Beacon("Nike")
    .with_category("running shoes")
    .with_competitors("Adidas", "Puma")
    .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
    .scan()
)

try:
    report.assert_visibility(
        min_score=40, min_share_of_voice=0.15, min_presence_rate=0.5, max_rank=3
    )
    print(f"Visibility check passed (score={report.visibility_score:.1f})")
except VisibilityAssertionError as e:
    for failure in e.failures:
        print(f"  - {failure}")
    sys.exit(1)
```

---

## Keyless demo

```bash
promptbeacon demo "Nike" -t "running shoes" -c "Adidas" -c "Puma"
```

```python
from promptbeacon import Beacon

report = (
    Beacon("Nike")
    .demo()
    .with_category("running shoes")
    .with_competitors("Adidas", "Puma")
    .scan()
)

sov = report.share_of_voice
print(f"Visibility score: {report.visibility_score}/100")
print(f"Share of voice:   {sov.target_share:.0%} (rank #{sov.target_rank})")
print(f"Presence rate:    {sov.target_presence_rate:.0%}")
for brand, entry in sov.aggregate.items():
    print(f"  {brand}: {entry.share_of_voice:.0%}")

report.assert_visibility(min_score=30, min_share_of_voice=0.1)
```

---

## Share of voice comparison

```python
from promptbeacon import Beacon, Provider

report = (
    Beacon("Nike")
    .with_category("running shoes")
    .with_competitors("Adidas", "Puma", "New Balance", "Under Armour")
    .with_providers(Provider.OPENAI, Provider.ANTHROPIC, Provider.GOOGLE)
    .with_prompt_count(15)
    .scan()
)

sov = report.share_of_voice
print(f"Target: {sov.target_share:.0%} | Presence: {sov.target_presence_rate:.0%}")

for brand, entry in sorted(
    sov.aggregate.items(), key=lambda x: x[1].share_of_voice, reverse=True
):
    bar = "#" * int(entry.share_of_voice * 40)
    print(f"  {brand:<20} {entry.share_of_voice:.0%}  {bar}")

# Per-provider: provider -> brand -> entry
for provider_name, entries in sov.by_provider.items():
    mine = entries.get(report.brand)
    if mine:
        print(f"  {provider_name}: {mine.share_of_voice:.0%}")
```

```bash
promptbeacon compare "Nike" -t "running shoes" -a "Adidas" -a "Puma" \
  -p openai -p anthropic -f json > comparison.json
```

---

## Stability scan

```python
from promptbeacon import Beacon, Provider

report = (
    Beacon("Nike")
    .with_category("running shoes")
    .with_competitors("Adidas", "Puma")
    .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
    .with_stability(5)  # 5 independent runs
    .with_temperature(0.7)  # non-zero, or the runs will not vary
    .scan_stability()
)

s = report.stability
print(f"Stability score: {s.stability_score:.1f}/100 ({s.volatility.stability_rating})")
lo, hi = s.score_confidence_interval
print(f"95% CI: [{lo:.1f}, {hi:.1f}]  flip-flops: {s.flip_flop_count}")
```

```bash
promptbeacon scan "Nike" -t "running shoes" --stability 5
promptbeacon scan "Nike" -t "running shoes" --stability 3 --demo   # explore for free
```

`--stability 5` multiplies API calls (and cost) by 5.

---

## HTML dashboard

```python
from promptbeacon import Beacon, Provider, to_dashboard_html

beacon = (
    Beacon("Nike")
    .with_category("running shoes")
    .with_competitors("Adidas", "Puma")
    .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
    .with_storage("~/.promptbeacon/nike.db")
)

report = beacon.scan()
history = beacon.get_history(days=30)

with open("nike_dashboard.html", "w", encoding="utf-8") as f:
    f.write(to_dashboard_html(report, history=history))  # includes a trend sparkline
```

```bash
promptbeacon dashboard "Nike" -t "running shoes" -c "Adidas" --demo -o report.html
promptbeacon dashboard "Nike" -t "running shoes" -c "Adidas" -p openai --no-open
```

---

## Brand monitoring dashboard

A complete brand monitoring solution with daily scans, historical tracking, and alerts.

```python
#!/usr/bin/env python3
"""Brand Monitoring Dashboard

Daily brand visibility monitoring with historical tracking and alerts.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from promptbeacon import Beacon, Provider, to_json, to_markdown, to_dashboard_html
from rich.console import Console
from rich.table import Table

console = Console()


class BrandMonitor:
    """Automated brand monitoring system."""

    def __init__(
        self, brand: str, category: str, competitors: list[str], storage_path: str
    ):
        self.brand = brand
        self.competitors = competitors
        self.storage_path = storage_path

        self.beacon = (
            Beacon(brand)
            .with_category(category)
            .with_aliases(f"{brand} Inc", f"{brand} Corporation")
            .with_competitors(*competitors)
            .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
            .with_cache()
            .with_storage(storage_path)
        )

    async def run_daily_scan(self):
        """Execute daily brand scan."""
        console.print(f"\n[bold]Starting daily scan for {self.brand}[/bold]")
        console.print(f"Time: {datetime.now()}")

        report = await self.beacon.scan_async()

        self._save_reports(report)
        self._check_alerts(report)
        self._display_summary(report)

        return report

    def _save_reports(self, report):
        """Save reports in multiple formats."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("./reports") / self.brand
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir / f"report_{timestamp}.json", "w") as f:
            f.write(to_json(report))

        with open(output_dir / f"report_{timestamp}.md", "w") as f:
            f.write(to_markdown(report))

        history = self.beacon.get_history(days=30)
        with open(output_dir / f"dashboard_{timestamp}.html", "w") as f:
            f.write(to_dashboard_html(report, history=history))

        console.print(f"Reports saved to {output_dir}")

    def _check_alerts(self, report):
        """Check for alert conditions."""
        comparison = self.beacon.compare_with_previous()

        if comparison:
            if comparison.score_change < -5:
                console.print(
                    f"[red]ALERT: Visibility dropped {comparison.score_change:.1f} points[/red]"
                )
            elif comparison.score_change > 5:
                console.print(
                    f"[green]Visibility increased {comparison.score_change:+.1f} points[/green]"
                )

        if report.sentiment_breakdown.negative > 0.2:
            console.print(
                f"[yellow]ALERT: Negative sentiment at {report.sentiment_breakdown.negative:.0%}[/yellow]"
            )

    def _display_summary(self, report):
        """Display scan summary."""
        table = Table(title=f"{self.brand} Scan Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        sov = report.share_of_voice
        table.add_row("Visibility Score", f"{report.visibility_score:.1f}/100")
        table.add_row(
            "Share of Voice", f"{sov.target_share:.0%} (rank #{sov.target_rank})"
        )
        table.add_row("Presence Rate", f"{sov.target_presence_rate:.0%}")
        table.add_row("Mentions", str(report.mention_count))
        table.add_row(
            "Positive Sentiment", f"{report.sentiment_breakdown.positive:.0%}"
        )
        table.add_row("Providers", ", ".join(report.providers_used))
        table.add_row("Duration", f"{report.scan_duration_seconds:.1f}s")

        if report.total_cost_usd:
            table.add_row("Cost", f"${report.total_cost_usd:.4f}")

        console.print("\n", table)

        if report.competitor_comparison:
            comp_table = Table(title="Competitor Comparison")
            comp_table.add_column("Brand", style="cyan")
            comp_table.add_column("Score")
            comp_table.add_column("SoV")
            comp_table.add_column("Mentions")

            comp_table.add_row(
                f"[bold]{self.brand}[/bold]",
                f"[bold]{report.visibility_score:.1f}[/bold]",
                f"[bold]{sov.target_share:.0%}[/bold]",
                f"[bold]{report.mention_count}[/bold]",
            )

            for name, score in report.competitor_comparison.items():
                comp_entry = sov.aggregate.get(name)
                sov_str = f"{comp_entry.share_of_voice:.0%}" if comp_entry else "-"
                comp_table.add_row(
                    name,
                    f"{score.visibility_score:.1f}",
                    sov_str,
                    str(score.mention_count),
                )

            console.print("\n", comp_table)

    def get_weekly_summary(self):
        """Generate weekly summary."""
        history = self.beacon.get_history(days=7)

        if not history.data_points:
            console.print("No data for weekly summary")
            return

        console.print(f"\n[bold]Weekly Summary: {self.brand}[/bold]")
        console.print(f"Average Score: {history.average_score:.1f}")
        console.print(f"Trend: {history.trend_direction}")
        console.print(f"Volatility: {history.volatility:.2f}")


async def main():
    monitor = BrandMonitor(
        brand="Nike",
        category="running shoes",
        competitors=["Adidas", "Puma", "New Balance"],
        storage_path="~/.promptbeacon/nike.db",
    )

    await monitor.run_daily_scan()
    monitor.get_weekly_summary()


if __name__ == "__main__":
    asyncio.run(main())
```

### Cron Setup

```bash
# Run daily at 8 AM
0 8 * * * /usr/bin/python3 /path/to/brand_monitor.py
```

---

## Competitive intelligence system

Track multiple competitors with detailed analysis and reporting.

```python
#!/usr/bin/env python3
"""Competitive Intelligence System"""

import asyncio
from datetime import datetime
from promptbeacon import Beacon, Provider
import pandas as pd
from pathlib import Path


class CompetitiveIntelligence:
    def __init__(self, brands: list[str], categories: list[str]):
        self.brands = brands
        self.categories = categories
        self.storage_path = "~/.promptbeacon/competitive.db"

    async def run_competitive_scan(self):
        results = []

        for brand in self.brands:
            print(f"\nScanning {brand}...")

            beacon = (
                Beacon(brand)
                .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
                .with_categories(*self.categories)
                .with_storage(self.storage_path)
                .with_prompt_count(15)
                .with_competitors(*[b for b in self.brands if b != brand])
            )

            report = await beacon.scan_async()
            sov = report.share_of_voice

            results.append(
                {
                    "brand": brand,
                    "score": report.visibility_score,
                    "sov": sov.target_share,
                    "presence_rate": sov.target_presence_rate,
                    "rank": sov.target_rank,
                    "mentions": report.mention_count,
                    "positive": report.sentiment_breakdown.positive,
                    "negative": report.sentiment_breakdown.negative,
                    "timestamp": report.timestamp,
                }
            )

        return pd.DataFrame(results)

    def generate_competitive_report(self, df: pd.DataFrame):
        output_dir = Path("./competitive_reports")
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        df.to_csv(output_dir / f"competitive_data_{timestamp}.csv", index=False)

        report_md = f"""# Competitive Intelligence Report

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Executive Summary

- **Brands Analyzed**: {len(df)}
- **Categories**: {", ".join(self.categories)}
- **Market Leader (Score)**: {df.loc[df["score"].idxmax(), "brand"]} ({df["score"].max():.1f})
- **Market Leader (SoV)**: {df.loc[df["sov"].idxmax(), "brand"]} ({df["sov"].max():.0%})

## Brand Rankings

| Rank | Brand | Score | Share of Voice | Presence Rate | Positive % |
|------|-------|-------|----------------|---------------|------------|
"""
        for idx, row in df.sort_values("score", ascending=False).iterrows():
            rank = df.sort_values("score", ascending=False).index.get_loc(idx) + 1
            report_md += f"| {rank} | {row['brand']} | {row['score']:.1f} | {row['sov']:.0%} | {row['presence_rate']:.0%} | {row['positive']:.0%} |\n"

        filepath = output_dir / f"report_{timestamp}.md"
        with open(filepath, "w") as f:
            f.write(report_md)

        print(f"\nReport generated in {output_dir}")


async def main():
    ci = CompetitiveIntelligence(
        brands=["Nike", "Adidas", "Puma", "New Balance", "Under Armour"],
        categories=["running shoes", "athletic wear", "sports brand"],
    )

    df = await ci.run_competitive_scan()
    ci.generate_competitive_report(df)
    print("\nCompetitive Intelligence Scan Complete!")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## PR campaign impact tracking

Track brand visibility before, during, and after PR campaigns.

```python
#!/usr/bin/env python3
"""PR Campaign Impact Tracker"""

from promptbeacon import Beacon
from datetime import datetime


class CampaignTracker:
    def __init__(self, brand: str, category: str, campaign_start: datetime):
        self.brand = brand
        self.campaign_start = campaign_start
        self.beacon = (
            Beacon(brand)
            .with_category(category)
            .with_storage("~/.promptbeacon/campaigns.db")
        )

    def track_campaign(self, days_before: int = 7, days_after: int = 14):
        history = self.beacon.get_history(days=days_before + days_after)

        if not history.data_points:
            print("Insufficient historical data")
            return

        pre_campaign = [
            dp for dp in history.data_points if dp.timestamp < self.campaign_start
        ]
        post_campaign = [
            dp for dp in history.data_points if dp.timestamp >= self.campaign_start
        ]

        pre_avg = (
            sum(dp.visibility_score for dp in pre_campaign) / len(pre_campaign)
            if pre_campaign
            else 0
        )
        post_avg = (
            sum(dp.visibility_score for dp in post_campaign) / len(post_campaign)
            if post_campaign
            else 0
        )
        impact = post_avg - pre_avg

        print(f"\n{self.brand} Campaign Impact Analysis")
        print("=" * 50)
        print(f"Campaign Start: {self.campaign_start}")
        print(f"\nPre-Campaign Average: {pre_avg:.1f}")
        print(f"Post-Campaign Average: {post_avg:.1f}")
        print(f"Impact: {impact:+.1f} points")

        if impact > 2:
            print("Status: Positive impact detected")
        elif impact < -2:
            print("Status: Negative impact detected")
        else:
            print("Status: No significant impact")

        return {"pre_avg": pre_avg, "post_avg": post_avg, "impact": impact}


if __name__ == "__main__":
    tracker = CampaignTracker(
        brand="Nike",
        category="running shoes",
        campaign_start=datetime(2026, 1, 10),
    )

    results = tracker.track_campaign(days_before=7, days_after=14)
```

---

## Multi-brand portfolio management

```python
#!/usr/bin/env python3
"""Multi-Brand Portfolio Manager"""

import asyncio
from promptbeacon import Beacon, Provider
from rich.console import Console
from rich.table import Table

console = Console()


class PortfolioManager:
    def __init__(self, brands: dict[str, tuple[str, list[str]]]):
        self.brands = brands
        self.storage_path = "~/.promptbeacon/portfolio.db"

    async def scan_portfolio(self):
        results = {}

        for brand, (category, competitors) in self.brands.items():
            console.print(f"\n[cyan]Scanning {brand}...[/cyan]")

            beacon = (
                Beacon(brand)
                .with_category(category)
                .with_competitors(*competitors)
                .with_providers(Provider.OPENAI)
                .with_storage(self.storage_path)
                .with_prompt_count(10)
            )

            report = await beacon.scan_async()
            results[brand] = report

        return results

    def display_portfolio_summary(self, results: dict):
        table = Table(title="Portfolio Summary")
        table.add_column("Brand", style="cyan")
        table.add_column("Score")
        table.add_column("SoV")
        table.add_column("Rank")
        table.add_column("Sentiment")
        table.add_column("Status")

        for brand, report in results.items():
            sov = report.share_of_voice

            if report.visibility_score >= 70:
                status = "[green]Excellent[/green]"
            elif report.visibility_score >= 50:
                status = "[yellow]Good[/yellow]"
            else:
                status = "[red]Needs Attention[/red]"

            table.add_row(
                brand,
                f"{report.visibility_score:.1f}",
                f"{sov.target_share:.0%}",
                f"#{sov.target_rank}",
                f"{report.sentiment_breakdown.positive:.0%}",
                status,
            )

        console.print("\n", table)


async def main():
    portfolio = {
        "Brand A": ("project management software", ["Competitor A1", "Competitor A2"]),
        "Brand B": ("crm software", ["Competitor B1", "Competitor B2"]),
    }

    manager = PortfolioManager(portfolio)
    console.print("[bold]Starting Portfolio Scan...[/bold]")
    results = await manager.scan_portfolio()
    manager.display_portfolio_summary(results)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Automated alerting system

```python
#!/usr/bin/env python3
"""Automated Alerting System"""

from promptbeacon import Beacon
import requests


class AlertSystem:
    def __init__(self, brand: str, category: str, slack_webhook: str | None = None):
        self.brand = brand
        self.slack_webhook = slack_webhook
        self.beacon = (
            Beacon(brand)
            .with_category(category)
            .with_storage("~/.promptbeacon/alerts.db")
        )

    def monitor_and_alert(self, thresholds: dict = None):
        if thresholds is None:
            thresholds = {
                "score_drop": -5.0,
                "score_increase": 5.0,
                "negative_sentiment": 0.2,
                "low_score": 40.0,
                "low_sov": 0.1,
            }

        report = self.beacon.scan()
        alerts = self._check_thresholds(report, thresholds)

        for alert in alerts:
            self._send_alert(alert)

        return alerts

    def _check_thresholds(self, report, thresholds):
        alerts = []
        sov = report.share_of_voice

        comparison = self.beacon.compare_with_previous()
        if comparison:
            if comparison.score_change <= thresholds["score_drop"]:
                alerts.append(
                    {
                        "severity": "high",
                        "type": "score_drop",
                        "message": f"Visibility dropped by {abs(comparison.score_change):.1f} points",
                    }
                )
            elif comparison.score_change >= thresholds["score_increase"]:
                alerts.append(
                    {
                        "severity": "info",
                        "type": "score_increase",
                        "message": f"Visibility increased by {comparison.score_change:.1f} points",
                    }
                )

        if report.sentiment_breakdown.negative >= thresholds["negative_sentiment"]:
            alerts.append(
                {
                    "severity": "medium",
                    "type": "negative_sentiment",
                    "message": f"Negative sentiment at {report.sentiment_breakdown.negative:.0%}",
                }
            )

        if report.visibility_score <= thresholds["low_score"]:
            alerts.append(
                {
                    "severity": "high",
                    "type": "low_score",
                    "message": f"Visibility score below threshold: {report.visibility_score:.1f}",
                }
            )

        if sov.target_share <= thresholds.get("low_sov", 0):
            alerts.append(
                {
                    "severity": "medium",
                    "type": "low_sov",
                    "message": f"Share of Voice below threshold: {sov.target_share:.0%}",
                }
            )

        return alerts

    def _send_alert(self, alert: dict):
        print(f"\nALERT [{alert['severity'].upper()}]: {alert['message']}")

        if self.slack_webhook:
            payload = {"text": f"Brand Alert: {self.brand} — {alert['message']}"}
            try:
                requests.post(self.slack_webhook, json=payload)
            except Exception as e:
                print(f"Slack alert failed: {e}")


if __name__ == "__main__":
    alert_system = AlertSystem(
        brand="Nike",
        category="running shoes",
        slack_webhook="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    )

    alerts = alert_system.monitor_and_alert()
    if alerts:
        print(f"\n{len(alerts)} alert(s) triggered")
    else:
        print("\nNo alerts — all metrics within thresholds")
```

---

## Weekly report generation

```python
#!/usr/bin/env python3
"""Weekly Report Generator"""

from promptbeacon import Beacon, to_markdown, to_dashboard_html
from datetime import datetime
from pathlib import Path


class WeeklyReporter:
    def __init__(self, brand: str, category: str, competitors: list[str]):
        self.brand = brand
        self.competitors = competitors
        self.beacon = (
            Beacon(brand)
            .with_category(category)
            .with_competitors(*competitors)
            .with_storage("~/.promptbeacon/weekly.db")
        )

    def generate_weekly_report(self):
        current_report = self.beacon.scan()
        history = self.beacon.get_history(days=7)

        sov = current_report.share_of_voice

        report = f"""# Weekly Visibility Report: {self.brand}

**Report Period:** {datetime.now().strftime("%Y-%m-%d")}
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Executive Summary

- **Current Visibility Score:** {current_report.visibility_score:.1f}/100
- **Share of Voice:** {sov.target_share:.0%} (rank #{sov.target_rank})
- **Presence Rate:** {sov.target_presence_rate:.0%}
- **Total Mentions:** {current_report.mention_count}
- **Positive Sentiment:** {current_report.sentiment_breakdown.positive:.0%}
"""

        if history.data_points:
            report += f"- **7-Day Trend:** {history.trend_direction.upper()}\n"
            report += f"- **7-Day Average:** {history.average_score:.1f}\n"

        report += "\n## Competitive Analysis\n\n"
        report += "| Brand | Score | SoV | Mentions | Positive % |\n"
        report += "|-------|-------|-----|----------|------------|\n"
        report += f"| **{self.brand}** | **{current_report.visibility_score:.1f}** | **{sov.target_share:.0%}** | **{current_report.mention_count}** | **{current_report.sentiment_breakdown.positive:.0%}** |\n"

        for name, score in sorted(
            current_report.competitor_comparison.items(),
            key=lambda x: x[1].visibility_score,
            reverse=True,
        ):
            comp_entry = sov.aggregate.get(name)
            sov_str = f"{comp_entry.share_of_voice:.0%}" if comp_entry else "-"
            report += f"| {name} | {score.visibility_score:.1f} | {sov_str} | {score.mention_count} | {score.sentiment.positive:.0%} |\n"

        if current_report.recommendations:
            report += "\n## Recommendations\n\n"
            for rec in current_report.recommendations[:5]:
                report += f"### [{rec.priority.upper()}] {rec.action}\n\n"
                report += f"**Rationale:** {rec.rationale}\n\n"
                if rec.expected_impact:
                    report += f"**Expected Impact:** {rec.expected_impact}\n\n"

        # Save markdown
        output_dir = Path("./weekly_reports")
        output_dir.mkdir(exist_ok=True)
        filename = f"weekly_report_{self.brand}_{datetime.now().strftime('%Y%m%d')}"

        with open(output_dir / f"{filename}.md", "w") as f:
            f.write(report)

        # Save HTML dashboard
        with open(output_dir / f"{filename}.html", "w") as f:
            f.write(to_dashboard_html(current_report, history=history))

        print(f"Reports saved to {output_dir}")
        return report


if __name__ == "__main__":
    reporter = WeeklyReporter(
        brand="Nike",
        category="running shoes",
        competitors=["Adidas", "Puma", "New Balance"],
    )

    report = reporter.generate_weekly_report()
    print(report)
```

---

## BeaconGuard: brand safety

Real-time brand safety analysis for LLM outputs — no API calls needed.

### Basic Guard

```python
from promptbeacon import BeaconGuard

guard = BeaconGuard("Nike", competitors=["Adidas", "Puma"])

responses = [
    "I recommend Nike for running shoes. Great quality and innovation.",
    "Try Adidas instead — Nike has had quality issues lately.",
    "Popular running brands include Brooks, Asics, and Saucony.",
]

for response in responses:
    result = guard.analyze(response)
    print(f"Risk: {result.risk_level} | Flags: {result.flags}")
```

### Guard as Middleware

```python
from promptbeacon import BeaconGuard
from promptbeacon.integrations.middleware import BeaconGuardMiddleware

guard = BeaconGuard("Acme", competitors=["CompetitorX"])
middleware = BeaconGuardMiddleware(
    guard, on_high_risk=lambda r: print(f"ALERT: {r.flags}")
)

result = middleware("I'd suggest CompetitorX over Acme for this use case.")
print(f"Risk: {result.risk_level}")
```

See the [examples directory](https://github.com/yotambraun/promptbeacon/tree/main/examples) for runnable scripts: `guard_example.py` and `langchain_guard.py`.

---

## See Also

- [Quickstart Guide](quickstart.md) - Getting started
- [API Reference](api-reference.md) - Complete API documentation
- [Advanced Usage](advanced.md) - Advanced patterns
- [CLI Reference](cli.md) - Command-line tools
- [Storage Guide](storage.md) - Data management
