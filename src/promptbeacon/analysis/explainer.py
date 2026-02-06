"""Explanation generation for visibility changes and patterns."""

from __future__ import annotations

from typing import Literal

from promptbeacon.core.schemas import (
    BrandMention,
    Explanation,
    ProviderResult,
    Recommendation,
    SentimentBreakdown,
)
from promptbeacon.extraction.sentiment import aggregate_mention_sentiment


def generate_explanations(
    results: list[ProviderResult],
    brand: str,
    visibility_score: float,
    _competitors: list[str] | None = None,
) -> list[Explanation]:
    """Generate explanations for visibility patterns.

    Args:
        results: List of provider results.
        brand: The target brand.
        visibility_score: Current visibility score.
        competitors: Optional list of competitors.

    Returns:
        List of explanations.
    """
    explanations: list[Explanation] = []

    # Collect brand mentions
    brand_mentions = []
    for result in results:
        brand_mentions.extend(
            [m for m in result.mentions if m.brand_name.lower() == brand.lower()]
        )

    # Explain visibility level
    if visibility_score >= 70:
        explanations.append(
            Explanation(
                category="visibility",
                message=f"{brand} has strong visibility in LLM responses",
                evidence=[m.context[:100] for m in brand_mentions[:3]],
                impact="high",
            )
        )
    elif visibility_score >= 40:
        explanations.append(
            Explanation(
                category="visibility",
                message=f"{brand} has moderate visibility with room for improvement",
                evidence=[m.context[:100] for m in brand_mentions[:2]],
                impact="medium",
            )
        )
    else:
        explanations.append(
            Explanation(
                category="visibility",
                message=f"{brand} has low visibility in LLM responses",
                evidence=[],
                impact="high",
            )
        )

    # Explain sentiment patterns
    if brand_mentions:
        sentiment = aggregate_mention_sentiment(brand_mentions)
        explanations.extend(_explain_sentiment(brand, sentiment, brand_mentions))

    # Explain recommendation patterns
    recommendations = [m for m in brand_mentions if m.is_recommendation]
    if recommendations:
        explanations.append(
            Explanation(
                category="recommendations",
                message=f"{brand} is actively recommended in {len(recommendations)} responses",
                evidence=[m.context[:100] for m in recommendations[:2]],
                impact="high",
            )
        )
    elif brand_mentions:
        explanations.append(
            Explanation(
                category="recommendations",
                message=f"{brand} is mentioned but rarely explicitly recommended",
                evidence=[],
                impact="medium",
            )
        )

    # Explain provider differences
    provider_explanations = _explain_provider_differences(results, brand)
    explanations.extend(provider_explanations)

    return explanations


def _explain_sentiment(
    brand: str,
    sentiment: SentimentBreakdown,
    mentions: list[BrandMention],
) -> list[Explanation]:
    """Generate explanations for sentiment patterns."""
    explanations = []

    if sentiment.positive > 0.6:
        positive_mentions = [m for m in mentions if m.sentiment == "positive"]
        explanations.append(
            Explanation(
                category="sentiment",
                message=f"{brand} is mentioned predominantly in positive contexts",
                evidence=[m.context[:100] for m in positive_mentions[:2]],
                impact="high",
            )
        )
    elif sentiment.negative > 0.4:
        negative_mentions = [m for m in mentions if m.sentiment == "negative"]
        explanations.append(
            Explanation(
                category="sentiment",
                message=f"{brand} has concerning negative sentiment in some responses",
                evidence=[m.context[:100] for m in negative_mentions[:2]],
                impact="high",
            )
        )
    else:
        explanations.append(
            Explanation(
                category="sentiment",
                message=f"{brand} sentiment is mixed or neutral across responses",
                evidence=[],
                impact="low",
            )
        )

    return explanations


