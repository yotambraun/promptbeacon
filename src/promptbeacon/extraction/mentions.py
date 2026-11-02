"""Brand mention extraction from LLM responses."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field

from promptbeacon.core.schemas import BrandMention
from promptbeacon.extraction.matching import brand_regex, iter_brand_matches


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

    A brand is matched only as a whole name (see
    :mod:`promptbeacon.extraction.matching`), so "uv" is not found in
    "uvicorn". Mentions are returned in the order they appear in the text.

    Args:
        response: The LLM response text.
        target_brand: The main brand to look for.
        competitors: Optional list of competitor brands.
        aliases: Optional alternative names for the target brand.
            Matches are credited to ``target_brand``.

    Returns:
        MentionExtractionResult with extracted mentions. Each mention's
        ``position`` is its brand's order of first appearance among the
        tracked brands found (0 = the first brand the answer names), and
        ``brands_found`` lists those brands in that order.
    """
    # Map each searched name to the brand it is credited to.
    names: list[tuple[str, str]] = [(target_brand, target_brand)]
    names += [(alias, target_brand) for alias in aliases or []]
    names += [(competitor, competitor) for competitor in competitors or []]

    candidates: list[tuple[str, str, re.Match[str]]] = [
        (canonical, name, match)
        for name, canonical in names
        for match in iter_brand_matches(response, name)
    ]
    # Text order, longest name first at the same place, and one mention per
    # stretch of text for each brand: "Nike Inc" with the alias "Nike Inc" is
    # one mention of Nike, not two.
    candidates.sort(key=lambda c: (c[2].start(), -len(c[2].group(0))))
    found: list[tuple[str, str, re.Match[str]]] = []
    for canonical, name, match in candidates:
        if not any(
            other == canonical
            and match.start() < kept.end()
            and kept.start() < match.end()
            for other, _, kept in found
        ):
            found.append((canonical, name, match))

    order: dict[str, int] = {}
    for canonical, _, _ in found:
        order.setdefault(canonical, len(order))

    mentions: list[BrandMention] = []
    for canonical, name, match in found:
        start, end = match.span()

        # Surrounding text, for sentiment and the evidence quote
        context_start = max(0, start - 100)
        context_end = min(len(response), end + 100)
        context = response[context_start:context_end]
        if context_start > 0:
            context = "..." + context
        if context_end < len(response):
            context = context + "..."

        sentiment = analyze_mention_sentiment(context)
        mentions.append(
            BrandMention(
                brand_name=canonical,
                sentiment=sentiment,
                position=order[canonical],
                context=context.strip(),
                confidence=_calculate_mention_confidence(match, name, sentiment),
                is_recommendation=is_brand_recommended(context, name),
            )
        )

    return MentionExtractionResult(
        mentions=mentions,
        total_mentions=len(mentions),
        brands_found=list(order),
    )


def _calculate_mention_confidence(
    match: re.Match[str],
    brand: str,
    sentiment: str,
) -> float:
    """Calculate confidence score from signal quality.

    The score reflects what a pattern-only extraction can claim:
      - Base 0.6 (the whole name appears; substrings never match)
      - +0.1 for exact case match (the response used the brand's casing)
      - +0.1 when the context carries a sentiment signal

    Resulting range: 0.6 – 0.8.
    """
    confidence = 0.6
    if match.group(0) == brand:
        confidence += 0.1
    if sentiment != "neutral":
        confidence += 0.1
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


# Phrases that recommend (or warn against) the brand that follows or precedes
# them. Matched case-insensitively, on whole words, with the brand as a whole
# name; any run of whitespace separates the words.
_RECOMMEND_BEFORE = (
    "recommend",
    "suggest",
    "try",
    "go with",
    "choose",
    "best option is",
    "top choice is",
    "consider",
)
_RECOMMEND_AFTER = ("is a great choice", "is the best", "is recommended")
_ANTI_BEFORE = (
    "don't recommend",
    "dont recommend",
    "do not recommend",
    "wouldn't recommend",
    "wouldnt recommend",
    "would not recommend",
    "cannot recommend",
    "can't recommend",
    "recommend against",
    "advise against",
    "avoid",
    "stay away from",
    "steer clear of",
    "not suggest",
    "never recommend",
    "stop recommending",
)
_ANTI_AFTER = ("is not recommended", "isn't recommended")


def _phrase_regex(phrases: tuple[str, ...]) -> str:
    alternatives = [
        r"\s+".join(re.escape(word) for word in phrase.split()).replace("'", "['’]")
        for phrase in phrases
    ]
    return "(?:" + "|".join(alternatives) + ")"


@lru_cache(maxsize=512)
def _advice_pattern(brand: str, before: str, after: str) -> re.Pattern[str]:
    name = brand_regex(brand)
    return re.compile(
        rf"(?<!\w){before}\s+{name}|{name}\s+{after}(?!\w)", re.IGNORECASE
    )


_RECOMMEND = (_phrase_regex(_RECOMMEND_BEFORE), _phrase_regex(_RECOMMEND_AFTER))
_ANTI = (_phrase_regex(_ANTI_BEFORE), _phrase_regex(_ANTI_AFTER))


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
    if is_brand_anti_recommended(context, brand):
        return False
    return _advice_pattern(brand, *_RECOMMEND).search(context) is not None


def is_brand_anti_recommended(context: str, brand: str) -> bool:
    """Check if a brand is being explicitly warned against in the context.

    Complements ``is_brand_recommended`` by detecting negative recommendation
    patterns such as "avoid Nike" or "don't recommend Nike".

    Args:
        context: The text context around the mention.
        brand: The brand name.

    Returns:
        True if the brand appears to be negatively recommended against.
    """
    return _advice_pattern(brand, *_ANTI).search(context) is not None


def count_brand_mentions(response: str, brand: str) -> int:
    """Count the number of times a brand is mentioned.

    Args:
        response: The LLM response text.
        brand: The brand to count.

    Returns:
        Number of mentions.
    """
    return sum(1 for _ in iter_brand_matches(response, brand))


def get_mention_positions(response: str, brand: str) -> list[int]:
    """Get character positions of all brand mentions.

    Args:
        response: The LLM response text.
        brand: The brand to find.

    Returns:
        List of character positions.
    """
    return [match.start() for match in iter_brand_matches(response, brand)]


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
