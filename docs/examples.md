# Real-World Examples

Practical, production-ready examples for common PromptBeacon use cases.

## Table of Contents

- [Brand Monitoring Dashboard](#brand-monitoring-dashboard)
- [Competitive Intelligence System](#competitive-intelligence-system)
- [PR Campaign Impact Tracking](#pr-campaign-impact-tracking)
- [Multi-Brand Portfolio Management](#multi-brand-portfolio-management)
- [Automated Alerting System](#automated-alerting-system)
- [Weekly Report Generation](#weekly-report-generation)
- [Market Leader Analysis](#market-leader-analysis)
- [Sentiment Tracking](#sentiment-tracking)

---

## Brand Monitoring Dashboard

A complete brand monitoring solution with daily scans, historical tracking, and alerts.

### Complete Implementation

```python
#!/usr/bin/env python3
"""Brand Monitoring Dashboard

Daily brand visibility monitoring with historical tracking and alerts.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from promptbeacon import Beacon, Provider, to_json, to_markdown
from rich.console import Console
from rich.table import Table
import smtplib
from email.mime.text import MIMEText

console = Console()

class BrandMonitor:
    """Automated brand monitoring system."""

    def __init__(self, brand: str, competitors: list[str], storage_path: str):
        self.brand = brand
        self.competitors = competitors
        self.storage_path = storage_path

        self.beacon = (
            Beacon(brand)
            .with_competitors(*competitors)
            .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
            .with_storage(storage_path)
            .with_prompt_count(15)
        )

    async def run_daily_scan(self):
        """Execute daily brand scan."""
        console.print(f"\n[bold]Starting daily scan for {self.brand}[/bold]")
        console.print(f"Time: {datetime.now()}")

        # Run scan
        report = await self.beacon.scan_async()

        # Save reports
        self._save_reports(report)

        # Check for alerts
        self._check_alerts(report)

        # Display summary
        self._display_summary(report)

        return report

    def _save_reports(self, report):
        """Save reports in multiple formats."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("./reports") / self.brand
        output_dir.mkdir(parents=True, exist_ok=True)

        # JSON
        with open(output_dir / f"report_{timestamp}.json", "w") as f:
            f.write(to_json(report))

        # Markdown
        with open(output_dir / f"report_{timestamp}.md", "w") as f:
            f.write(to_markdown(report))

        console.print(f"✓ Reports saved to {output_dir}")

    def _check_alerts(self, report):
        """Check for alert conditions."""
        comparison = self.beacon.compare_with_previous()

        if comparison:
            # Significant score drop
            if comparison.score_change < -5:
                self._send_alert(
                    subject=f"⚠️ {self.brand} Visibility Drop",
                    message=f"""
                    Brand visibility has dropped significantly.

                    Current Score: {comparison.current_score:.1f}
                    Previous Score: {comparison.previous_score:.1f}
                    Change: {comparison.score_change:.1f} points

                    Direction: {comparison.change_direction}
                    Time: {datetime.now()}
                    """,
                )

            # Significant score increase
            elif comparison.score_change > 5:
                self._send_alert(
                    subject=f"✓ {self.brand} Visibility Increase",
                    message=f"""
                    Brand visibility has increased significantly!

                    Current Score: {comparison.current_score:.1f}
                    Previous Score: {comparison.previous_score:.1f}
                    Change: {comparison.score_change:+.1f} points

                    Direction: {comparison.change_direction}
                    Time: {datetime.now()}
                    """,
                )

        # Low sentiment alert
        if report.sentiment_breakdown.negative > 0.2:
            self._send_alert(
                subject=f"⚠️ {self.brand} Negative Sentiment Alert",
                message=f"""
                Negative sentiment is higher than usual.

                Negative: {report.sentiment_breakdown.negative:.0%}
                Positive: {report.sentiment_breakdown.positive:.0%}
                Neutral: {report.sentiment_breakdown.neutral:.0%}

                Time: {datetime.now()}
                """,
            )

    def _send_alert(self, subject: str, message: str):
        """Send email alert."""
        console.print(f"\n[yellow]ALERT: {subject}[/yellow]")
        console.print(message)

        # Implement email sending
        # smtp_server = "smtp.gmail.com"
        # smtp_port = 587
        # sender = "alerts@company.com"
        # recipient = "team@company.com"
        # password = os.environ.get("SMTP_PASSWORD")
        #
        # msg = MIMEText(message)
        # msg['Subject'] = subject
        # msg['From'] = sender
        # msg['To'] = recipient
        #
        # with smtplib.SMTP(smtp_server, smtp_port) as server:
        #     server.starttls()
        #     server.login(sender, password)
        #     server.send_message(msg)

    def _display_summary(self, report):
        """Display scan summary."""
        table = Table(title=f"{self.brand} Scan Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Visibility Score", f"{report.visibility_score:.1f}/100")
        table.add_row("Mentions", str(report.mention_count))
        table.add_row("Positive Sentiment", f"{report.sentiment_breakdown.positive:.0%}")
        table.add_row("Providers", ", ".join(report.providers_used))
        table.add_row("Duration", f"{report.scan_duration_seconds:.1f}s")

        if report.total_cost_usd:
            table.add_row("Cost", f"${report.total_cost_usd:.4f}")

        console.print("\n", table)

        # Competitor comparison
        if report.competitor_comparison:
            comp_table = Table(title="Competitor Comparison")
            comp_table.add_column("Brand", style="cyan")
            comp_table.add_column("Score")
            comp_table.add_column("Mentions")

            # Add main brand
            comp_table.add_row(
                f"[bold]{self.brand}[/bold]",
                f"[bold]{report.visibility_score:.1f}[/bold]",
                f"[bold]{report.mention_count}[/bold]",
            )

            # Add competitors
            for name, score in report.competitor_comparison.items():
                comp_table.add_row(
                    name,
                    f"{score.visibility_score:.1f}",
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

        # Daily breakdown
        table = Table(title="Daily Scores")
        table.add_column("Date")
        table.add_column("Score")
        table.add_column("Change")

        for i, dp in enumerate(history.data_points):
            if i > 0:
                change = dp.visibility_score - history.data_points[i-1].visibility_score
                change_str = f"{change:+.1f}"
            else:
                change_str = "-"

            table.add_row(
                dp.timestamp.strftime("%Y-%m-%d"),
                f"{dp.visibility_score:.1f}",
                change_str,
            )

        console.print("\n", table)


async def main():
    """Main monitoring function."""
    monitor = BrandMonitor(
        brand="Nike",
        competitors=["Adidas", "Puma", "New Balance"],
        storage_path="~/.promptbeacon/nike.db",
    )

    # Run daily scan
    await monitor.run_daily_scan()

    # Generate weekly summary
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

## Competitive Intelligence System

Track multiple competitors with detailed analysis and reporting.

```python
#!/usr/bin/env python3
"""Competitive Intelligence System

Track multiple competitors across categories with detailed analysis.
"""

import asyncio
from datetime import datetime
from promptbeacon import Beacon, Provider
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

class CompetitiveIntelligence:
    """Competitive intelligence tracking system."""

    def __init__(self, brands: list[str], categories: list[str]):
        self.brands = brands
        self.categories = categories
        self.storage_path = "~/.promptbeacon/competitive.db"

    async def run_competitive_scan(self):
        """Scan all brands and categories."""
        results = []

        for brand in self.brands:
            print(f"\nScanning {brand}...")

            beacon = (
                Beacon(brand)
                .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
                .with_categories(*self.categories)
                .with_storage(self.storage_path)
                .with_prompt_count(15)
            )

            # Add other brands as competitors
            competitors = [b for b in self.brands if b != brand]
            beacon = beacon.with_competitors(*competitors)

            report = await beacon.scan_async()

            results.append({
                "brand": brand,
                "score": report.visibility_score,
                "mentions": report.mention_count,
                "positive": report.sentiment_breakdown.positive,
                "neutral": report.sentiment_breakdown.neutral,
                "negative": report.sentiment_breakdown.negative,
                "timestamp": report.timestamp,
            })

        return pd.DataFrame(results)

    def generate_competitive_report(self, df: pd.DataFrame):
        """Generate comprehensive competitive report."""
        output_dir = Path("./competitive_reports")
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save data
        df.to_csv(output_dir / f"competitive_data_{timestamp}.csv", index=False)

        # Generate visualizations
        self._create_visualizations(df, output_dir, timestamp)

        # Generate markdown report
        self._create_markdown_report(df, output_dir, timestamp)

        print(f"\nReport generated in {output_dir}")

    def _create_visualizations(self, df: pd.DataFrame, output_dir: Path, timestamp: str):
        """Create competitive visualizations."""
        # Visibility scores
        plt.figure(figsize=(10, 6))
        df.plot(x="brand", y="score", kind="bar", legend=False)
        plt.title("Brand Visibility Scores")
        plt.xlabel("Brand")
        plt.ylabel("Visibility Score")
        plt.tight_layout()
        plt.savefig(output_dir / f"scores_{timestamp}.png")
        plt.close()

        # Sentiment comparison
        fig, ax = plt.subplots(figsize=(12, 6))
        x = range(len(df))
        width = 0.25

        ax.bar([i - width for i in x], df["positive"], width, label="Positive")
        ax.bar(x, df["neutral"], width, label="Neutral")
        ax.bar([i + width for i in x], df["negative"], width, label="Negative")

        ax.set_xlabel("Brand")
        ax.set_ylabel("Sentiment Proportion")
        ax.set_title("Sentiment Comparison")
        ax.set_xticks(x)
        ax.set_xticklabels(df["brand"])
        ax.legend()

        plt.tight_layout()
        plt.savefig(output_dir / f"sentiment_{timestamp}.png")
        plt.close()

    def _create_markdown_report(self, df: pd.DataFrame, output_dir: Path, timestamp: str):
        """Create markdown report."""
        report = f"""# Competitive Intelligence Report

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Executive Summary

- **Brands Analyzed**: {len(df)}
- **Categories**: {", ".join(self.categories)}
- **Market Leader**: {df.loc[df['score'].idxmax(), 'brand']} ({df['score'].max():.1f})

## Brand Rankings

| Rank | Brand | Visibility Score | Mentions | Positive % |
|------|-------|------------------|----------|------------|
"""

        for idx, row in df.sort_values("score", ascending=False).iterrows():
            rank = df.sort_values("score", ascending=False).index.get_loc(idx) + 1
            report += f"| {rank} | {row['brand']} | {row['score']:.1f} | {row['mentions']} | {row['positive']:.0%} |\n"

        report += f"""
## Insights

### Top Performer
{df.loc[df['score'].idxmax(), 'brand']} leads with a visibility score of {df['score'].max():.1f}.

### Most Positive Sentiment
{df.loc[df['positive'].idxmax(), 'brand']} has the highest positive sentiment at {df['positive'].max():.0%}.

### Most Mentions
{df.loc[df['mentions'].idxmax(), 'brand']} received the most mentions ({df['mentions'].max()}).

## Visualizations

![Visibility Scores](scores_{timestamp}.png)
![Sentiment Comparison](sentiment_{timestamp}.png)
"""

        with open(output_dir / f"report_{timestamp}.md", "w") as f:
            f.write(report)


async def main():
    """Run competitive intelligence scan."""
    ci = CompetitiveIntelligence(
        brands=["Nike", "Adidas", "Puma", "New Balance", "Under Armour"],
        categories=["running shoes", "athletic wear", "sports brand"],
    )

    # Run scan
    df = await ci.run_competitive_scan()

    # Generate report
    ci.generate_competitive_report(df)

    print("\nCompetitive Intelligence Scan Complete!")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## PR Campaign Impact Tracking

Track brand visibility before, during, and after PR campaigns.

```python
#!/usr/bin/env python3
"""PR Campaign Impact Tracker

Track brand visibility changes during PR campaigns.
"""

from promptbeacon import Beacon
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt

class CampaignTracker:
    """Track PR campaign impact on brand visibility."""

    def __init__(self, brand: str, campaign_start: datetime):
        self.brand = brand
        self.campaign_start = campaign_start
        self.beacon = Beacon(brand).with_storage("~/.promptbeacon/campaigns.db")

    def track_campaign(self, days_before: int = 7, days_after: int = 14):
        """Track campaign impact."""
        # Get historical data
        history = self.beacon.get_history(days=days_before + days_after)

        if not history.data_points:
            print("Insufficient historical data")
            return

        # Separate pre and post campaign
        pre_campaign = []
        post_campaign = []

        for dp in history.data_points:
            if dp.timestamp < self.campaign_start:
                pre_campaign.append(dp)
            else:
                post_campaign.append(dp)

        # Calculate metrics
        if pre_campaign:
            pre_avg = sum(dp.visibility_score for dp in pre_campaign) / len(pre_campaign)
        else:
            pre_avg = 0

        if post_campaign:
            post_avg = sum(dp.visibility_score for dp in post_campaign) / len(post_campaign)
        else:
            post_avg = 0

        impact = post_avg - pre_avg

        # Display results
        print(f"\n{self.brand} Campaign Impact Analysis")
        print("=" * 50)
        print(f"Campaign Start: {self.campaign_start}")
        print(f"\nPre-Campaign Average: {pre_avg:.1f}")
        print(f"Post-Campaign Average: {post_avg:.1f}")
        print(f"Impact: {impact:+.1f} points")

        if impact > 2:
            print("Status: ✓ Positive impact detected")
        elif impact < -2:
            print("Status: ✗ Negative impact detected")
        else:
            print("Status: → No significant impact")

        # Visualize
        self._visualize_campaign_impact(pre_campaign, post_campaign)

        return {
            "pre_avg": pre_avg,
            "post_avg": post_avg,
            "impact": impact,
        }

    def _visualize_campaign_impact(self, pre_data, post_data):
        """Visualize campaign impact."""
        fig, ax = plt.subplots(figsize=(12, 6))

        # Pre-campaign data
        pre_dates = [dp.timestamp for dp in pre_data]
        pre_scores = [dp.visibility_score for dp in pre_data]

        # Post-campaign data
        post_dates = [dp.timestamp for dp in post_data]
        post_scores = [dp.visibility_score for dp in post_data]

        # Plot
        ax.plot(pre_dates, pre_scores, 'o-', label="Pre-Campaign", color="blue")
        ax.plot(post_dates, post_scores, 'o-', label="Post-Campaign", color="green")

        # Campaign start line
        ax.axvline(x=self.campaign_start, color="red", linestyle="--", label="Campaign Start")

        ax.set_xlabel("Date")
        ax.set_ylabel("Visibility Score")
        ax.set_title(f"{self.brand} - Campaign Impact")
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(f"campaign_impact_{self.brand}.png")
        plt.close()

        print(f"\nVisualization saved: campaign_impact_{self.brand}.png")


# Example usage
if __name__ == "__main__":
    tracker = CampaignTracker(
        brand="Nike",
        campaign_start=datetime(2026, 1, 10),
    )

    # Track campaign impact
    results = tracker.track_campaign(days_before=7, days_after=14)
```

---

## Multi-Brand Portfolio Management

Manage visibility for multiple brands in a portfolio.

```python
#!/usr/bin/env python3
"""Multi-Brand Portfolio Manager

Manage and monitor multiple brands in a portfolio.
"""

import asyncio
from promptbeacon import Beacon, Provider
from rich.console import Console
from rich.table import Table
from datetime import datetime

console = Console()

class PortfolioManager:
    """Manage multiple brands in a portfolio."""

    def __init__(self, brands: dict[str, list[str]]):
        """
        Args:
            brands: Dict mapping brand names to their competitors
        """
        self.brands = brands
        self.storage_path = "~/.promptbeacon/portfolio.db"

    async def scan_portfolio(self):
        """Scan all brands in portfolio."""
        results = {}

        for brand, competitors in self.brands.items():
            console.print(f"\n[cyan]Scanning {brand}...[/cyan]")

            beacon = (
                Beacon(brand)
                .with_competitors(*competitors)
                .with_providers(Provider.OPENAI)
                .with_storage(self.storage_path)
                .with_prompt_count(10)
            )

            report = await beacon.scan_async()
            results[brand] = report

        return results

    def display_portfolio_summary(self, results: dict):
        """Display portfolio summary."""
        table = Table(title="Portfolio Summary")
        table.add_column("Brand", style="cyan")
        table.add_column("Score")
        table.add_column("Trend")
        table.add_column("Sentiment")
        table.add_column("Status")

        for brand, report in results.items():
            # Get trend
            beacon = Beacon(brand).with_storage(self.storage_path)
            history = beacon.get_history(days=7)
            trend = history.trend_direction if history.data_points else "unknown"

            # Status based on score
            if report.visibility_score >= 70:
                status = "[green]Excellent[/green]"
            elif report.visibility_score >= 50:
                status = "[yellow]Good[/yellow]"
            else:
                status = "[red]Needs Attention[/red]"

            table.add_row(
                brand,
                f"{report.visibility_score:.1f}",
                trend,
                f"{report.sentiment_breakdown.positive:.0%}",
                status,
            )

        console.print("\n", table)

    def get_portfolio_alerts(self, results: dict):
        """Get alerts for portfolio brands."""
        alerts = []

        for brand, report in results.items():
            # Low score alert
            if report.visibility_score < 50:
                alerts.append({
                    "brand": brand,
                    "type": "low_score",
                    "message": f"Low visibility score: {report.visibility_score:.1f}",
                    "priority": "high",
                })

            # Negative sentiment alert
            if report.sentiment_breakdown.negative > 0.2:
                alerts.append({
                    "brand": brand,
                    "type": "negative_sentiment",
                    "message": f"High negative sentiment: {report.sentiment_breakdown.negative:.0%}",
                    "priority": "medium",
                })

        return alerts

    def display_alerts(self, alerts: list):
        """Display portfolio alerts."""
        if not alerts:
            console.print("\n[green]No alerts - portfolio is healthy[/green]")
            return

        table = Table(title="Portfolio Alerts")
        table.add_column("Brand", style="cyan")
        table.add_column("Priority")
        table.add_column("Message")

        for alert in sorted(alerts, key=lambda x: x["priority"]):
            priority_color = {
                "high": "red",
                "medium": "yellow",
                "low": "green",
            }.get(alert["priority"], "white")

            table.add_row(
                alert["brand"],
                f"[{priority_color}]{alert['priority'].upper()}[/{priority_color}]",
                alert["message"],
            )

        console.print("\n", table)


async def main():
    """Run portfolio management."""
    # Define portfolio
    portfolio = {
        "Brand A": ["Competitor A1", "Competitor A2"],
        "Brand B": ["Competitor B1", "Competitor B2"],
        "Brand C": ["Competitor C1", "Competitor C2"],
    }

    manager = PortfolioManager(portfolio)

    # Scan portfolio
    console.print("[bold]Starting Portfolio Scan...[/bold]")
    results = await manager.scan_portfolio()

    # Display summary
    manager.display_portfolio_summary(results)

    # Check alerts
    alerts = manager.get_portfolio_alerts(results)
    manager.display_alerts(alerts)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Automated Alerting System

Real-time alerting for significant visibility changes.

```python
#!/usr/bin/env python3
"""Automated Alerting System

Real-time monitoring with Slack/email alerts.
"""

from promptbeacon import Beacon
import requests
import json

class AlertSystem:
    """Automated alerting for brand visibility changes."""

    def __init__(self, brand: str, slack_webhook: str = None, email: str = None):
        self.brand = brand
        self.slack_webhook = slack_webhook
        self.email = email
        self.beacon = Beacon(brand).with_storage("~/.promptbeacon/alerts.db")

    def monitor_and_alert(self, thresholds: dict = None):
        """Monitor brand and send alerts."""
        if thresholds is None:
            thresholds = {
                "score_drop": -5.0,
                "score_increase": 5.0,
                "negative_sentiment": 0.2,
                "low_score": 40.0,
            }

        # Run scan
        report = self.beacon.scan()

        # Check for alerts
        alerts = self._check_thresholds(report, thresholds)

        # Send alerts
        for alert in alerts:
            self._send_alert(alert)

        return alerts

    def _check_thresholds(self, report, thresholds):
        """Check if any thresholds are crossed."""
        alerts = []

        # Score change alert
        comparison = self.beacon.compare_with_previous()
        if comparison:
            if comparison.score_change <= thresholds["score_drop"]:
                alerts.append({
                    "severity": "high",
                    "type": "score_drop",
                    "message": f"Visibility dropped by {abs(comparison.score_change):.1f} points",
                    "current": comparison.current_score,
                    "previous": comparison.previous_score,
                })

            elif comparison.score_change >= thresholds["score_increase"]:
                alerts.append({
                    "severity": "info",
                    "type": "score_increase",
                    "message": f"Visibility increased by {comparison.score_change:.1f} points",
                    "current": comparison.current_score,
                    "previous": comparison.previous_score,
                })

        # Sentiment alert
        if report.sentiment_breakdown.negative >= thresholds["negative_sentiment"]:
            alerts.append({
                "severity": "medium",
                "type": "negative_sentiment",
                "message": f"Negative sentiment at {report.sentiment_breakdown.negative:.0%}",
                "score": report.visibility_score,
            })

        # Low score alert
        if report.visibility_score <= thresholds["low_score"]:
            alerts.append({
                "severity": "high",
                "type": "low_score",
                "message": f"Visibility score below threshold: {report.visibility_score:.1f}",
                "score": report.visibility_score,
            })

        return alerts

    def _send_alert(self, alert: dict):
        """Send alert via configured channels."""
        print(f"\nALERT [{alert['severity'].upper()}]: {alert['message']}")

        if self.slack_webhook:
            self._send_slack(alert)

        if self.email:
            self._send_email(alert)

    def _send_slack(self, alert: dict):
        """Send alert to Slack."""
        severity_emoji = {
            "high": ":rotating_light:",
            "medium": ":warning:",
            "low": ":information_source:",
            "info": ":white_check_mark:",
        }

        emoji = severity_emoji.get(alert["severity"], ":bell:")

        message = {
            "text": f"{emoji} Brand Visibility Alert: {self.brand}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} {alert['type'].replace('_', ' ').title()}",
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Brand:* {self.brand}\n*Message:* {alert['message']}"
                    }
                }
            ]
        }

        if "current" in alert and "previous" in alert:
            message["blocks"].append({
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Current Score:*\n{alert['current']:.1f}"},
                    {"type": "mrkdwn", "text": f"*Previous Score:*\n{alert['previous']:.1f}"},
                ]
            })

        try:
            response = requests.post(self.slack_webhook, json=message)
            if response.status_code == 200:
                print("✓ Slack alert sent")
        except Exception as e:
            print(f"✗ Slack alert failed: {e}")

    def _send_email(self, alert: dict):
        """Send alert via email."""
        # Implement email sending
        print(f"✓ Email alert would be sent to {self.email}")


# Example usage
if __name__ == "__main__":
    alert_system = AlertSystem(
        brand="Nike",
        slack_webhook="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    )

    # Monitor and alert
    alerts = alert_system.monitor_and_alert(thresholds={
        "score_drop": -3.0,
        "score_increase": 5.0,
        "negative_sentiment": 0.15,
        "low_score": 50.0,
    })

    if alerts:
        print(f"\n{len(alerts)} alert(s) triggered")
    else:
        print("\nNo alerts - all metrics within thresholds")
```

---

## Weekly Report Generation

Generate comprehensive weekly reports for stakeholders.

```python
#!/usr/bin/env python3
"""Weekly Report Generator

Generate comprehensive weekly visibility reports.
"""

from promptbeacon import Beacon, to_markdown
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt

class WeeklyReporter:
    """Generate weekly visibility reports."""

    def __init__(self, brand: str, competitors: list[str]):
        self.brand = brand
        self.competitors = competitors
        self.beacon = (
            Beacon(brand)
            .with_competitors(*competitors)
            .with_storage("~/.promptbeacon/weekly.db")
        )

    def generate_weekly_report(self):
        """Generate comprehensive weekly report."""
        # Get current scan
        current_report = self.beacon.scan()

        # Get historical data
        history = self.beacon.get_history(days=7)

        # Generate report sections
        report = self._create_report_header()
        report += self._create_executive_summary(current_report, history)
        report += self._create_detailed_metrics(current_report)
        report += self._create_trend_analysis(history)
        report += self._create_competitive_analysis(current_report)
        report += self._create_recommendations(current_report)

        # Save report
        output_path = self._save_report(report)

        print(f"Weekly report generated: {output_path}")
        return report

    def _create_report_header(self):
        """Create report header."""
        return f"""# Weekly Visibility Report: {self.brand}

**Report Period:** {datetime.now().strftime("%Y-%m-%d")}
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

"""

    def _create_executive_summary(self, report, history):
        """Create executive summary."""
        summary = "## Executive Summary\n\n"

        summary += f"- **Current Visibility Score:** {report.visibility_score:.1f}/100\n"
        summary += f"- **Total Mentions:** {report.mention_count}\n"
        summary += f"- **Positive Sentiment:** {report.sentiment_breakdown.positive:.0%}\n"

        if history.data_points:
            summary += f"- **7-Day Trend:** {history.trend_direction.upper()}\n"
            summary += f"- **7-Day Average:** {history.average_score:.1f}\n"
            summary += f"- **Volatility:** {history.volatility:.2f}\n"

        summary += "\n"
        return summary

    def _create_detailed_metrics(self, report):
        """Create detailed metrics section."""
        metrics = "## Detailed Metrics\n\n"

        metrics += "### Visibility Breakdown\n\n"
        metrics += f"- **Visibility Score:** {report.visibility_score:.1f}/100\n"
        metrics += f"- **Mention Count:** {report.mention_count}\n"
        metrics += f"- **Recommendation Rate:** {report.metrics.recommendation_rate:.0%}\n"

        if report.metrics.average_position:
            metrics += f"- **Average Position:** {report.metrics.average_position:.1f}\n"

        metrics += "\n### Sentiment Analysis\n\n"
        metrics += f"- **Positive:** {report.sentiment_breakdown.positive:.0%}\n"
        metrics += f"- **Neutral:** {report.sentiment_breakdown.neutral:.0%}\n"
        metrics += f"- **Negative:** {report.sentiment_breakdown.negative:.0%}\n"

        metrics += "\n"
        return metrics

    def _create_trend_analysis(self, history):
        """Create trend analysis section."""
        if not history.data_points:
            return ""

        trends = "## Trend Analysis\n\n"

        # Create trend chart
        dates = [dp.timestamp.strftime("%m-%d") for dp in history.data_points]
        scores = [dp.visibility_score for dp in history.data_points]

        plt.figure(figsize=(10, 6))
        plt.plot(dates, scores, marker='o')
        plt.title(f"{self.brand} - 7-Day Visibility Trend")
        plt.xlabel("Date")
        plt.ylabel("Visibility Score")
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()

        chart_path = f"trend_{self.brand}_{datetime.now().strftime('%Y%m%d')}.png"
        plt.savefig(chart_path)
        plt.close()

        trends += f"![7-Day Trend]({chart_path})\n\n"

        trends += f"**Trend Direction:** {history.trend_direction.upper()}\n"
        trends += f"**Average Score:** {history.average_score:.1f}\n"
        trends += f"**Volatility:** {history.volatility:.2f}\n\n"

        return trends

    def _create_competitive_analysis(self, report):
        """Create competitive analysis section."""
        if not report.competitor_comparison:
            return ""

        comp = "## Competitive Analysis\n\n"
        comp += "| Brand | Visibility Score | Mentions | Positive % |\n"
        comp += "|-------|------------------|----------|------------|\n"

        # Add main brand
        comp += f"| **{self.brand}** | **{report.visibility_score:.1f}** | **{report.mention_count}** | **{report.sentiment_breakdown.positive:.0%}** |\n"

        # Add competitors
        for name, score in sorted(
            report.competitor_comparison.items(),
            key=lambda x: x[1].visibility_score,
            reverse=True
        ):
            comp += f"| {name} | {score.visibility_score:.1f} | {score.mention_count} | {score.sentiment.positive:.0%} |\n"

        comp += "\n"
        return comp

    def _create_recommendations(self, report):
        """Create recommendations section."""
        if not report.recommendations:
            return ""

        recs = "## Recommendations\n\n"

        for rec in report.recommendations[:5]:
            recs += f"### [{rec.priority.upper()}] {rec.action}\n\n"
            recs += f"**Rationale:** {rec.rationale}\n\n"
            if rec.expected_impact:
                recs += f"**Expected Impact:** {rec.expected_impact}\n\n"

        return recs

    def _save_report(self, report: str):
        """Save report to file."""
        output_dir = Path("./weekly_reports")
        output_dir.mkdir(exist_ok=True)

        filename = f"weekly_report_{self.brand}_{datetime.now().strftime('%Y%m%d')}.md"
        filepath = output_dir / filename

        with open(filepath, "w") as f:
            f.write(report)

        return filepath


# Example usage
if __name__ == "__main__":
    reporter = WeeklyReporter(
        brand="Nike",
        competitors=["Adidas", "Puma", "New Balance"],
    )

    report = reporter.generate_weekly_report()
    print(report)
```

---

## See Also

- [Quickstart Guide](quickstart.md) - Getting started
- [API Reference](api-reference.md) - Complete API documentation
- [Advanced Usage](advanced.md) - Advanced patterns
- [CLI Reference](cli.md) - Command-line tools
- [Storage Guide](storage.md) - Data management
