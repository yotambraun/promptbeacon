"""Export formats for reports."""

from __future__ import annotations

import html as _html
from typing import TYPE_CHECKING, Any

from promptbeacon.core.schemas import Report

if TYPE_CHECKING:
    from promptbeacon.core.schemas import HistoryReport

# Brand colour palette for charts. Target brand is always the first (indigo);
# competitors cycle through the rest.
_PALETTE = [
    "#6366f1",  # indigo (target)
    "#22d3ee",  # cyan
    "#a855f7",  # violet
    "#f59e0b",  # amber
    "#10b981",  # emerald
    "#ef4444",  # red
    "#64748b",  # slate
]


def _esc(text: str) -> str:
    """HTML-escape a string."""
    return _html.escape(str(text))


def _score_color(score: float) -> str:
    """Traffic-light colour for a 0-100 score."""
    return "#22c55e" if score >= 70 else "#eab308" if score >= 40 else "#ef4444"


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
        raise ImportError(
            "pandas is required for DataFrame export: pip install pandas"
        ) from None

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
        raise ImportError(
            "pandas is required for DataFrame export: pip install pandas"
        ) from None

    mentions_data = []
    for result in report.provider_results:
        for mention in result.mentions:
            mentions_data.append(
                {
                    "brand_name": mention.brand_name,
                    "sentiment": mention.sentiment,
                    "position": mention.position,
                    "context": mention.context,
                    "confidence": mention.confidence,
                    "is_recommendation": mention.is_recommendation,
                    "provider": result.provider,
                    "model": result.model,
                    "prompt": result.prompt,
                }
            )

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
        f"citation_count,{report.citation_summary.total_citations if report.citation_summary else 0}",
    ]

    if report.share_of_voice:
        sov = report.share_of_voice
        lines.append(f"share_of_voice,{sov.target_share}")
        lines.append(f"presence_rate,{sov.target_presence_rate}")
        lines.append(f"sov_rank,{sov.target_rank}")

    if report.stability:
        lines.append(f"stability_score,{report.stability.stability_score}")
        lines.append(f"stability_runs,{report.stability.runs}")

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
        "| Metric | Value |",
        "|--------|-------|",
        f"| Visibility Score | **{report.visibility_score:.1f}**/100 |",
        f"| Total Mentions | {report.mention_count} |",
        f"| Positive Sentiment | {report.sentiment_breakdown.positive:.1%} |",
        f"| Neutral Sentiment | {report.sentiment_breakdown.neutral:.1%} |",
        f"| Negative Sentiment | {report.sentiment_breakdown.negative:.1%} |",
        "",
    ]

    if report.share_of_voice:
        sov = report.share_of_voice
        lines.extend(
            [
                "## Share of Voice",
                "",
                f"**{report.brand}** holds **{sov.target_share:.0%}** share of voice "
                f"(rank {sov.target_rank}), appearing in "
                f"**{sov.target_presence_rate:.0%}** of prompts.",
                "",
                "| Brand | Appearances | Presence | Share of Voice |",
                "|-------|-------------|----------|----------------|",
            ]
        )
        ordered = sorted(
            sov.aggregate.values(), key=lambda e: e.appearances, reverse=True
        )
        for entry in ordered:
            marker = "**" if entry.brand_name == report.brand else ""
            lines.append(
                f"| {marker}{entry.brand_name}{marker} | {entry.appearances}"
                f"/{entry.total_prompts} | {entry.presence_rate:.0%} | "
                f"{marker}{entry.share_of_voice:.0%}{marker} |"
            )
        lines.append("")

    if report.competitor_comparison:
        lines.extend(
            [
                "## Competitor Comparison",
                "",
                "| Brand | Visibility Score | Mentions |",
                "|-------|-----------------|----------|",
            ]
        )
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
        lines.extend(
            [
                "## Key Insights",
                "",
            ]
        )
        for exp in report.explanations:
            impact_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                exp.impact, ""
            )
            lines.append(f"- {impact_emoji} **{exp.category}**: {exp.message}")
            if exp.evidence:
                for evidence in exp.evidence[:2]:
                    lines.append(f'  - *"{evidence[:100]}..."*')
        lines.append("")

    if report.recommendations:
        lines.extend(
            [
                "## Recommendations",
                "",
            ]
        )
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

    if report.citation_summary and report.citation_summary.total_citations > 0:
        lines.extend(
            [
                "## Sources Cited",
                "",
            ]
        )
        for cit in report.citation_summary.citations[:15]:
            source = f"[{cit.source_name}]({cit.url})" if cit.url else cit.source_name
            brand_tag = f" *({cit.brand_associated})*" if cit.brand_associated else ""
            lines.append(f"- {source}{brand_tag}")
        if report.citation_summary.unique_domains:
            lines.append(
                f"\n*{len(report.citation_summary.unique_domains)} unique domain(s)*"
            )
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            f"*Scan Duration: {report.scan_duration_seconds:.1f}s | "
            f"Providers: {', '.join(report.providers_used)}*",
        ]
    )

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
        "#22c55e"
        if report.visibility_score >= 70
        else "#eab308"
        if report.visibility_score >= 40
        else "#ef4444"
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
    <p style="color: #6b7280;">Generated: {report.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}</p>

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

    if report.share_of_voice:
        html += _sov_html_section(report)

    if report.stability:
        html += _stability_html_section(report)

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

    if report.citation_summary and report.citation_summary.total_citations > 0:
        html += "    <h2>Sources Cited</h2>\n    <ul>\n"
        for cit in report.citation_summary.citations[:15]:
            if cit.url:
                source_html = f'<a href="{cit.url}">{cit.source_name}</a>'
            else:
                source_html = cit.source_name
            brand_tag = (
                f" <em>({cit.brand_associated})</em>" if cit.brand_associated else ""
            )
            html += f"        <li>{source_html}{brand_tag}</li>\n"
        html += "    </ul>\n"

    html += f"""
    <hr>
    <p style="color: #6b7280; font-size: 0.9em;">
        Scan Duration: {report.scan_duration_seconds:.1f}s |
        Providers: {", ".join(report.providers_used)}
        {f" | Estimated Cost: ${report.total_cost_usd:.4f}" if report.total_cost_usd else ""}
    </p>
</body>
</html>"""

    return html


