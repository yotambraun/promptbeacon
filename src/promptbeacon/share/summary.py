"""CI summaries: GitHub step outputs, a Markdown job summary, and PR comments.

Used by ``promptbeacon ci`` and the GitHub Action. Everything here is a pure
function of a :class:`Report`, so it is easy to test and to reuse in other CI
systems.
"""

from __future__ import annotations

from promptbeacon.core.schemas import Report
from promptbeacon.reporting.formats import describe_cost

# Hidden marker that identifies PromptBeacon's sticky PR comment.
COMMENT_MARKER = "<!-- promptbeacon-report -->"

_TIER_TEXT = {
    "demo": "demo data (not a real measurement)",
    "base_model": "base model (training memory, no web search)",
    "api_grounded": "web-grounded (provider web search)",
}

_PROVIDER_NAMES = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google": "Google",
    "mistral": "Mistral",
    "cohere": "Cohere",
    "perplexity": "Perplexity",
}


def _md(text: str) -> str:
    """Escape text for a Markdown table cell / inline context."""
    out = text.replace("\\", "\\\\").replace("|", "\\|")
    for ch in "*_`[]<>":
        out = out.replace(ch, "\\" + ch)
    return out.replace("\n", " ")


def ci_outputs(report: Report, passed: bool | None = None) -> dict[str, str]:
    """Key/value outputs for ``$GITHUB_OUTPUT`` (all values are strings)."""
    sov = report.share_of_voice
    outputs = {
        "score": f"{report.visibility_score:.1f}",
        "share-of-voice": f"{sov.target_share:.4f}" if sov else "",
        "rank": str(sov.target_rank) if sov else "",
        "presence": f"{sov.target_presence_rate:.4f}" if sov else "",
        "stability": f"{report.stability.stability_score:.1f}"
        if report.stability
        else "",
        "tier": report.measurement_tier,
        "category": ", ".join(report.categories),
        "cost-usd": f"{report.total_cost_usd:.6f}" if report.total_cost_usd else "",
    }
    if passed is not None:
        outputs["passed"] = "true" if passed else "false"
    return outputs


def summary_markdown(
    report: Report,
    *,
    failures: list[str] | None = None,
    thresholds: dict[str, float] | None = None,
    marker: bool = False,
    max_rows: int = 10,
) -> str:
    """A compact Markdown report for job summaries and PR comments."""
    lines: list[str] = []
    if marker:
        lines.append(COMMENT_MARKER)
    topic = f" · {_md(', '.join(report.categories))}" if report.categories else ""
    lines.append(f"### AI visibility: {_md(report.brand)}{topic}")
    lines.append("")

    sov = report.share_of_voice
    parts = [f"**{report.visibility_score:.0f}/100** visibility score"]
    if sov and sov.aggregate:
        total = len(sov.aggregate)
        parts.append(
            f"**{sov.target_share:.0%}** share of voice (rank {sov.target_rank} "
            f"of {total})"
        )
        entry = sov.aggregate.get(report.brand)
        if entry:
            parts.append(f"in {entry.appearances}/{entry.total_prompts} answers")
    if report.stability:
        parts.append(f"stability {report.stability.stability_score:.0f}/100")
    lines.append(" · ".join(parts))
    lines.append("")

    if sov and sov.aggregate:
        lines.append("| Brand | Answers mentioning it | Share of voice |")
        lines.append("|---|---:|---:|")
        entries = sorted(
            sov.aggregate.values(),
            key=lambda e: (-e.appearances, e.brand_name != report.brand),
        )
        shown = entries[:max_rows]
        if not any(e.brand_name == report.brand for e in shown):
            shown = shown[: max_rows - 1] + [sov.aggregate[report.brand]]
        for e in shown:
            name = _md(e.brand_name)
            if e.brand_name == report.brand:
                name = f"**{name}**"
            lines.append(
                f"| {name} | {e.appearances}/{e.total_prompts} | "
                f"{e.share_of_voice:.0%} |"
            )
        if len(entries) > len(shown):
            lines.append(f"| … {len(entries) - len(shown)} more | | |")
        lines.append("")

    if thresholds:
        rules = ", ".join(f"{k} {v:g}" for k, v in thresholds.items())
        if failures:
            lines.append(f"**Failed** ({rules}):")
            lines.extend(f"- {_md(f)}" for f in failures)
        else:
            lines.append(f"**Passed** ({rules})")
        lines.append("")

    models = sorted(
        {
            f"{_PROVIDER_NAMES.get(r.provider, r.provider)} {r.model}"
            for r in report.provider_results
        }
    )
    prompts = len({r.prompt for r in report.provider_results})
    meta = [
        f"Measured: {_TIER_TEXT.get(report.measurement_tier, report.measurement_tier)}",
        f"{prompts} prompts",
    ]
    if models:
        meta.append(_md(", ".join(models)))
    cost = describe_cost(report)
    if cost:
        meta.append(f"cost {cost}")
    lines.append("<sub>" + " · ".join(meta) + " · measured with "
                 "[PromptBeacon](https://github.com/yotambraun/promptbeacon)</sub>")  # fmt: skip
    return "\n".join(lines) + "\n"


def report_summary(report: Report, *, max_brands: int = 10) -> dict:
    """A compact, JSON-serialisable view of a report (for tools and agents).

    Omits raw model responses; includes the numbers people act on.
    """
    sov = report.share_of_voice
    brands = []
    if sov and sov.aggregate:
        for e in sorted(
            sov.aggregate.values(),
            key=lambda e: (-e.appearances, e.brand_name != report.brand),
        )[:max_brands]:
            brands.append(
                {
                    "brand": e.brand_name,
                    "is_target": e.brand_name == report.brand,
                    "answers_mentioning": e.appearances,
                    "answers_total": e.total_prompts,
                    "share_of_voice": round(e.share_of_voice, 4),
                }
            )
    sources = []
    if report.source_attribution:
        sources = [
            {
                "domain": s.domain,
                "type": s.source_type,
                "citations": s.citations,
                "cites_target": s.cites_target,
            }
            for s in report.source_attribution.entries[:10]
        ]
    return {
        "brand": report.brand,
        "categories": report.categories,
        "prompt_strategy": report.prompt_strategy,
        "measurement_tier": report.measurement_tier,
        "visibility_score": round(report.visibility_score, 1),
        "share_of_voice": round(sov.target_share, 4) if sov else None,
        "rank": sov.target_rank if sov else None,
        "presence_rate": round(sov.target_presence_rate, 4) if sov else None,
        "stability_score": round(report.stability.stability_score, 1)
        if report.stability
        else None,
        "brands": brands,
        "top_sources": sources,
        "models": sorted({f"{r.provider}/{r.model}" for r in report.provider_results}),
        "prompts": len({r.prompt for r in report.provider_results}),
        "cost": describe_cost(report),
        "recommendations": [r.action for r in report.recommendations[:3]],
        "timestamp": report.timestamp.isoformat(),
    }
