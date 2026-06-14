"""LLM-generated, evidence-linked recommendations (opt-in).

Rule-based recommendations are generic. Smart mode feeds the scan's own numbers
and evidence quotes to an LLM and asks for prioritized, specific guidance on how
to improve the brand's AI visibility. Prompt-building and parsing are pure
(testable without keys); ``Beacon`` makes the one extra LLM call and falls back
to the rule-based recommendations on any error.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from promptbeacon.core.schemas import Recommendation

if TYPE_CHECKING:
    from promptbeacon.core.schemas import Report

_VALID_PRIORITIES = {"high", "medium", "low"}


def build_recommendations_prompt(report: Report) -> str:
    """Build a prompt asking an LLM for evidence-linked recommendations."""
    sov = report.share_of_voice
    sov_line = (
        f"Share of Voice: {sov.target_share:.0%} (rank {sov.target_rank}, "
        f"appears in {sov.target_presence_rate:.0%} of prompts)."
        if sov
        else "Share of Voice: not computed."
    )
    competitors = (
        ", ".join(
            f"{name} ({c.visibility_score:.0f})"
            for name, c in list(report.competitor_comparison.items())[:5]
        )
        or "none tracked"
    )

    # A few real evidence quotes from the responses.
    quotes: list[str] = []
    for result in report.provider_results:
        for m in result.mentions:
            if m.context:
                quotes.append(m.context[:160])
            if len(quotes) >= 5:
                break
        if len(quotes) >= 5:
            break
    evidence = "\n".join(f"- {q}" for q in quotes) or "- (no direct mentions found)"

    return (
        "You are a Generative Engine Optimization (GEO) strategist. Based on the "
        f'AI-visibility scan below for the brand "{report.brand}", produce '
        "specific, actionable recommendations to improve how AI assistants "
        "mention and recommend this brand.\n\n"
        "SCAN RESULTS\n"
        f"- Visibility score: {report.visibility_score:.1f}/100\n"
        f"- {sov_line}\n"
        f"- Sentiment: {report.sentiment_breakdown.positive:.0%} positive, "
        f"{report.sentiment_breakdown.negative:.0%} negative\n"
        f"- Competitors (visibility score): {competitors}\n"
        f"- Sample evidence from AI responses:\n{evidence}\n\n"
        "Return ONLY a JSON object, no prose, in exactly this shape:\n"
        '{"recommendations": [{"action": "<concrete step>", '
        '"rationale": "<why, referencing the data above>", '
        '"priority": "high|medium|low", '
        '"expected_impact": "<what improves if done>"}]}\n'
        "Give 3-5 recommendations, ordered most important first. Be specific to "
        "this brand and these results — not generic SEO advice."
    )


def _strip_code_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


def parse_recommendations(raw: str) -> list[Recommendation]:
    """Parse an LLM's JSON recommendations into Recommendation objects.

    Raises:
        ValueError: If the output cannot be parsed, so the caller can fall back.
    """
    try:
        data = json.loads(_strip_code_fences(raw))
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM recommendations were not valid JSON: {e}") from e

    if not isinstance(data, dict) or "recommendations" not in data:
        raise ValueError("LLM recommendations missing 'recommendations' key")

    recs: list[Recommendation] = []
    for item in data.get("recommendations", []):
        if not isinstance(item, dict) or not item.get("action"):
            continue
        priority = str(item.get("priority", "medium")).lower()
        if priority not in _VALID_PRIORITIES:
            priority = "medium"
        recs.append(
            Recommendation(
                action=str(item["action"]),
                rationale=str(item.get("rationale", "")),
                priority=priority,  # type: ignore[arg-type]
                expected_impact=str(item.get("expected_impact", "")),
            )
        )

    if not recs:
        raise ValueError("LLM returned no usable recommendations")
    return recs
