"""Position and ranking extraction from LLM responses."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field


class RankingResult(BaseModel):
    """Result of ranking extraction."""

    brand: str
    position: int | None = Field(default=None, ge=1)
    total_ranked: int = Field(default=0, ge=0)
    context: str = ""
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    ranking_type: Literal["numbered", "ordered", "recommended", "mentioned"] = "mentioned"


class RankingAnalysis(BaseModel):
    """Analysis of brand rankings in a response."""

    rankings: list[RankingResult] = Field(default_factory=list)
    has_explicit_ranking: bool = False
    top_brand: str | None = None
    brand_positions: dict[str, int] = Field(default_factory=dict)


def extract_rankings(
    response: str,
    target_brand: str,
    competitors: list[str] | None = None,
) -> RankingAnalysis:
    """Extract brand rankings from an LLM response.

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

    # Look for numbered lists (1. Brand, 2. Brand, etc.)
    numbered_pattern = r"(\d+)[.\)]\s*([^:\n]+)"
    numbered_matches = re.findall(numbered_pattern, response)

    if numbered_matches:
        for position_str, text in numbered_matches:
            position = int(position_str)
            for brand in all_brands:
                if brand.lower() in text.lower():
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

    # Look for bullet points with order indicators
    bullet_patterns = [
        r"[-•*]\s*(first|#1|top|best)[:\s]+([^\n]+)",
        r"[-•*]\s*(second|#2|runner-up)[:\s]+([^\n]+)",
        r"[-•*]\s*(third|#3)[:\s]+([^\n]+)",
    ]

    for idx, pattern in enumerate(bullet_patterns, 1):
        matches = re.findall(pattern, response, re.IGNORECASE)
        for _, text in matches:
            for brand in all_brands:
                if brand.lower() in text.lower():
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

    # Look for recommendation patterns
    rec_patterns = [
        (r"(recommend|suggest|top pick|best choice)[:\s]+([^\n.]+)", "recommended"),
        (r"(first choice|my pick|go-to)[:\s]+([^\n.]+)", "recommended"),
    ]

    for pattern, ranking_type in rec_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        for _, text in matches:
            for brand in all_brands:
                if brand.lower() in text.lower():
                    if brand not in brand_positions:
                        brand_positions[brand] = 1
                        rankings.append(
                            RankingResult(
                                brand=brand,
                                position=1,
                                context=text.strip()[:200],
                                confidence=0.8,
                                ranking_type=ranking_type,
                            )
                        )

    # For brands not found in rankings, record their first mention position
    for brand in all_brands:
        if brand not in brand_positions:
            pattern = re.compile(re.escape(brand), re.IGNORECASE)
            match = pattern.search(response)
            if match:
                # Calculate relative position based on character position
                char_pos = match.start()
                relative_pos = int((char_pos / max(len(response), 1)) * 10) + 1
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
        top_brand = min(brand_positions, key=brand_positions.get)

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
