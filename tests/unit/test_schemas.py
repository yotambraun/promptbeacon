"""Tests for core schemas."""

import pytest
from datetime import datetime

from promptbeacon.core.schemas import (
    BrandMention,
    ProviderResult,
    Report,
    SentimentBreakdown,
    VisibilityMetrics,
)


class TestBrandMention:
    """Tests for BrandMention model."""

    def test_create_brand_mention(self):
        mention = BrandMention(
            brand_name="Acme Corp",
            sentiment="positive",
            position=0,
            context="Acme Corp is a great company.",
            confidence=0.95,
            is_recommendation=True,
        )

        assert mention.brand_name == "Acme Corp"
        assert mention.sentiment == "positive"
        assert mention.position == 0
        assert mention.confidence == 0.95
        assert mention.is_recommendation is True

    def test_default_values(self):
        mention = BrandMention(
            brand_name="Test",
            sentiment="neutral",
            position=1,
            context="Test context",
        )

        assert mention.confidence == 1.0
        assert mention.is_recommendation is False

    def test_confidence_validation(self):
        with pytest.raises(ValueError):
            BrandMention(
                brand_name="Test",
                sentiment="positive",
                position=0,
                context="context",
                confidence=1.5,  # Invalid: > 1.0
            )


class TestSentimentBreakdown:
    """Tests for SentimentBreakdown model."""

    def test_from_mentions_positive(self):
        mentions = [
            BrandMention(
                brand_name="Test",
                sentiment="positive",
                position=0,
                context="good",
            ),
            BrandMention(
                brand_name="Test",
                sentiment="positive",
                position=1,
                context="great",
            ),
            BrandMention(
                brand_name="Test",
                sentiment="neutral",
                position=2,
                context="okay",
            ),
        ]

        breakdown = SentimentBreakdown.from_mentions(mentions)

        assert breakdown.positive == pytest.approx(2 / 3, rel=0.01)
        assert breakdown.neutral == pytest.approx(1 / 3, rel=0.01)
        assert breakdown.negative == 0.0

    def test_from_empty_mentions(self):
        breakdown = SentimentBreakdown.from_mentions([])

        assert breakdown.positive == 0.0
        assert breakdown.neutral == 0.0
        assert breakdown.negative == 0.0


class TestProviderResult:
    """Tests for ProviderResult model."""

    def test_success_computed_property(self):
        result = ProviderResult(
            provider="openai",
            model="gpt-4",
            prompt="test prompt",
            response="test response",
            latency_ms=100.0,
        )

        assert result.success is True

    def test_failed_result(self):
        result = ProviderResult(
            provider="openai",
            model="gpt-4",
            prompt="test prompt",
            response="",
            latency_ms=0.0,
            error="API Error",
        )

        assert result.success is False

    def test_mention_count(self):
        result = ProviderResult(
            provider="openai",
            model="gpt-4",
            prompt="test",
            response="test",
            mentions=[
                BrandMention(
                    brand_name="Test",
                    sentiment="positive",
                    position=0,
                    context="context",
                ),
            ],
            latency_ms=100.0,
        )

        assert result.mention_count == 1


class TestReport:
    """Tests for Report model."""

    def test_providers_used_computed(self):
        results = [
            ProviderResult(
                provider="openai",
                model="gpt-4",
                prompt="test",
                response="test",
                latency_ms=100.0,
            ),
            ProviderResult(
                provider="anthropic",
                model="claude-3",
                prompt="test",
                response="test",
                latency_ms=100.0,
            ),
        ]

        report = Report(
            brand="Test",
            visibility_score=75.0,
            mention_count=5,
            provider_results=results,
            metrics=VisibilityMetrics(
                visibility_score=75.0,
                mention_count=5,
            ),
        )

        assert "openai" in report.providers_used
        assert "anthropic" in report.providers_used

    def test_success_rate(self):
        results = [
            ProviderResult(
                provider="openai",
                model="gpt-4",
                prompt="test",
                response="test",
                latency_ms=100.0,
            ),
            ProviderResult(
                provider="openai",
                model="gpt-4",
                prompt="test",
                response="",
                latency_ms=0.0,
                error="Failed",
            ),
        ]

        report = Report(
            brand="Test",
            visibility_score=50.0,
            mention_count=1,
            provider_results=results,
            metrics=VisibilityMetrics(
                visibility_score=50.0,
                mention_count=1,
            ),
        )

        assert report.success_rate == 0.5
