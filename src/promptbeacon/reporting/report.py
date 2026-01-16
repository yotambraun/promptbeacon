"""Report generation and management."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from promptbeacon.core.schemas import Report

if TYPE_CHECKING:
    pass


class ReportBuilder:
    """Builder for creating custom reports."""

    def __init__(self, report: Report):
        """Initialize with a base report.

        Args:
            report: The Report to build from.
        """
        self._report = report

    @property
    def report(self) -> Report:
        """Get the underlying report."""
        return self._report

    def summary(self) -> str:
        """Generate a text summary of the report.

        Returns:
            Human-readable summary string.
        """
        lines = [
            f"Brand Visibility Report: {self._report.brand}",
            f"Generated: {self._report.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            f"Visibility Score: {self._report.visibility_score:.1f}/100",
            f"Total Mentions: {self._report.mention_count}",
            "",
            "Sentiment Breakdown:",
            f"  Positive: {self._report.sentiment_breakdown.positive:.1%}",
            f"  Neutral: {self._report.sentiment_breakdown.neutral:.1%}",
            f"  Negative: {self._report.sentiment_breakdown.negative:.1%}",
        ]

        if self._report.competitor_comparison:
            lines.append("")
            lines.append("Competitor Comparison:")
            for name, score in self._report.competitor_comparison.items():
                lines.append(f"  {name}: {score.visibility_score:.1f}")

        if self._report.explanations:
            lines.append("")
            lines.append("Key Insights:")
            for exp in self._report.explanations[:3]:
                lines.append(f"  - {exp.message}")

        if self._report.recommendations:
            lines.append("")
            lines.append("Recommendations:")
            for rec in self._report.recommendations[:3]:
                lines.append(f"  - [{rec.priority.upper()}] {rec.action}")

        lines.extend(
            [
                "",
                f"Scan Duration: {self._report.scan_duration_seconds:.1f}s",
                f"Providers Used: {', '.join(self._report.providers_used)}",
            ]
        )

        if self._report.total_cost_usd:
            lines.append(f"Estimated Cost: ${self._report.total_cost_usd:.4f}")

        return "\n".join(lines)

    def executive_summary(self) -> str:
        """Generate a brief executive summary.

        Returns:
            Short summary suitable for dashboards.
        """
        sentiment = self._report.sentiment_breakdown
        primary_sentiment = "positive" if sentiment.positive > 0.5 else (
            "negative" if sentiment.negative > 0.5 else "neutral"
        )

        score_rating = (
            "strong" if self._report.visibility_score >= 70 else
            "moderate" if self._report.visibility_score >= 40 else
            "low"
        )

        return (
            f"{self._report.brand} has {score_rating} LLM visibility "
            f"(score: {self._report.visibility_score:.1f}/100) with "
            f"predominantly {primary_sentiment} sentiment across "
            f"{len(self._report.providers_used)} AI providers."
        )


def create_report_builder(report: Report) -> ReportBuilder:
    """Create a ReportBuilder for a report.

    Args:
        report: The Report to build from.

    Returns:
        ReportBuilder instance.
    """
    return ReportBuilder(report)


def merge_reports(reports: list[Report]) -> Report | None:
    """Merge multiple reports into a combined report.

    Useful for aggregating results from multiple scans.

    Args:
        reports: List of reports to merge.

    Returns:
        Merged report or None if empty.
    """
    if not reports:
        return None

    if len(reports) == 1:
        return reports[0]

    # Use the most recent report as base
    reports = sorted(reports, key=lambda r: r.timestamp, reverse=True)
    base = reports[0]

    # Combine all provider results
    all_results = []
    for report in reports:
        all_results.extend(report.provider_results)

    # Recalculate metrics
    total_mentions = sum(r.mention_count for r in reports)
    avg_visibility = sum(r.visibility_score for r in reports) / len(reports)

    # Merge competitor comparisons
    merged_competitors = {}
    for report in reports:
        for name, score in report.competitor_comparison.items():
            if name not in merged_competitors:
                merged_competitors[name] = score

    # Combine explanations and recommendations (deduplicated)
    seen_explanations = set()
    all_explanations = []
    for report in reports:
        for exp in report.explanations:
            if exp.message not in seen_explanations:
                seen_explanations.add(exp.message)
                all_explanations.append(exp)

    seen_recommendations = set()
    all_recommendations = []
    for report in reports:
        for rec in report.recommendations:
            if rec.action not in seen_recommendations:
                seen_recommendations.add(rec.action)
                all_recommendations.append(rec)

    return Report(
        brand=base.brand,
        visibility_score=round(avg_visibility, 1),
        mention_count=total_mentions,
        sentiment_breakdown=base.sentiment_breakdown,
        competitor_comparison=merged_competitors,
        provider_results=all_results,
        metrics=base.metrics,
        explanations=all_explanations,
        recommendations=all_recommendations,
        timestamp=datetime.utcnow(),
        scan_duration_seconds=sum(r.scan_duration_seconds for r in reports),
        total_cost_usd=sum(r.total_cost_usd or 0 for r in reports) or None,
    )