def _sov_html_section(report: Report) -> str:
    """Render a Share-of-Voice stacked bar + legend (inline CSS, no JS)."""
    sov = report.share_of_voice
    if not sov:
        return ""

    ordered = sorted(sov.aggregate.values(), key=lambda e: e.appearances, reverse=True)
    colors = {report.brand: _PALETTE[0]}
    ci = 1
    for entry in ordered:
        if entry.brand_name != report.brand:
            colors[entry.brand_name] = _PALETTE[ci % len(_PALETTE)]
            ci += 1

    segments = ""
    for entry in ordered:
        pct = entry.share_of_voice * 100
        if pct <= 0:
            continue
        label = f"{entry.brand_name} {pct:.0f}%" if pct >= 8 else ""
        segments += (
            f'<div style="width:{pct:.2f}%;background:{colors[entry.brand_name]};'
            "color:#fff;font-size:0.75em;line-height:32px;text-align:center;"
            f'overflow:hidden;white-space:nowrap;" title="{_esc(entry.brand_name)}: '
            f'{pct:.1f}%">{_esc(label)}</div>'
        )

    legend = ""
    for entry in ordered:
        legend += (
            '<span style="display:inline-flex;align-items:center;margin-right:14px;'
            'font-size:0.85em;">'
            f'<span style="width:11px;height:11px;border-radius:3px;margin-right:5px;'
            f'background:{colors[entry.brand_name]};"></span>'
            f"{_esc(entry.brand_name)} &mdash; {entry.share_of_voice:.0%} SoV "
            f"({entry.presence_rate:.0%} presence)</span>"
        )

    return f"""
    <h2>Share of Voice</h2>
    <p style="color:#374151;"><strong>{_esc(report.brand)}</strong> holds
        <strong>{sov.target_share:.0%}</strong> share of voice (rank
        {sov.target_rank}), appearing in <strong>{sov.target_presence_rate:.0%}</strong>
        of prompts.</p>
    <div style="display:flex;border-radius:8px;overflow:hidden;height:32px;
        background:#e5e7eb;">{segments}</div>
    <div style="margin-top:10px;">{legend}</div>
"""