def _explain_provider_differences(
    results: list[ProviderResult],
    brand: str,
) -> list[Explanation]:
    """Generate explanations for differences between providers."""
    explanations: list[Explanation] = []

    # Group by provider
    by_provider: dict[str, list[ProviderResult]] = {}
    for result in results:
        if result.provider not in by_provider:
            by_provider[result.provider] = []
        by_provider[result.provider].append(result)

    if len(by_provider) < 2:
        return explanations

    # Calculate mention rate per provider
    provider_mention_rates: dict[str, float] = {}
    for provider, provider_results in by_provider.items():
        mentions = sum(
            1
            for r in provider_results
            if any(m.brand_name.lower() == brand.lower() for m in r.mentions)
        )
        provider_mention_rates[provider] = mentions / len(provider_results)

    # Find significant differences
    rates = list(provider_mention_rates.values())
    if max(rates) - min(rates) > 0.3:
        best_provider = max(
            provider_mention_rates, key=lambda k: provider_mention_rates[k]
        )
        worst_provider = min(
            provider_mention_rates, key=lambda k: provider_mention_rates[k]
        )
        explanations.append(
            Explanation(
                category="provider_variance",
                message=(
                    f"{brand} visibility varies significantly across providers: "
                    f"highest on {best_provider}, lowest on {worst_provider}"
                ),
                evidence=[],
                impact="medium",
            )
        )

    return explanations


def generate_recommendations(
    results: list[ProviderResult],
    brand: str,
    visibility_score: float,
    sentiment: SentimentBreakdown,
    competitors: list[str] | None = None,
) -> list[Recommendation]:
    """Generate evidence-based recommendations for improving visibility.

    Recommendations reference actual scan data (prompt categories, contexts,
    provider names, competitor score gaps) so users know *exactly* what to
    address rather than receiving generic advice.

    Args:
        results: List of provider results.
        brand: The target brand.
        visibility_score: Current visibility score.
        sentiment: Current sentiment breakdown.
        competitors: Optional list of competitors.

    Returns:
        List of recommendations.
    """
    recommendations: list[Recommendation] = []

    # Collect brand mentions and per-query hit/miss info
    brand_mentions: list[BrandMention] = []
    successful_results = [r for r in results if r.success]
    queries_with_mention: list[ProviderResult] = []
    queries_without_mention: list[ProviderResult] = []

    for result in successful_results:
        hits = [m for m in result.mentions if m.brand_name.lower() == brand.lower()]
        brand_mentions.extend(hits)
        if hits:
            queries_with_mention.append(result)
        else:
            queries_without_mention.append(result)

    total_queries = len(successful_results)

    # --- LOW VISIBILITY ---
    if visibility_score < 40:
        # Find which prompt categories missed the brand
        missed_prompts = [r.prompt for r in queries_without_mention[:5]]
        mentioned_count = len(queries_with_mention)
        detail = f"Your brand appeared in {mentioned_count}/{total_queries} queries."
        if missed_prompts:
            sample = "', '".join(missed_prompts[:3])
            detail += f" Queries like '{sample}' did not mention you."

        recommendations.append(
            Recommendation(
                action="Improve brand presence in AI knowledge sources",
                rationale=detail,
                priority="high",
                expected_impact="Higher mention frequency across LLM providers",
            )
        )

    # --- NEGATIVE SENTIMENT ---
    negative_mentions = [m for m in brand_mentions if m.sentiment == "negative"]
    if sentiment.negative > 0.3 and negative_mentions:
        snippets = [m.context[:120] for m in negative_mentions[:3]]
        snippet_text = " | ".join(f'"{s}"' for s in snippets)
        recommendations.append(
            Recommendation(
                action="Address negative sentiment in AI responses",
                rationale=(
                    f"{len(negative_mentions)} mention(s) had negative sentiment. "
                    f"Examples: {snippet_text}"
                ),
                priority="high",
                expected_impact="Improved brand perception in AI responses",
            )
        )

    if sentiment.positive < 0.4 and not (sentiment.negative > 0.3):
        recommendations.append(
            Recommendation(
                action="Amplify positive brand stories",
                rationale=(
                    f"Only {sentiment.positive:.0%} of mentions were positive. "
                    "Increase positive content through case studies, testimonials, "
                    "and success stories."
                ),
                priority="medium",
                expected_impact="More positive brand associations",
            )
        )

    # --- RECOMMENDATION RATE ---
    recommendation_count = sum(1 for m in brand_mentions if m.is_recommendation)
    recommendation_rate = (
        recommendation_count / len(brand_mentions) if brand_mentions else 0
    )

    if recommendation_rate < 0.2:
        recommendations.append(
            Recommendation(
                action="Build recommendation-worthy content",
                rationale=(
                    f"Only {recommendation_rate:.0%} of mentions included an explicit "
                    "recommendation. LLMs recommend brands they associate with quality "
                    "and user satisfaction."
                ),
                priority="medium",
                expected_impact="Higher recommendation rate in AI responses",
            )
        )

    # --- PROVIDER VARIANCE ---
    by_provider: dict[str, list[ProviderResult]] = {}
    for result in successful_results:
        by_provider.setdefault(result.provider, []).append(result)

    if len(by_provider) > 1:
        provider_rates: dict[str, float] = {}
        for provider, provider_results in by_provider.items():
            mentions = sum(
                1
                for r in provider_results
                if any(m.brand_name.lower() == brand.lower() for m in r.mentions)
            )
            provider_rates[provider] = mentions / len(provider_results)

        best_provider = max(provider_rates, key=lambda k: provider_rates[k])
        worst_provider = min(provider_rates, key=lambda k: provider_rates[k])
        if provider_rates[worst_provider] < 0.3:
            recommendations.append(
                Recommendation(
                    action=f"Investigate low visibility on {worst_provider}",
                    rationale=(
                        f"Visibility on {worst_provider} ({provider_rates[worst_provider]:.0%}) "
                        f"is significantly lower than {best_provider} "
                        f"({provider_rates[best_provider]:.0%})."
                    ),
                    priority="medium",
                    expected_impact=f"Improved visibility on {worst_provider}",
                )
            )

    # --- COMPETITOR GAP ---
    if competitors:
        from promptbeacon.analysis.scorer import calculate_visibility_score

        for comp in competitors:
            comp_score = calculate_visibility_score(results, comp)
            gap = comp_score - visibility_score
            if gap > 10:
                # Figure out what drives the gap
                comp_mentions = [
                    m
                    for r in results
                    for m in r.mentions
                    if m.brand_name.lower() == comp.lower()
                ]
                comp_rec_rate = (
                    sum(1 for m in comp_mentions if m.is_recommendation)
                    / len(comp_mentions)
                    if comp_mentions
                    else 0
                )
                driver = ""
                if comp_rec_rate > recommendation_rate + 0.1:
                    driver = " driven by a higher recommendation rate"
                recommendations.append(
                    Recommendation(
                        action=f"Close the gap with {comp}",
                        rationale=(
                            f"{comp} scores {comp_score:.0f} vs your {visibility_score:.0f} "
                            f"— a {gap:.0f}-point gap{driver}."
                        ),
                        priority="high" if gap > 20 else "medium",
                        expected_impact=f"Reduced competitive gap with {comp}",
                    )
                )

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    recommendations.sort(key=lambda r: priority_order.get(r.priority, 1))

    return recommendations


