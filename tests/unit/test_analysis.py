"""Tests for analysis module."""

import pytest

from promptbeacon.analysis.scorer import (
    calculate_visibility_score,
    calculate_metrics,
    ScoringWeights,
)
from promptbeacon.analysis.statistics import (
    calculate_confidence_interval,
    calculate_statistical_summary,
    calculate_volatility,
    calculate_trend,
    check_significance,
)
from promptbeacon.analysis.explainer import (
    generate_explanations,
    generate_recommendations,
)
from promptbeacon.core.schemas import (
    BrandMention,
    ProviderResult,
    SentimentBreakdown,
)


class TestVisibilityScoring:
    """Tests for visibility scoring."""

    def test_high_visibility_score(self):
        results = [
            ProviderResult(
                provider="openai",
                model="gpt-4",
                prompt="recommend shoes",
                response="I recommend Nike for the best shoes.",
                mentions=[
                    BrandMention(
                        brand_name="Nike",
                        sentiment="positive",
                        position=0,
                        context="I recommend Nike for the best shoes.",
                        is_recommendation=True,
                    )
                ],
                latency_ms=100.0,
            )
            for _ in range(10)
        ]

        score = calculate_visibility_score(results, "Nike")

        assert score > 50  # Should have decent visibility

    def test_zero_visibility_score(self):
        results = [
            ProviderResult(
                provider="openai",
                model="gpt-4",
                prompt="test",
                response="No brands mentioned.",
                mentions=[],
                latency_ms=100.0,
            )
        ]

        score = calculate_visibility_score(results, "Nike")

        assert score == 0.0

    def test_empty_results(self):
        score = calculate_visibility_score([], "Nike")

        assert score == 0.0

    def test_calculate_metrics(self):
        results = [
            ProviderResult(
                provider="openai",
                model="gpt-4",
                prompt="test",
                response="Nike is great.",
                mentions=[
                    BrandMention(
                        brand_name="Nike",
                        sentiment="positive",
                        position=0,
                        context="Nike is great.",
                    )
                ],
                latency_ms=100.0,
            )
        ]

        metrics = calculate_metrics(results, "Nike")

        assert metrics.mention_count == 1
        assert metrics.visibility_score >= 0


class TestStatistics:
    """Tests for statistical analysis."""

    def test_confidence_interval(self):
        scores = [70, 72, 68, 75, 71]
        lower, upper = calculate_confidence_interval(scores)

        assert lower < 71  # Below mean
        assert upper > 71  # Above mean
        assert lower >= 0
        assert upper <= 100

    def test_confidence_interval_single_value(self):
        lower, upper = calculate_confidence_interval([75.0])

        assert lower == 75.0
        assert upper == 75.0

    def test_confidence_interval_empty(self):
        lower, upper = calculate_confidence_interval([])

        assert lower == 0.0
        assert upper == 0.0

    def test_statistical_summary(self):
        scores = [60, 70, 80, 90, 100]
        summary = calculate_statistical_summary(scores)

        assert summary.mean == 80.0
        assert summary.median == 80.0
        assert summary.min_value == 60.0
        assert summary.max_value == 100.0
        assert summary.count == 5

    def test_volatility_stable(self):
        scores = [70, 71, 70, 71, 70]
        volatility = calculate_volatility(scores)

        assert volatility.stability_rating == "stable"
        assert volatility.volatility_score < 3

    def test_volatility_high(self):
        scores = [50, 80, 40, 90, 30]
        volatility = calculate_volatility(scores)

        assert volatility.stability_rating in ["moderate", "volatile"]

    def test_trend_up(self):
        scores = [50, 55, 60, 65, 70, 75]
        trend = calculate_trend(scores)

        assert trend == "up"

    def test_trend_down(self):
        scores = [80, 75, 70, 65, 60, 55]
        trend = calculate_trend(scores)

        assert trend == "down"

    def test_trend_stable(self):
        scores = [70, 71, 70, 69, 70, 71]
        trend = calculate_trend(scores)

        assert trend == "stable"

    def test_significance_test(self):
        before = [60, 62, 58, 61, 59]
        after = [80, 82, 78, 81, 79]

        result = check_significance(before, after)

        assert result.is_significant is True
        assert result.effect_size is not None


class TestExplainer:
    """Tests for explanation generation."""

    def test_generate_explanations_high_visibility(self):
        results = [
            ProviderResult(
                provider="openai",
                model="gpt-4",
                prompt="test",
                response="Nike is the best brand.",
                mentions=[
                    BrandMention(
                        brand_name="Nike",
                        sentiment="positive",
                        position=0,
                        context="Nike is the best brand.",
                    )
                ],
                latency_ms=100.0,
            )
        ]

        explanations = generate_explanations(results, "Nike", 75.0)

        assert len(explanations) > 0
        assert any("visibility" in e.category for e in explanations)

    def test_generate_recommendations_low_visibility(self):
        results = [
            ProviderResult(
                provider="openai",
                model="gpt-4",
                prompt="test",
                response="No brands.",
                mentions=[],
                latency_ms=100.0,
            )
        ]

        sentiment = SentimentBreakdown(positive=0.0, neutral=1.0, negative=0.0)
        recommendations = generate_recommendations(results, "Nike", 20.0, sentiment)

        assert len(recommendations) > 0
        # Low visibility should generate high priority recommendations
        assert any(r.priority == "high" for r in recommendations)