def _stability_html_section(report: Report) -> str:
    """Render a stability band: score, confidence interval, rating chip."""
    st = report.stability
    if not st:
        return ""

    rating_color = {
        "stable": "#22c55e",
        "moderate": "#eab308",
        "volatile": "#ef4444",
    }.get(st.volatility.stability_rating, "#64748b")
    lo, hi = st.score_confidence_interval
    width = max(0.0, min(100.0, st.stability_score))

    return f"""
    <h2>Stability <span style="font-size:0.6em;color:#6b7280;">
        ({st.runs} runs)</span></h2>
    <p style="color:#374151;">How much to trust a single scan. A stability score
        near 100 means the answer engines are consistent; a low score means the
        visibility number swings run-to-run.</p>
    <div style="display:flex;align-items:center;gap:14px;margin:10px 0;">
        <div style="font-size:2.2em;font-weight:bold;color:{rating_color};">
            {st.stability_score:.0f}</div>
        <span style="background:{rating_color};color:#fff;padding:3px 10px;
            border-radius:999px;font-size:0.8em;text-transform:uppercase;">
            {st.volatility.stability_rating}</span>
    </div>
    <div style="background:#e5e7eb;border-radius:8px;height:10px;overflow:hidden;">
        <div style="width:{width:.1f}%;height:100%;background:{rating_color};"></div>
    </div>
    <p style="color:#6b7280;font-size:0.85em;margin-top:8px;">
        Score across runs: {", ".join(f"{s:.0f}" for s in st.score_per_run)} &middot;
        95% CI [{lo:.0f}, {hi:.0f}] &middot;
        {st.flip_flop_count} flip-flopping prompt(s) &middot;
        presence consistency {st.overall_presence_consistency:.0%}</p>
"""


def _score_breakdown_html(report: Report) -> str:
    """Render the four scoring factors as horizontal bars."""
    bd = report.metrics.score_breakdown if report.metrics else None
    if not bd:
        return ""

    rows = [
        ("Mention Frequency", bd.mention_frequency),
        ("Sentiment", bd.sentiment),
        ("Position / Prominence", bd.position),
        ("Recommendation Rate", bd.recommendation),
    ]
    bars = ""
    for label, value in rows:
        bars += (
            '<div style="margin:8px 0;">'
            f'<div style="font-size:0.85em;color:#374151;">{label} '
            f'<span style="color:#6b7280;">{value:.0f}</span></div>'
            '<div style="background:#e5e7eb;border-radius:6px;height:9px;'
            'overflow:hidden;">'
            f'<div style="width:{max(0.0, min(100.0, value)):.1f}%;height:100%;'
            'background:#6366f1;"></div></div></div>'
        )
    return f"<h2>Score Breakdown</h2>{bars}"


def _sentiment_donut_html(report: Report) -> str:
    """Render a sentiment donut using a CSS conic-gradient (no JS/SVG)."""
    s = report.sentiment_breakdown
    pos = s.positive * 100
    neu = s.neutral * 100
    p2 = pos + neu
    return f"""
    <h2>Sentiment</h2>
    <div style="display:flex;align-items:center;gap:18px;">
        <div style="width:120px;height:120px;border-radius:50%;
            background:conic-gradient(#22c55e 0 {pos:.1f}%,#94a3b8 {pos:.1f}% {p2:.1f}%,
            #ef4444 {p2:.1f}% 100%);display:flex;align-items:center;
            justify-content:center;">
            <div style="width:74px;height:74px;border-radius:50%;background:#fff;">
            </div>
        </div>
        <div style="font-size:0.9em;color:#374151;line-height:1.8;">
            <div><span style="color:#22c55e;">●</span> Positive {pos:.0f}%</div>
            <div><span style="color:#94a3b8;">●</span> Neutral {neu:.0f}%</div>
            <div><span style="color:#ef4444;">●</span> Negative {s.negative * 100:.0f}%</div>
        </div>
    </div>
"""


def _sparkline_svg(values: list[float]) -> str:
    """Render a simple inline-SVG sparkline for a list of scores."""
    if len(values) < 2:
        return ""
    width, height, pad = 480, 80, 6
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    step = (width - 2 * pad) / (len(values) - 1)
    points = " ".join(
        f"{pad + i * step:.1f},"
        f"{height - pad - (v - lo) / span * (height - 2 * pad):.1f}"
        for i, v in enumerate(values)
    )
    return f"""
    <h2>History</h2>
    <svg viewBox="0 0 {width} {height}" width="100%" height="{height}"
        preserveAspectRatio="none">
        <polyline fill="none" stroke="#6366f1" stroke-width="2.5"
            stroke-linejoin="round" stroke-linecap="round" points="{points}"/>
    </svg>
"""