def explain_change(
    previous_score: float,
    current_score: float,
    _previous_results: list[ProviderResult] | None = None,
    _current_results: list[ProviderResult] | None = None,
    _brand: str = "",
) -> list[Explanation]:
    """Generate explanations for score changes between scans.

    Args:
        previous_score: Previous visibility score.
        current_score: Current visibility score.
        previous_results: Optional previous scan results.
        current_results: Optional current scan results.
        brand: The brand name.

    Returns:
        List of explanations for the change.
    """
    explanations: list[Explanation] = []
    change = current_score - previous_score

    if abs(change) < 2:
        explanations.append(
            Explanation(
                category="change",
                message=f"Visibility score remained stable ({change:+.1f} points)",
                evidence=[],
                impact="low",
            )
        )
    elif change > 0:
        impact: Literal["high", "medium", "low"] = "high" if change > 10 else "medium"
        explanations.append(
            Explanation(
                category="change",
                message=f"Visibility improved by {change:.1f} points",
                evidence=[],
                impact=impact,
            )
        )
    else:
        impact_neg: Literal["high", "medium", "low"] = (
            "high" if change < -10 else "medium"
        )
        explanations.append(
            Explanation(
                category="change",
                message=f"Visibility decreased by {abs(change):.1f} points",
                evidence=[],
                impact=impact_neg,
            )
        )

    return explanations
