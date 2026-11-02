"""Position and ranking extraction from LLM responses."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from promptbeacon.extraction.matching import find_brand, mentions_brand

RankingType = Literal["numbered", "ordered", "recommended", "mentioned"]


class RankingResult(BaseModel):
    """Result of ranking extraction."""

    brand: str
    position: int | None = Field(default=None, ge=1)
    total_ranked: int = Field(default=0, ge=0)
    context: str = ""
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    ranking_type: RankingType = "mentioned"


class RankingAnalysis(BaseModel):
    """Analysis of brand rankings in a response."""

    rankings: list[RankingResult] = Field(default_factory=list)
    has_explicit_ranking: bool = False
    top_brand: str | None = None
    brand_positions: dict[str, int] = Field(default_factory=dict)


# A numbered list item: the number starts the line, after optional indentation
# and Markdown emphasis or a heading marker ("1. X", "  2) X", "**3. X**",
# "### 4. X"), and is followed by whitespace. Numbers inside a sentence
# ("Python 3.12", "2.5 times") are never ranks. The item's title is the text
# before the first colon, so a brand named only in the description is not
# credited with the item's rank.
_NUMBERED_ITEM = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]+)?[*_]{0,2}(\d{1,2})[.)][ \t]+([^:\n]+)", re.MULTILINE
)

# Bulleted items that state an order ("- Best: X", "* **Second:** Y").
_ORDERED_BULLETS = [
    re.compile(
        rf"^[ \t]*[-•*+][ \t]+[*_]{{0,2}}(?:{words})[*_]{{0,2}}[:\s]+([^\n]+)",
        re.IGNORECASE | re.MULTILINE,
    )
    for words in ("first|#1|top|best", "second|#2|runner-up", "third|#3")
]

# A sentence that recommends something; the clause runs to the end of the
# sentence (a period followed by whitespace or the end of the text), so dotted
# names such as "Node.js" stay whole.
_RECOMMENDATIONS: list[tuple[re.Pattern[str], RankingType]] = [
    (
        re.compile(
            rf"(?<!\w)(?:{phrases})[:\s]+(.+?)(?=[.!?](?:\s|$)|\n|$)",
            re.IGNORECASE,
        ),
        "recommended",
    )
    for phrases in (
        "recommend|suggest|top pick|best choice",
        "first choice|my pick|go-to",
    )
]


def extract_rankings(
    response: str,
    target_brand: str,
    competitors: list[str] | None = None,
) -> RankingAnalysis:
    """Extract brand rankings from an LLM response.

    Brands are matched as whole names (see
    :mod:`promptbeacon.extraction.matching`).

    Args:
        response: The LLM response text.
        target_brand: The main brand to track.
        competitors: Optional list of competitor brands.

    Returns:
        RankingAnalysis with extracted rankings.
    """
    all_brands = [target_brand] + (competitors or [])
    rankings: list[RankingResult] = []
    brand_positions: dict[str, int] = {}
    has_explicit_ranking = False

    # Numbered list items (1. Brand, 2. Brand, ...)
    numbered_matches = _NUMBERED_ITEM.findall(response)
    for position_str, text in numbered_matches:
        position = int(position_str)
        for brand in all_brands:
            if mentions_brand(text, brand):
                has_explicit_ranking = True
                if brand not in brand_positions or position < brand_positions[brand]:
                    brand_positions[brand] = position
                    rankings.append(
                        RankingResult(
                            brand=brand,
                            position=position,
                            total_ranked=len(numbered_matches),
                            context=text.strip()[:200],
                            confidence=0.9,
                            ranking_type="numbered",
                        )
                    )

    # Bullet points with order indicators
    for idx, pattern in enumerate(_ORDERED_BULLETS, 1):
        for text in pattern.findall(response):
            for brand in all_brands:
                if mentions_brand(text, brand):
                    has_explicit_ranking = True
                    if brand not in brand_positions:
                        brand_positions[brand] = idx
                        rankings.append(
                            RankingResult(
                                brand=brand,
                                position=idx,
                                context=text.strip()[:200],
                                confidence=0.85,
                                ranking_type="ordered",
                            )
                        )

    # Recommendation sentences
    for rec_pattern, rec_ranking_type in _RECOMMENDATIONS:
        for text in rec_pattern.findall(response):
            for brand in all_brands:
                if brand not in brand_positions and mentions_brand(text, brand):
                    brand_positions[brand] = 1
                    rankings.append(
                        RankingResult(
                            brand=brand,
                            position=1,
                            context=text.strip()[:200],
                            confidence=0.8,
                            ranking_type=rec_ranking_type,
                        )
                    )

    # For brands not found in rankings, record their first mention
    for brand in all_brands:
        if brand not in brand_positions:
            match = find_brand(response, brand)
            if match:
                char_pos = match.start()
                rankings.append(
                    RankingResult(
                        brand=brand,
                        position=None,  # No explicit ranking
                        context=response[
                            max(0, char_pos - 50) : min(len(response), char_pos + 100)
                        ],
                        confidence=0.5,
                        ranking_type="mentioned",
                    )
                )

    # Determine top brand
    top_brand = None
    if brand_positions:
        top_brand = min(brand_positions, key=lambda k: brand_positions[k])

    return RankingAnalysis(
        rankings=rankings,
        has_explicit_ranking=has_explicit_ranking,
        top_brand=top_brand,
        brand_positions=brand_positions,
    )


def calculate_position_score(position: int | None, total: int = 10) -> float:
    """Calculate a score based on ranking position.

    Args:
        position: The ranking position (1 = best).
        total: Total number of items ranked.

    Returns:
        Score from 0.0 to 1.0 (higher is better).
    """
    if position is None:
        return 0.0
    return max(0.0, (total - position + 1) / total)


def get_average_position(rankings: list[RankingResult]) -> float | None:
    """Calculate the average ranking position.

    Args:
        rankings: List of ranking results.

    Returns:
        Average position or None if no positions.
    """
    positions = [r.position for r in rankings if r.position is not None]
    if not positions:
        return None
    return sum(positions) / len(positions)