def to_dashboard_html(report: Report, *, history: HistoryReport | None = None) -> str:
    """Export a rich, self-contained HTML dashboard for a report.

    Single file, inline CSS/SVG, zero JavaScript — shareable as-is. Renders the
    visibility score, Share of Voice bar, score breakdown, sentiment donut,
    stability band (if measured), competitor table, citations, and an optional
    history sparkline.

    Args:
        report: The Report to render.
        history: Optional HistoryReport for a trend sparkline.

    Returns:
        A complete HTML document as a string.
    """
    score_color = _score_color(report.visibility_score)

    competitor_rows = ""
    if report.competitor_comparison:
        competitor_rows = (
            "<h2>Competitor Comparison</h2><table><tr><th>Brand</th>"
            "<th>Visibility</th><th>Mentions</th><th>Positive</th></tr>"
            f"<tr><td><strong>{_esc(report.brand)}</strong></td>"
            f"<td><strong>{report.visibility_score:.1f}</strong></td>"
            f"<td><strong>{report.mention_count}</strong></td>"
            f"<td><strong>{report.sentiment_breakdown.positive:.0%}</strong></td></tr>"
        )
        for name, score in report.competitor_comparison.items():
            competitor_rows += (
                f"<tr><td>{_esc(name)}</td><td>{score.visibility_score:.1f}</td>"
                f"<td>{score.mention_count}</td>"
                f"<td>{score.sentiment.positive:.0%}</td></tr>"
            )
        competitor_rows += "</table>"

    citations = ""
    if report.citation_summary and report.citation_summary.total_citations > 0:
        items = ""
        for cit in report.citation_summary.citations[:15]:
            src = (
                f'<a href="{_esc(cit.url)}">{_esc(cit.source_name)}</a>'
                if cit.url
                else _esc(cit.source_name)
            )
            tag = (
                f" <em>({_esc(cit.brand_associated)})</em>"
                if cit.brand_associated
                else ""
            )
            items += f"<li>{src}{tag}</li>"
        citations = f"<h2>Sources Cited</h2><ul>{items}</ul>"

    spark = _sparkline_svg(history.visibility_trend) if history else ""

    cost = (
        f" &middot; Est. cost ${report.total_cost_usd:.4f}"
        if report.total_cost_usd
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PromptBeacon Report: {_esc(report.brand)}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    max-width: 880px; margin: 0 auto; padding: 28px; color: #1f2937;
    background: #f8fafc; }}
  .card {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 14px;
    padding: 24px 28px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); margin-bottom: 20px; }}
  h1 {{ margin: 0; font-size: 1.5em; }}
  h2 {{ font-size: 1.1em; margin: 22px 0 8px; }}
  .brandmark {{ display:flex; align-items:center; gap:10px; }}
  .dot {{ width:30px;height:30px;border-radius:50%;
    background:radial-gradient(circle at 35% 35%, #22d3ee, #6366f1); }}
  .muted {{ color: #6b7280; font-size: 0.9em; }}
  .score {{ font-size: 3.4em; font-weight: 800; color: {score_color}; line-height: 1; }}
  table {{ width:100%; border-collapse: collapse; margin: 6px 0; }}
  th, td {{ padding: 9px 10px; text-align: left; border-bottom: 1px solid #eef2f7; }}
  th {{ background:#f9fafb; font-size:0.85em; color:#6b7280; }}
  a {{ color:#6366f1; }}
</style>
</head>
<body>
  <div class="card">
    <div class="brandmark"><span class="dot"></span>
      <h1>PromptBeacon &mdash; {_esc(report.brand)}</h1></div>
    <p class="muted">AI visibility report &middot;
      {report.timestamp.strftime("%Y-%m-%d %H:%M UTC")}</p>
    <div style="display:flex;align-items:flex-end;gap:14px;margin-top:10px;">
      <div class="score">{report.visibility_score:.1f}</div>
      <div class="muted" style="padding-bottom:8px;">/ 100 visibility</div>
    </div>
  </div>

  <div class="card">
    {_sov_html_section(report)}
  </div>

  <div class="card">
    {_score_breakdown_html(report)}
    {_sentiment_donut_html(report)}
  </div>

  {f'<div class="card">{_stability_html_section(report)}</div>' if report.stability else ""}

  {f'<div class="card">{competitor_rows}</div>' if competitor_rows else ""}

  {f'<div class="card">{spark}</div>' if spark else ""}

  {f'<div class="card">{citations}</div>' if citations else ""}

  <p class="muted" style="text-align:center;">
    Scan {report.scan_duration_seconds:.1f}s &middot;
    Providers: {_esc(", ".join(report.providers_used))}{cost} &middot;
    Generated by PromptBeacon</p>
</body>
</html>"""
