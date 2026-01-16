"""Brand mention extraction from LLM responses."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from promptbeacon.core.schemas import BrandMention


class MentionExtractionResult(BaseModel):
    """Result of extracting mentions from a response."""

    mentions: list[BrandMention] = Field(default_factory=list)
    total_mentions: int = 0
    brands_found: list[str] = Field(default_factory=list)


def extract_mentions(
    response: str,
    target_brand: str,
    competitors: list[str] | None = None,
) -> MentionExtractionResult:
    """Extract brand mentions from an LLM response.

    Args:
        response: The LLM response text.
        target_brand: The main brand to look for.
        competitors: Optional list of competitor brands.

    Returns:
        MentionExtractionResult with extracted mentions.
    """
    all_brands = [target_brand] + (competitors or [])
    mentions: list[BrandMention] = []
    brands_found: set[str] = set()
    position = 0

    for brand in all_brands:
        # Find all occurrences of the brand (case-insensitive)
        pattern = re.compile(re.escape(brand), re.IGNORECASE)
        for match in pattern.finditer(response):
            start = match.start()
            end = match.end()

            # Extract context (surrounding text)
            context_start = max(0, start - 100)
            context_end = min(len(response), end + 100)
            context = response[context_start:context_end]
            if context_start > 0:
                context = "..." + context
            if context_end < len(response):
                context = context + "..."

            # Determine sentiment from context
            sentiment = analyze_mention_sentiment(context)

            # Check if this is a recommendation
            is_recommendation = is_brand_recommended(context, brand)

            mentions.append(
                BrandMention(
                    brand_name=brand,
                    sentiment=sentiment,
                    position=position,
                    context=context.strip(),
                    confidence=0.9,  # Base confidence for regex matching
                    is_recommendation=is_recommendation,
                )
            )
            brands_found.add(brand)
            position += 1

    return MentionExtractionResult(
        mentions=mentions,
        total_mentions=len(mentions),
        brands_found=list(brands_found),
    )


def analyze_mention_sentiment(
    context: str,
) -> Literal["positive", "neutral", "negative"]:
    """Analyze the sentiment of a brand mention based on context.

    Args:
        context: The text context around the mention.

    Returns:
        Sentiment classification.
    """
    context_lower = context.lower()

    # Positive indicators
    positive_words = [
        "excellent",
        "great",
        "best",
        "recommend",
        "top",
        "leading",
        "outstanding",
        "superior",
        "preferred",
        "trusted",
        "reliable",
        "innovative",
        "quality",
        "love",
        "amazing",
        "fantastic",
        "popular",
        "well-known",
        "reputable",
        "highly rated",
        "favorite",
        "top-rated",
        "premium",
    ]

    # Negative indicators
    negative_words = [
        "poor",
        "bad",
        "worst",
        "avoid",
        "disappointing",
        "inferior",
        "unreliable",
        "problems",
        "issues",
        "complaints",
        "expensive",
        "overpriced",
        "lacking",
        "criticized",
        "concerns",
        "controversy",
        "scandal",
        "lawsuit",
        "recall",
        "warning",
    ]

    positive_count = sum(1 for word in positive_words if word in context_lower)
    negative_count = sum(1 for word in negative_words if word in context_lower)

    if positive_count > negative_count:
        return "positive"
    elif negative_count > positive_count:
        return "negative"
    return "neutral"


def is_brand_recommended(context: str, brand: str) -> bool:
    """Check if a brand is being explicitly recommended in the context.

    Args:
        context: The text context around the mention.
        brand: The brand name.

    Returns:
        True if the brand appears to be recommended.
    """
    context_lower = context.lower()
    brand_lower = brand.lower()

    recommendation_patterns = [
        f"recommend {brand_lower}",
        f"i recommend {brand_lower}",
        f"would recommend {brand_lower}",
        f"suggest {brand_lower}",
        f"try {brand_lower}",
        f"go with {brand_lower}",
        f"choose {brand_lower}",
        f"best option is {brand_lower}",
        f"top choice is {brand_lower}",
        f"{brand_lower} is a great choice",
        f"{brand_lower} is the best",
        f"{brand_lower} is recommended",
        f"consider {brand_lower}",
    ]

    return any(pattern in context_lower for pattern in recommendation_patterns)


def count_brand_mentions(response: str, brand: str) -> int:
    """Count the number of times a brand is mentioned.

    Args:
        response: The LLM response text.
        brand: The brand to count.

    Returns:
        Number of mentions.
    """
    pattern = re.compile(re.escape(brand), re.IGNORECASE)
    return len(pattern.findall(response))


def get_mention_positions(response: str, brand: str) -> list[int]:
    """Get character positions of all brand mentions.

    Args:
        response: The LLM response text.
        brand: The brand to find.

    Returns:
        List of character positions.
    """
    pattern = re.compile(re.escape(brand), re.IGNORECASE)
    return [match.start() for match in pattern.finditer(response)]


def calculate_mention_prominence(response: str, brand: str) -> float:
    """Calculate how prominently a brand is mentioned.

    Prominence is based on:
    - Position in response (earlier = more prominent)
    - Frequency of mentions
    - Context quality

    Args:
        response: The LLM response text.
        brand: The brand to analyze.

    Returns:
        Prominence score from 0.0 to 1.0.
    """
    positions = get_mention_positions(response, brand)
    if not positions:
        return 0.0

    # Factor 1: First mention position (earlier is better)
    first_position = positions[0]
    position_score = max(0, 1 - (first_position / len(response)))

    # Factor 2: Frequency (more mentions = higher score, with diminishing returns)
    mention_count = len(positions)
    frequency_score = min(1.0, mention_count / 5)

    # Combined score
    prominence = (position_score * 0.6) + (frequency_score * 0.4)
    return round(prominence, 3)
