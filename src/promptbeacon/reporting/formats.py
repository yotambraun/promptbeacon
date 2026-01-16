"""Export formats for reports."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from promptbeacon.core.schemas import Report

if TYPE_CHECKING:
    pass


def to_json(report: Report, indent: int = 2) -> str:
    """Export report to JSON string.

    Args:
        report: The Report to export.
        indent: JSON indentation level.

    Returns:
        JSON string representation.
    """
    return report.model_dump_json(indent=indent)


def to_dict(report: Report) -> dict[str, Any]:
    """Export report to dictionary.

    Args:
        report: The Report to export.

    Returns:
        Dictionary representation.
    """
    return report.model_dump()


def to_dataframe(report: Report):
    """Export report to a pandas DataFrame.

    Requires pandas to be installed.

    Args:
        report: The Report to export.

    Returns:
        pandas DataFrame with report data.

    Raises:
        ImportError: If pandas is not installed.
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for DataFrame export: pip install pandas")

    # Create main metrics row
    main_data = {
        "brand": report.brand,
        "visibility_score": report.visibility_score,
        "mention_count": report.mention_count,
        "sentiment_positive": report.sentiment_breakdown.positive,
        "sentiment_neutral": report.sentiment_breakdown.neutral,
        "sentiment_negative": report.sentiment_breakdown.negative,
        "timestamp": report.timestamp,
        "scan_duration_seconds": report.scan_duration_seconds,
        "total_cost_usd": report.total_cost_usd,
        "providers_used": ",".join(report.providers_used),
    }

    return pd.DataFrame([main_data])


