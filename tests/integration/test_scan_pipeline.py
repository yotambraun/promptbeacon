"""Integration tests for the full scan pipeline.

These tests mock `LiteLLMClient.complete` with realistic pre-canned
responses so the entire pipeline — extraction, scoring, explanations,
recommendations, and report building — is exercised end-to-end without
requiring actual API keys.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from promptbeacon.beacon import Beacon
from promptbeacon.core.config import Provider
from promptbeacon.providers.base import LLMResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(content: str, provider: str = "openai") -> LLMResponse:
    return LLMResponse(
        content=content,
        model="mock-model",
        provider=provider,
        latency_ms=100.0,
        cost_usd=0.001,
    )


POSITIVE_RESPONSE = (
    "I would highly recommend Nike for running shoes. Nike is a top-rated, "
    "excellent brand known for innovative and reliable products. "
    "According to Runner's World, Nike leads in performance. "
    "See https://www.runnersworld.com/nike-review for details."
)

NEGATIVE_RESPONSE = (
    "Nike has faced complaints about overpriced products and poor customer "
    "service. Many users report issues and disappointing quality. "
    "I would recommend against Nike for budget-conscious buyers."
)

NO_MENTION_RESPONSE = (
    "There are many great running shoe options available today. "
    "Brands like Asics and Brooks are well-regarded."
)

COMPETITOR_RESPONSE = (
    "Adidas is the best choice for athletic wear. I recommend Adidas for "
    "their excellent quality and innovative designs. Nike is also decent "
    "but Adidas leads the market."
)

PARTIAL_FAILURE_RESPONSE = Exception("API timeout")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def _mock_available_providers():
    """Make all providers appear available during tests."""
    with patch(
        "promptbeacon.beacon.get_available_providers",
        return_value=[Provider.OPENAI],
    ):
        yield


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestScanPipeline:
    """End-to-end pipeline tests with mock LLM responses."""

    @pytest.mark.usefixtures("_mock_available_providers")
    def test_basic_scan_produces_valid_report(self):
        mock_complete = AsyncMock(return_value=_make_response(POSITIVE_RESPONSE))
        with patch("promptbeacon.beacon.LiteLLMClient.complete", mock_complete):
            beacon = Beacon("Nike").with_categories("running shoes")
            report = beacon.scan()

        assert report.brand == "Nike"
        assert report.visibility_score > 0
        assert report.mention_count > 0
        assert report.scan_duration_seconds >= 0

    @pytest.mark.usefixtures("_mock_available_providers")
    def test_negative_scan_detected(self):
        mock_complete = AsyncMock(return_value=_make_response(NEGATIVE_RESPONSE))
        with patch("promptbeacon.beacon.LiteLLMClient.complete", mock_complete):
            beacon = Beacon("Nike").with_categories("shoes")
            report = beacon.scan()

        assert report.mention_count > 0
        # Negative sentiment should be present
        assert report.sentiment_breakdown.negative > 0
        # Anti-recommendation should be detected
        nike_mentions = [
            m
            for r in report.provider_results
            for m in r.mentions
            if m.brand_name.lower() == "nike"
        ]
        assert any(m.is_recommendation is False for m in nike_mentions)

    @pytest.mark.usefixtures("_mock_available_providers")
    def test_competitor_comparison(self):
        mock_complete = AsyncMock(return_value=_make_response(COMPETITOR_RESPONSE))
        with patch("promptbeacon.beacon.LiteLLMClient.complete", mock_complete):
            beacon = (
                Beacon("Nike")
                .with_competitors("Adidas")
                .with_categories("athletic wear")
            )
            report = beacon.scan()

        assert "Adidas" in report.competitor_comparison
        assert report.competitor_comparison["Adidas"].visibility_score >= 0

    @pytest.mark.usefixtures("_mock_available_providers")
    def test_no_mention_produces_zero_score(self):
        mock_complete = AsyncMock(return_value=_make_response(NO_MENTION_RESPONSE))
        with patch("promptbeacon.beacon.LiteLLMClient.complete", mock_complete):
            beacon = Beacon("Nike").with_categories("shoes")
            report = beacon.scan()

        assert report.visibility_score == 0.0
        assert report.mention_count == 0

    @pytest.mark.usefixtures("_mock_available_providers")
    def test_partial_failures_still_produce_report(self):
        """When some queries fail, the pipeline should still return a report
        using the successful results."""
        call_count = 0

        async def mock_complete(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                raise Exception("API timeout")
            return _make_response(POSITIVE_RESPONSE)

        with patch(
            "promptbeacon.beacon.LiteLLMClient.complete",
            side_effect=mock_complete,
        ):
            beacon = Beacon("Nike").with_categories("shoes").with_prompt_count(4)
            report = beacon.scan()

        # Should still produce a valid report with partial results
        assert report.brand == "Nike"
        assert report.visibility_score >= 0

    @pytest.mark.usefixtures("_mock_available_providers")
    def test_citations_extracted_in_pipeline(self):
        mock_complete = AsyncMock(return_value=_make_response(POSITIVE_RESPONSE))
        with patch("promptbeacon.beacon.LiteLLMClient.complete", mock_complete):
            beacon = Beacon("Nike").with_categories("shoes")
            report = beacon.scan()

        # The positive response contains a URL and an "According to" pattern
        assert report.citation_summary.total_citations > 0
        assert any(
            c.url and "runnersworld.com" in c.url
            for c in report.citation_summary.citations
        )

    @pytest.mark.usefixtures("_mock_available_providers")
    def test_custom_scoring_weights(self):
        mock_complete = AsyncMock(return_value=_make_response(POSITIVE_RESPONSE))
        with patch("promptbeacon.beacon.LiteLLMClient.complete", mock_complete):
            # High weight on recommendations
            beacon = (
                Beacon("Nike")
                .with_categories("shoes")
                .with_scoring_weights(
                    mention_frequency=0.1,
                    sentiment=0.1,
                    position=0.1,
                    recommendation=0.7,
                )
            )
            report = beacon.scan()

        assert report.brand == "Nike"
        assert report.visibility_score >= 0
