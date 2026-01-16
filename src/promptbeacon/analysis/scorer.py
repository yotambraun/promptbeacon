"""Visibility scoring for brand mentions."""

from __future__ import annotations

from pydantic import BaseModel, Field

from promptbeacon.core.schemas import (
    BrandMention,
    CompetitorScore,
    ProviderResult,
    SentimentBreakdown,
    VisibilityMetrics,
)
from promptbeacon.extraction.mentions import calculate_mention_prominence
from promptbeacon.extraction.ranking import extract_rankings, get_average_position
from promptbeacon.extraction.sentiment import aggregate_mention_sentiment


class ScoringWeights(BaseModel):
    """Weights for visibility score calculation."""

    mention_frequency: float = Field(default=0.3, ge=0.0, le=1.0)
    sentiment: float = Field(default=0.25, ge=0.0, le=1.0)
    position: float = Field(default=0.25, ge=0.0, le=1.0)
    recommendation: float = Field(default=0.2, ge=0.0, le=1.0)


DEFAULT_WEIGHTS = ScoringWeights()


def calculate_visibility_score(
    results: list[ProviderResult],
    brand: str,
    weights: ScoringWeights | None = None,
) -> float:
    """Calculate the overall visibility score for a brand.

    Args:
        results: List of provider results.
        brand: The brand to score.
        weights: Optional custom weights.

    Returns:
        Visibility score from 0 to 100.
    """
    if not results:
        return 0.0

    weights = weights or DEFAULT_WEIGHTS

    # Collect all mentions for the brand
    all_mentions = []
    for result in results:
        brand_mentions = [m for m in result.mentions if m.brand_name.lower() == brand.lower()]
        all_mentions.extend(brand_mentions)

    successful_results = [r for r in results if r.success]
    if not successful_results:
        return 0.0

    # Factor 1: Mention frequency (mentions per query)
    total_queries = len(successful_results)
    queries_with_mention = sum(
        1
        for r in successful_results
        if any(m.brand_name.lower() == brand.lower() for m in r.mentions)
    )
    mention_rate = queries_with_mention / total_queries
    frequency_score = mention_rate * 100

    # Factor 2: Sentiment score
    sentiment_breakdown = aggregate_mention_sentiment(all_mentions)
    # Convert sentiment to 0-100 scale (positive = good)
    sentiment_score = (
        (sentiment_breakdown.positive * 100)
        + (sentiment_breakdown.neutral * 50)
        + (sentiment_breakdown.negative * 0)
    )

    # Factor 3: Position score (earlier mentions = better)
    position_scores = []
    for result in successful_results:
        rankings = extract_rankings(result.response, brand)
        if rankings.brand_positions.get(brand):
            # Normalize position to 0-100 (position 1 = 100, position 10 = 10)
            pos = rankings.brand_positions[brand]
            position_scores.append(max(0, 100 - ((pos - 1) * 10)))
        elif any(m.brand_name.lower() == brand.lower() for m in result.mentions):
            # Brand mentioned but not ranked - partial score
            prominence = calculate_mention_prominence(result.response, brand)
            position_scores.append(prominence * 60)

    position_score = sum(position_scores) / len(position_scores) if position_scores else 0

    # Factor 4: Recommendation rate
    recommendations = sum(1 for m in all_mentions if m.is_recommendation)
    recommendation_rate = recommendations / len(all_mentions) if all_mentions else 0
    recommendation_score = recommendation_rate * 100

    # Weighted combination
    visibility_score = (
        (frequency_score * weights.mention_frequency)
        + (sentiment_score * weights.sentiment)
        + (position_score * weights.position)
        + (recommendation_score * weights.recommendation)
    )

    return round(min(100, max(0, visibility_score)), 1)


def calculate_metrics(
    results: list[ProviderResult],
    brand: str,
) -> VisibilityMetrics:
    """Calculate detailed visibility metrics for a brand.

    Args:
        results: List of provider results.
        brand: The brand to analyze.

    Returns:
        VisibilityMetrics with detailed analysis.
    """
    visibility_score = calculate_visibility_score(results, brand)

    # Collect all mentions
    all_mentions = []
    for result in results:
        brand_mentions = [m for m in result.mentions if m.brand_name.lower() == brand.lower()]
        all_mentions.extend(brand_mentions)

    # Calculate metrics
    mention_count = len(all_mentions)
    sentiment = aggregate_mention_sentiment(all_mentions)

    # Recommendation rate
    recommendations = sum(1 for m in all_mentions if m.is_recommendation)
    recommendation_rate = recommendations / mention_count if mention_count > 0 else 0

    # Average position
    positions = [m.position for m in all_mentions]
    average_position = sum(positions) / len(positions) if positions else None

    return VisibilityMetrics(
        visibility_score=visibility_score,
        mention_count=mention_count,
        recommendation_rate=round(recommendation_rate, 3),
        average_position=round(average_position, 2) if average_position else None,
        sentiment=sentiment,
        confidence_interval=None,  # Calculated separately with statistics module
    )


def calculate_competitor_scores(
    results: list[ProviderResult],
    competitors: list[str],
) -> dict[str, CompetitorScore]:
    """Calculate visibility scores for competitors.

    Args:
        results: List of provider results.
        competitors: List of competitor brand names.

    Returns:
        Dictionary mapping competitor names to their scores.
    """
    scores = {}

    for competitor in competitors:
        visibility_score = calculate_visibility_score(results, competitor)

        # Collect mentions for this competitor
        all_mentions = []
        for result in results:
            comp_mentions = [
                m for m in result.mentions if m.brand_name.lower() == competitor.lower()
            ]
            all_mentions.extend(comp_mentions)

        sentiment = aggregate_mention_sentiment(all_mentions)

        scores[competitor] = CompetitorScore(
            brand_name=competitor,
            visibility_score=visibility_score,
            mention_count=len(all_mentions),
            sentiment=sentiment,
        )

    return scores


def compare_to_competitors(
    brand_score: float,
    competitor_scores: dict[str, CompetitorScore],
) -> dict[str, float]:
    """Compare brand score to competitors.

    Args:
        brand_score: The target brand's visibility score.
        competitor_scores: Dictionary of competitor scores.

    Returns:
        Dictionary with comparison metrics.
    """
    if not competitor_scores:
        return {"share_of_voice": 100.0, "rank": 1, "gap_to_leader": 0.0}

    all_scores = [brand_score] + [c.visibility_score for c in competitor_scores.values()]
    total = sum(all_scores)

    share_of_voice = (brand_score / total * 100) if total > 0 else 0

    # Calculate rank (1 = highest score)
    sorted_scores = sorted(all_scores, reverse=True)
    rank = sorted_scores.index(brand_score) + 1

    # Gap to leader
    leader_score = max(all_scores)
    gap_to_leader = leader_score - brand_score

    return {
        "share_of_voice": round(share_of_voice, 1),
        "rank": rank,
        "gap_to_leader": round(gap_to_leader, 1),
        "average_competitor_score": round(
            sum(c.visibility_score for c in competitor_scores.values())
            / len(competitor_scores),
            1,
        ),
    }
