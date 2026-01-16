"""Sentiment analysis for brand mentions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from promptbeacon.core.schemas import BrandMention, SentimentBreakdown


class SentimentAnalysisResult(BaseModel):
    """Result of sentiment analysis."""

    overall_sentiment: Literal["positive", "neutral", "negative"]
    breakdown: SentimentBreakdown
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    positive_signals: list[str] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)


def analyze_response_sentiment(response: str) -> SentimentAnalysisResult:
    """Analyze the overall sentiment of an LLM response.

    Args:
        response: The LLM response text.

    Returns:
        SentimentAnalysisResult with detailed analysis.
    """
    response_lower = response.lower()

    # Positive indicators with weights
    positive_signals = {
        "excellent": 2,
        "outstanding": 2,
        "best": 1.5,
        "great": 1,
        "good": 0.5,
        "recommend": 1.5,
        "top": 1,
        "leading": 1,
        "innovative": 1,
        "trusted": 1.5,
        "reliable": 1,
        "quality": 1,
        "popular": 0.5,
        "preferred": 1,
        "superior": 1.5,
        "impressive": 1,
        "remarkable": 1,
        "exceptional": 1.5,
    }

    # Negative indicators with weights
    negative_signals = {
        "poor": 1.5,
        "bad": 1,
        "worst": 2,
        "avoid": 2,
        "disappointing": 1.5,
        "unreliable": 1.5,
        "problems": 1,
        "issues": 0.5,
        "complaints": 1,
        "concerning": 1,
        "controversy": 1.5,
        "criticized": 1,
        "lacking": 1,
        "inferior": 1.5,
        "weak": 1,
        "limited": 0.5,
        "expensive": 0.5,
        "overpriced": 1,
    }

    # Calculate scores
    positive_score = sum(
        weight for word, weight in positive_signals.items() if word in response_lower
    )
    negative_score = sum(
        weight for word, weight in negative_signals.items() if word in response_lower
    )

    found_positive = [word for word in positive_signals if word in response_lower]
    found_negative = [word for word in negative_signals if word in response_lower]

    total_score = positive_score + negative_score
    if total_score == 0:
        breakdown = SentimentBreakdown(positive=0.0, neutral=1.0, negative=0.0)
        overall = "neutral"
    else:
        positive_ratio = positive_score / total_score
        negative_ratio = negative_score / total_score
        neutral_ratio = max(0, 1 - positive_ratio - negative_ratio)

        breakdown = SentimentBreakdown(
            positive=round(positive_ratio, 3),
            neutral=round(neutral_ratio, 3),
            negative=round(negative_ratio, 3),
        )

        if positive_ratio > 0.6:
            overall = "positive"
        elif negative_ratio > 0.6:
            overall = "negative"
        else:
            overall = "neutral"

    # Calculate confidence based on signal strength
    confidence = min(0.95, 0.5 + (total_score * 0.05))

    return SentimentAnalysisResult(
        overall_sentiment=overall,
        breakdown=breakdown,
        confidence=confidence,
        positive_signals=found_positive,
        negative_signals=found_negative,
    )


def aggregate_mention_sentiment(mentions: list[BrandMention]) -> SentimentBreakdown:
    """Aggregate sentiment across multiple brand mentions.

    Args:
        mentions: List of brand mentions.

    Returns:
        Aggregated SentimentBreakdown.
    """
    return SentimentBreakdown.from_mentions(mentions)


def calculate_sentiment_score(breakdown: SentimentBreakdown) -> float:
    """Calculate a single sentiment score from breakdown.

    Score ranges from -1 (all negative) to +1 (all positive).

    Args:
        breakdown: The sentiment breakdown.

    Returns:
        Single sentiment score.
    """
    return round(breakdown.positive - breakdown.negative, 3)


def compare_sentiment(
    brand_mentions: list[BrandMention],
    competitor_mentions: list[BrandMention],
) -> dict[str, float]:
    """Compare sentiment between brand and competitors.

    Args:
        brand_mentions: Mentions of the target brand.
        competitor_mentions: Mentions of competitors.

    Returns:
        Dictionary with sentiment comparison metrics.
    """
    brand_breakdown = aggregate_mention_sentiment(brand_mentions)
    competitor_breakdown = aggregate_mention_sentiment(competitor_mentions)

    brand_score = calculate_sentiment_score(brand_breakdown)
    competitor_score = calculate_sentiment_score(competitor_breakdown)

    return {
        "brand_sentiment_score": brand_score,
        "competitor_sentiment_score": competitor_score,
        "sentiment_advantage": round(brand_score - competitor_score, 3),
        "brand_positive_rate": brand_breakdown.positive,
        "competitor_positive_rate": competitor_breakdown.positive,
    }
