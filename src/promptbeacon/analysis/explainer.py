"""Explanation generation for visibility changes and patterns."""

from __future__ import annotations

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
    competitors: list[str] | None = None,
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
    explanations = []

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
        best_provider = max(provider_mention_rates, key=provider_mention_rates.get)
        worst_provider = min(provider_mention_rates, key=provider_mention_rates.get)
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
    """Generate actionable recommendations for improving visibility.

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

    # Low visibility recommendations
    if visibility_score < 40:
        recommendations.append(
            Recommendation(
                action="Increase brand content in AI training sources",
                rationale=(
                    "LLMs learn from public content. Ensure your brand has strong presence "
                    "in Wikipedia, news articles, review sites, and authoritative sources."
                ),
                priority="high",
                expected_impact="Significant improvement in brand mention frequency",
            )
        )
        recommendations.append(
            Recommendation(
                action="Create comprehensive brand documentation",
                rationale=(
                    "Detailed, factual documentation about your products helps LLMs "
                    "provide accurate information when asked."
                ),
                priority="high",
                expected_impact="More accurate brand representations in responses",
            )
        )

    # Sentiment recommendations
    if sentiment.negative > 0.3:
        recommendations.append(
            Recommendation(
                action="Address negative sentiment sources",
                rationale=(
                    "Negative sentiment in LLM responses may stem from reviews, news, "
                    "or other public content. Identify and address root causes."
                ),
                priority="high",
                expected_impact="Improved brand perception in AI responses",
            )
        )

    if sentiment.positive < 0.4:
        recommendations.append(
            Recommendation(
                action="Amplify positive brand stories",
                rationale=(
                    "Increase positive content through case studies, testimonials, "
                    "and success stories that can be indexed by AI systems."
                ),
                priority="medium",
                expected_impact="More positive brand associations",
            )
        )

    # Recommendation rate
    brand_mentions = []
    for result in results:
        brand_mentions.extend(
            [m for m in result.mentions if m.brand_name.lower() == brand.lower()]
        )

    recommendation_count = sum(1 for m in brand_mentions if m.is_recommendation)
    recommendation_rate = recommendation_count / len(brand_mentions) if brand_mentions else 0

    if recommendation_rate < 0.2:
        recommendations.append(
            Recommendation(
                action="Build recommendation-worthy content",
                rationale=(
                    "LLMs recommend brands they associate with quality, reliability, "
                    "and user satisfaction. Focus on building this reputation."
                ),
                priority="medium",
                expected_impact="Higher recommendation rate in AI responses",
            )
        )

    # Provider-specific recommendations
    by_provider: dict[str, list[ProviderResult]] = {}
    for result in results:
        if result.provider not in by_provider:
            by_provider[result.provider] = []
        by_provider[result.provider].append(result)

    if len(by_provider) > 1:
        provider_scores: dict[str, float] = {}
        for provider, provider_results in by_provider.items():
            mentions = sum(
                1
                for r in provider_results
                if any(m.brand_name.lower() == brand.lower() for m in r.mentions)
            )
            provider_scores[provider] = mentions / len(provider_results)

        worst_provider = min(provider_scores, key=provider_scores.get)
        if provider_scores[worst_provider] < 0.3:
            recommendations.append(
                Recommendation(
                    action=f"Investigate low visibility on {worst_provider}",
                    rationale=(
                        f"Your brand has particularly low visibility on {worst_provider}. "
                        "This may indicate gaps in how that AI system perceives your brand."
                    ),
                    priority="medium",
                    expected_impact=f"Improved visibility on {worst_provider}",
                )
            )

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    recommendations.sort(key=lambda r: priority_order.get(r.priority, 1))

    return recommendations


def explain_change(
    previous_score: float,
    current_score: float,
    previous_results: list[ProviderResult] | None = None,
    current_results: list[ProviderResult] | None = None,
    brand: str = "",
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
    explanations = []
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
        impact = "high" if change > 10 else "medium"
        explanations.append(
            Explanation(
                category="change",
                message=f"Visibility improved by {change:.1f} points",
                evidence=[],
                impact=impact,
            )
        )
    else:
        impact = "high" if change < -10 else "medium"
        explanations.append(
            Explanation(
                category="change",
                message=f"Visibility decreased by {abs(change):.1f} points",
                evidence=[],
                impact=impact,
            )
        )

    return explanations