def to_mentions_dataframe(report: Report):
    """Export report mentions to a pandas DataFrame.

    Requires pandas to be installed.

    Args:
        report: The Report to export.

    Returns:
        pandas DataFrame with mention data.

    Raises:
        ImportError: If pandas is not installed.
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for DataFrame export: pip install pandas")

    mentions_data = []
    for result in report.provider_results:
        for mention in result.mentions:
            mentions_data.append({
                "brand_name": mention.brand_name,
                "sentiment": mention.sentiment,
                "position": mention.position,
                "context": mention.context,
                "confidence": mention.confidence,
                "is_recommendation": mention.is_recommendation,
                "provider": result.provider,
                "model": result.model,
                "prompt": result.prompt,
            })

    return pd.DataFrame(mentions_data)


def to_csv(report: Report) -> str:
    """Export report to CSV string.

    Args:
        report: The Report to export.

    Returns:
        CSV string representation.
    """
    lines = [
        "metric,value",
        f"brand,{report.brand}",
        f"visibility_score,{report.visibility_score}",
        f"mention_count,{report.mention_count}",
        f"sentiment_positive,{report.sentiment_breakdown.positive}",
        f"sentiment_neutral,{report.sentiment_breakdown.neutral}",
        f"sentiment_negative,{report.sentiment_breakdown.negative}",
        f"timestamp,{report.timestamp.isoformat()}",
        f"scan_duration_seconds,{report.scan_duration_seconds}",
        f"total_cost_usd,{report.total_cost_usd or ''}",
    ]

    return "\n".join(lines)


def to_markdown(report: Report) -> str:
    """Export report to Markdown string.

    Args:
        report: The Report to export.

    Returns:
        Markdown string representation.
    """
    lines = [
        f"# Brand Visibility Report: {report.brand}",
        "",
        f"*Generated: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}*",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Visibility Score | **{report.visibility_score:.1f}**/100 |",
        f"| Total Mentions | {report.mention_count} |",
        f"| Positive Sentiment | {report.sentiment_breakdown.positive:.1%} |",
        f"| Neutral Sentiment | {report.sentiment_breakdown.neutral:.1%} |",
        f"| Negative Sentiment | {report.sentiment_breakdown.negative:.1%} |",
        "",
    ]

    if report.competitor_comparison:
        lines.extend([
            "## Competitor Comparison",
            "",
            "| Brand | Visibility Score | Mentions |",
            "|-------|-----------------|----------|",
        ])
        # Add the target brand
        lines.append(
            f"| **{report.brand}** | **{report.visibility_score:.1f}** | "
            f"**{report.mention_count}** |"
        )
        for name, score in report.competitor_comparison.items():
            lines.append(
                f"| {name} | {score.visibility_score:.1f} | {score.mention_count} |"
            )
        lines.append("")

    if report.explanations:
        lines.extend([
            "## Key Insights",
            "",
        ])
        for exp in report.explanations:
            impact_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(exp.impact, "")
            lines.append(f"- {impact_emoji} **{exp.category}**: {exp.message}")
            if exp.evidence:
                for evidence in exp.evidence[:2]:
                    lines.append(f"  - *\"{evidence[:100]}...\"*")
        lines.append("")

    if report.recommendations:
        lines.extend([
            "## Recommendations",
            "",
        ])
        for rec in report.recommendations:
            priority_badge = {
                "high": "🔴 HIGH",
                "medium": "🟡 MEDIUM",
                "low": "🟢 LOW",
            }.get(rec.priority, "")
            lines.append(f"### {priority_badge}: {rec.action}")
            lines.append("")
            lines.append(f"*{rec.rationale}*")
            if rec.expected_impact:
                lines.append(f"\n**Expected Impact**: {rec.expected_impact}")
            lines.append("")

    lines.extend([
        "---",
        "",
        f"*Scan Duration: {report.scan_duration_seconds:.1f}s | "
        f"Providers: {', '.join(report.providers_used)}*",
    ])

    if report.total_cost_usd:
        lines.append(f"\n*Estimated Cost: ${report.total_cost_usd:.4f}*")

    return "\n".join(lines)


def to_html(report: Report) -> str:
    """Export report to HTML string.

    Args:
        report: The Report to export.

    Returns:
        HTML string representation.
    """
    score_color = (
        "#22c55e" if report.visibility_score >= 70 else
        "#eab308" if report.visibility_score >= 40 else
        "#ef4444"
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Brand Visibility Report: {report.brand}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1f2937; }}
        .score {{ font-size: 3em; color: {score_color}; font-weight: bold; }}
        .metric {{ background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 10px 0; }}
        .metric-label {{ color: #6b7280; font-size: 0.9em; }}
        .metric-value {{ font-size: 1.5em; font-weight: bold; color: #1f2937; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
        th {{ background: #f9fafb; }}
        .recommendation {{ background: #fef3c7; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #f59e0b; }}
        .high {{ border-left-color: #ef4444; background: #fef2f2; }}
        .insight {{ background: #eff6ff; padding: 15px; border-radius: 8px; margin: 10px 0; }}
    </style>
</head>
<body>
    <h1>Brand Visibility Report: {report.brand}</h1>
    <p style="color: #6b7280;">Generated: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>

    <div class="metric">
        <div class="metric-label">Visibility Score</div>
        <div class="score">{report.visibility_score:.1f}</div>
        <div class="metric-label">out of 100</div>
    </div>

    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
        <div class="metric">
            <div class="metric-label">Total Mentions</div>
            <div class="metric-value">{report.mention_count}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Positive Sentiment</div>
            <div class="metric-value">{report.sentiment_breakdown.positive:.0%}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Providers Used</div>
            <div class="metric-value">{len(report.providers_used)}</div>
        </div>
    </div>
"""

    if report.competitor_comparison:
        html += """
    <h2>Competitor Comparison</h2>
    <table>
        <tr><th>Brand</th><th>Visibility Score</th><th>Mentions</th></tr>
"""
        html += f"        <tr><td><strong>{report.brand}</strong></td><td><strong>{report.visibility_score:.1f}</strong></td><td><strong>{report.mention_count}</strong></td></tr>\n"
        for name, score in report.competitor_comparison.items():
            html += f"        <tr><td>{name}</td><td>{score.visibility_score:.1f}</td><td>{score.mention_count}</td></tr>\n"
        html += "    </table>\n"

    if report.explanations:
        html += "    <h2>Key Insights</h2>\n"
        for exp in report.explanations[:5]:
            html += f'    <div class="insight"><strong>{exp.category}</strong>: {exp.message}</div>\n'

    if report.recommendations:
        html += "    <h2>Recommendations</h2>\n"
        for rec in report.recommendations[:5]:
            priority_class = "high" if rec.priority == "high" else ""
            html += f'    <div class="recommendation {priority_class}"><strong>[{rec.priority.upper()}]</strong> {rec.action}<br><small>{rec.rationale}</small></div>\n'

    html += f"""
    <hr>
    <p style="color: #6b7280; font-size: 0.9em;">
        Scan Duration: {report.scan_duration_seconds:.1f}s |
        Providers: {', '.join(report.providers_used)}
        {f' | Estimated Cost: ${report.total_cost_usd:.4f}' if report.total_cost_usd else ''}
    </p>
</body>
</html>"""

    return html
