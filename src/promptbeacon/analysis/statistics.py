"""Statistical analysis for visibility metrics."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field


class StatisticalSummary(BaseModel):
    """Statistical summary of visibility data."""

    mean: float
    median: float
    std_dev: float
    min_value: float
    max_value: float
    count: int
    confidence_interval_95: tuple[float, float]


class VolatilityMetrics(BaseModel):
    """Metrics for score volatility."""

    volatility_score: float = Field(ge=0.0, description="Standard deviation of changes")
    max_swing: float = Field(ge=0.0, description="Maximum single-period change")
    average_change: float = Field(description="Average period-to-period change")
    stability_rating: Literal["stable", "moderate", "volatile"]


class SignificanceTest(BaseModel):
    """Result of a significance test."""

    is_significant: bool
    p_value: float | None = None
    effect_size: float | None = None
    confidence_level: float = 0.95
    interpretation: str = ""


def calculate_confidence_interval(
    scores: list[float],
    confidence_level: float = 0.95,
) -> tuple[float, float]:
    """Calculate confidence interval for visibility scores.

    Args:
        scores: List of visibility scores.
        confidence_level: Confidence level (default 95%).

    Returns:
        Tuple of (lower_bound, upper_bound).
    """
    if not scores:
        return (0.0, 0.0)

    n = len(scores)
    if n == 1:
        return (scores[0], scores[0])

    mean = sum(scores) / n
    variance = sum((x - mean) ** 2 for x in scores) / (n - 1)
    std_dev = math.sqrt(variance)

    # Z-scores for common confidence levels
    z_scores = {
        0.90: 1.645,
        0.95: 1.96,
        0.99: 2.576,
    }
    z = z_scores.get(confidence_level, 1.96)

    margin = z * (std_dev / math.sqrt(n))
    lower = max(0, mean - margin)
    upper = min(100, mean + margin)

    return (round(lower, 2), round(upper, 2))


def calculate_statistical_summary(scores: list[float]) -> StatisticalSummary:
    """Calculate comprehensive statistical summary.

    Args:
        scores: List of visibility scores.

    Returns:
        StatisticalSummary with all metrics.
    """
    if not scores:
        return StatisticalSummary(
            mean=0.0,
            median=0.0,
            std_dev=0.0,
            min_value=0.0,
            max_value=0.0,
            count=0,
            confidence_interval_95=(0.0, 0.0),
        )

    n = len(scores)
    mean = sum(scores) / n

    sorted_scores = sorted(scores)
    if n % 2 == 0:
        median = (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2
    else:
        median = sorted_scores[n // 2]

    variance = sum((x - mean) ** 2 for x in scores) / max(n - 1, 1)
    std_dev = math.sqrt(variance)

    confidence_interval = calculate_confidence_interval(scores)

    return StatisticalSummary(
        mean=round(mean, 2),
        median=round(median, 2),
        std_dev=round(std_dev, 2),
        min_value=round(min(scores), 2),
        max_value=round(max(scores), 2),
        count=n,
        confidence_interval_95=confidence_interval,
    )


def calculate_volatility(
    scores: list[float],
) -> VolatilityMetrics:
    """Calculate volatility metrics from historical scores.

    Args:
        scores: List of visibility scores in chronological order.

    Returns:
        VolatilityMetrics with volatility analysis.
    """
    if len(scores) < 2:
        return VolatilityMetrics(
            volatility_score=0.0,
            max_swing=0.0,
            average_change=0.0,
            stability_rating="stable",
        )

    # Calculate period-to-period changes
    changes = [scores[i] - scores[i - 1] for i in range(1, len(scores))]

    abs_changes = [abs(c) for c in changes]
    average_change = sum(abs_changes) / len(abs_changes)
    max_swing = max(abs_changes)

    # Volatility is standard deviation of changes
    mean_change = sum(changes) / len(changes)
    variance = sum((c - mean_change) ** 2 for c in changes) / max(len(changes) - 1, 1)
    volatility_score = math.sqrt(variance)

    # Determine stability rating
    if volatility_score < 3:
        stability_rating = "stable"
    elif volatility_score < 8:
        stability_rating = "moderate"
    else:
        stability_rating = "volatile"

    return VolatilityMetrics(
        volatility_score=round(volatility_score, 2),
        max_swing=round(max_swing, 2),
        average_change=round(average_change, 2),
        stability_rating=stability_rating,
    )


def check_significance(
    before_scores: list[float],
    after_scores: list[float],
    threshold: float = 0.05,
) -> SignificanceTest:
    """Check if the change between two periods is statistically significant.

    Uses a simple difference of means test.

    Args:
        before_scores: Scores from the earlier period.
        after_scores: Scores from the later period.
        threshold: Significance threshold (default 0.05).

    Returns:
        SignificanceTest with results.
    """
    if not before_scores or not after_scores:
        return SignificanceTest(
            is_significant=False,
            interpretation="Insufficient data for significance test",
        )

    mean_before = sum(before_scores) / len(before_scores)
    mean_after = sum(after_scores) / len(after_scores)
    difference = mean_after - mean_before

    # Calculate pooled standard deviation
    n1, n2 = len(before_scores), len(after_scores)

    if n1 < 2 or n2 < 2:
        # Not enough data for proper test
        is_significant = abs(difference) > 5  # Simple threshold
        return SignificanceTest(
            is_significant=is_significant,
            effect_size=round(difference, 2),
            interpretation=f"Change of {difference:.1f} points (limited data)",
        )

    var1 = sum((x - mean_before) ** 2 for x in before_scores) / (n1 - 1)
    var2 = sum((x - mean_after) ** 2 for x in after_scores) / (n2 - 1)

    pooled_var = ((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2)
    pooled_std = math.sqrt(pooled_var)

    if pooled_std == 0:
        return SignificanceTest(
            is_significant=abs(difference) > 0,
            effect_size=round(difference, 2),
            interpretation="No variance in scores",
        )

    # Calculate effect size (Cohen's d)
    effect_size = difference / pooled_std

    # Simple significance heuristic based on effect size
    # Cohen's d: 0.2 = small, 0.5 = medium, 0.8 = large
    is_significant = abs(effect_size) >= 0.5

    if abs(effect_size) < 0.2:
        interpretation = f"Negligible change ({difference:+.1f} points)"
    elif abs(effect_size) < 0.5:
        interpretation = f"Small change ({difference:+.1f} points)"
    elif abs(effect_size) < 0.8:
        interpretation = f"Moderate change ({difference:+.1f} points)"
    else:
        interpretation = f"Large change ({difference:+.1f} points)"

    return SignificanceTest(
        is_significant=is_significant,
        effect_size=round(effect_size, 3),
        confidence_level=0.95,
        interpretation=interpretation,
    )


def calculate_trend(
    scores: list[float],
) -> Literal["up", "down", "stable"]:
    """Calculate trend direction from historical scores.

    Args:
        scores: List of scores in chronological order.

    Returns:
        Trend direction.
    """
    if len(scores) < 3:
        return "stable"

    # Compare recent vs older averages
    midpoint = len(scores) // 2
    older_avg = sum(scores[:midpoint]) / midpoint
    recent_avg = sum(scores[midpoint:]) / (len(scores) - midpoint)

    difference = recent_avg - older_avg

    if difference > 2:
        return "up"
    elif difference < -2:
        return "down"
    return "stable"
