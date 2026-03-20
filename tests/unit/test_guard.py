"""Tests for BeaconGuard real-time brand safety analysis."""

import pytest

from promptbeacon.guard import BeaconGuard, GuardResult, is_brand_anti_recommended


@pytest.fixture
def guard():
    return BeaconGuard("Nike", competitors=["Adidas", "Puma"])


class TestBeaconGuardAnalyze:
    def test_brand_positive_no_competitors(self, guard):
        result = guard.analyze(
            "I recommend Nike for running shoes. Great quality and innovation."
        )
        assert result.mentions_brand is True
        assert result.mentions_competitor is False
        assert result.competitor_names == []
        assert result.risk_level == "low"
        assert result.flags == []
        assert result.is_recommendation is True

    def test_competitor_mentioned(self, guard):
        result = guard.analyze(
            "Adidas makes excellent running shoes with great cushioning."
        )
        assert result.mentions_competitor is True
        assert "Adidas" in result.competitor_names
        assert result.risk_level == "medium"
        assert any("Competitor mentioned" in f for f in result.flags)

    def test_negative_sentiment_and_competitor_is_high_risk(self, guard):
        result = guard.analyze(
            "Nike has poor quality and disappointing problems. "
            "Adidas is a much better and more reliable alternative."
        )
        assert result.risk_level == "high"
        assert len(result.flags) >= 2

    def test_anti_recommendation_detected(self, guard):
        result = guard.analyze("I wouldn't recommend Nike for serious runners.")
        assert result.is_anti_recommendation is True
        assert any("anti-recommendation" in f.lower() for f in result.flags)

    def test_no_brand_mention_flag(self):
        guard = BeaconGuard("Nike", flag_no_brand_mention=True)
        result = guard.analyze("Running shoes are great for exercise.")
        assert result.mentions_brand is False
        assert any("Brand not mentioned" in f for f in result.flags)

    def test_empty_text(self, guard):
        result = guard.analyze("")
        assert result.mentions_brand is False
        assert result.mentions_competitor is False
        assert result.risk_level == "low"
        assert result.flags == []

    def test_aliases_credited_to_main_brand(self):
        guard = BeaconGuard("Nike", aliases=["Nike Inc", "Nike Corporation"])
        result = guard.analyze("Nike Inc makes great running shoes.")
        assert result.mentions_brand is True

    def test_guard_result_is_pydantic_model(self, guard):
        result = guard.analyze("Nike is great.")
        assert isinstance(result, GuardResult)
        data = result.model_dump()
        assert "risk_level" in data
        assert "flags" in data

    def test_sentiment_details_populated(self, guard):
        result = guard.analyze("Nike is excellent and innovative.")
        assert result.sentiment_details is not None
        assert result.sentiment_details.overall_sentiment in (
            "positive",
            "neutral",
            "negative",
        )

    def test_multiple_competitors(self, guard):
        result = guard.analyze("Adidas and Puma both make great shoes.")
        assert "Adidas" in result.competitor_names
        assert "Puma" in result.competitor_names


class TestIsBrandAntiRecommended:
    def test_avoid_pattern(self):
        assert is_brand_anti_recommended("You should avoid Nike.", "Nike") is True

    def test_wouldnt_recommend(self):
        assert (
            is_brand_anti_recommended("I wouldn't recommend Nike.", "Nike") is True
        )

    def test_positive_recommendation_not_anti(self):
        assert (
            is_brand_anti_recommended("I recommend Nike for running.", "Nike") is False
        )

    def test_case_insensitive(self):
        assert is_brand_anti_recommended("AVOID NIKE", "Nike") is True
