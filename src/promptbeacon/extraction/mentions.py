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
    aliases: list[str] | None = None,
) -> MentionExtractionResult:
    """Extract brand mentions from an LLM response.

    Args:
        response: The LLM response text.
        target_brand: The main brand to look for.
        competitors: Optional list of competitor brands.
        aliases: Optional alternative names for the target brand.
            Matches are credited to ``target_brand``.

    Returns:
        MentionExtractionResult with extracted mentions.
    """
    # Map alias -> canonical brand name so mentions are credited correctly
    alias_map: dict[str, str] = {}
    for alias in aliases or []:
        alias_map[alias] = target_brand

    all_brands = [target_brand] + (aliases or []) + (competitors or [])
    mentions: list[BrandMention] = []
    brands_found: set[str] = set()
    position = 0

    for brand in all_brands:
        # Find all occurrences of the brand (case-insensitive)
        pattern = re.compile(re.escape(brand), re.IGNORECASE)
        # Precompile word-boundary pattern for this brand
        word_boundary_pattern = re.compile(
            r"\b" + re.escape(brand) + r"\b", re.IGNORECASE
        )
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

            # Calculate confidence from signal quality
            confidence = _calculate_mention_confidence(
                response, brand, match, sentiment, word_boundary_pattern
            )

            # Credit aliases to the canonical brand name
            canonical_name = alias_map.get(brand, brand)

            mentions.append(
                BrandMention(
                    brand_name=canonical_name,
                    sentiment=sentiment,
                    position=position,
                    context=context.strip(),
                    confidence=confidence,
                    is_recommendation=is_recommendation,
                )
            )
            brands_found.add(canonical_name)
            position += 1

    return MentionExtractionResult(
        mentions=mentions,
        total_mentions=len(mentions),
        brands_found=list(brands_found),
    )


def _calculate_mention_confidence(
    response: str,
    brand: str,
    match: re.Match,
    sentiment: str,
    word_boundary_pattern: re.Pattern,
) -> float:
    """Calculate confidence score from signal quality.

    The score honestly reflects what a regex-only extraction can claim:
      - Base 0.5 (a regex match exists)
      - +0.1 for exact case match (the response used the brand's casing)
      - +0.1 for clean word boundaries (not a substring of another word)
      - +0.05 per sentiment signal found, up to +0.1

    Resulting range: 0.5 – 0.8.
    """
    confidence = 0.5

    # Exact case match bonus
    matched_text = response[match.start() : match.end()]
    if matched_text == brand:
        confidence += 0.1

    # Clean word-boundary bonus
    if word_boundary_pattern.search(
        response[match.start() : match.end() + 1]
        if match.end() < len(response)
        else response[match.start() : match.end()]
    ):
        # Verify the actual match position has word boundaries
        before_ok = match.start() == 0 or not response[match.start() - 1].isalnum()
        after_ok = match.end() == len(response) or not response[match.end()].isalnum()
        if before_ok and after_ok:
            confidence += 0.1

    # Sentiment signal bonus (+0.05 per signal, up to +0.1)
    if sentiment != "neutral":
        confidence += 0.1
    # (neutral sentiment = no sentiment signals detected = no bonus)

    return round(min(0.8, confidence), 2)


NEGATION_PREFIXES = [
    "not ",
    "no ",
    "never ",
    "isn't ",
    "isnt ",
    "don't ",
    "dont ",
    "doesn't ",
    "doesnt ",
    "wasn't ",
    "wasnt ",
    "weren't ",
    "werent ",
    "won't ",
    "wont ",
    "wouldn't ",
    "wouldnt ",
    "shouldn't ",
    "shouldnt ",
    "hardly ",
    "barely ",
    "neither ",
    "nor ",
]


def _is_negated(text: str, keyword: str) -> bool:
    """Check if a keyword is negated by looking at the preceding ~4 words.

    Args:
        text: The lowercased text to search in.
        keyword: The keyword to check for negation.

    Returns:
        True if the keyword is preceded by a negation word.
    """
    idx = text.find(keyword)
    if idx < 0:
        return False
    # Look at the ~40 characters before the keyword (roughly 4 words)
    window_start = max(0, idx - 40)
    window = text[window_start:idx]
    return any(neg in window for neg in NEGATION_PREFIXES)


def analyze_mention_sentiment(
    context: str,
) -> Literal["positive", "neutral", "negative"]:
    """Analyze the sentiment of a brand mention based on context.

    Uses keyword matching with negation detection: if a negation word
    appears in the ~4 words preceding a keyword, its polarity is flipped.

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

    positive_count = 0
    negative_count = 0

    for word in positive_words:
        if word in context_lower:
            if _is_negated(context_lower, word):
                negative_count += 1  # Negated positive -> negative
            else:
                positive_count += 1

    for word in negative_words:
        if word in context_lower:
            if _is_negated(context_lower, word):
                positive_count += 1  # Negated negative -> positive
            else:
                negative_count += 1

    if positive_count > negative_count:
        return "positive"
    elif negative_count > positive_count:
        return "negative"
    return "neutral"


def is_brand_recommended(context: str, brand: str) -> bool:
    """Check if a brand is being explicitly recommended in the context.

    Anti-recommendation patterns (e.g. "recommend against Nike") are checked
    first.  If any match, the function returns ``False`` immediately so that
    negative advice is never mistaken for a positive recommendation.

    Args:
        context: The text context around the mention.
        brand: The brand name.

    Returns:
        True if the brand appears to be positively recommended.
    """
    context_lower = context.lower()
    brand_lower = brand.lower()

    # Check anti-recommendation patterns FIRST — if any match, it's not a rec.
    anti_patterns = [
        f"don't recommend {brand_lower}",
        f"dont recommend {brand_lower}",
        f"do not recommend {brand_lower}",
        f"wouldn't recommend {brand_lower}",
        f"wouldnt recommend {brand_lower}",
        f"would not recommend {brand_lower}",
        f"cannot recommend {brand_lower}",
        f"can't recommend {brand_lower}",
        f"recommend against {brand_lower}",
        f"advise against {brand_lower}",
        f"avoid {brand_lower}",
        f"stay away from {brand_lower}",
        f"steer clear of {brand_lower}",
        f"not suggest {brand_lower}",
        f"never recommend {brand_lower}",
        f"stop recommending {brand_lower}",
        f"{brand_lower} is not recommended",
        f"{brand_lower} isn't recommended",
    ]

    if any(pattern in context_lower for pattern in anti_patterns):
        return False

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
