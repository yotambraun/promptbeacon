"""Tests for extraction module."""

import pytest

from promptbeacon.extraction.mentions import (
    extract_mentions,
    count_brand_mentions,
    calculate_mention_prominence,
    analyze_mention_sentiment,
)
from promptbeacon.extraction.sentiment import (
    analyze_response_sentiment,
    calculate_sentiment_score,
)
from promptbeacon.extraction.ranking import (
    extract_rankings,
    calculate_position_score,
)


class TestMentionExtraction:
    """Tests for mention extraction."""

    def test_extract_single_mention(self):
        response = "I recommend Nike for running shoes."
        result = extract_mentions(response, "Nike")

        assert result.total_mentions == 1
        assert "Nike" in result.brands_found
        assert result.mentions[0].brand_name == "Nike"

    def test_extract_multiple_mentions(self):
        response = "Nike makes great shoes. Nike is also known for sportswear."
        result = extract_mentions(response, "Nike")

        assert result.total_mentions == 2
        assert all(m.brand_name == "Nike" for m in result.mentions)

    def test_extract_with_competitors(self):
        response = "Nike and Adidas are both popular brands."
        result = extract_mentions(response, "Nike", competitors=["Adidas"])

        assert result.total_mentions == 2
        assert "Nike" in result.brands_found
        assert "Adidas" in result.brands_found

    def test_no_mentions(self):
        response = "I like running."
        result = extract_mentions(response, "Nike")

        assert result.total_mentions == 0
        assert len(result.brands_found) == 0

    def test_case_insensitive(self):
        response = "NIKE makes great products. nike is popular."
        result = extract_mentions(response, "Nike")

        assert result.total_mentions == 2


class TestSentimentAnalysis:
    """Tests for sentiment analysis."""

    def test_positive_sentiment(self):
        context = "Nike is an excellent company with great products."
        sentiment = analyze_mention_sentiment(context)

        assert sentiment == "positive"

    def test_negative_sentiment(self):
        context = "This brand has poor quality and many complaints."
        sentiment = analyze_mention_sentiment(context)

        assert sentiment == "negative"

    def test_neutral_sentiment(self):
        context = "This is a brand that exists."
        sentiment = analyze_mention_sentiment(context)

        assert sentiment == "neutral"

    def test_response_sentiment_analysis(self):
        response = "This is an excellent product with great quality."
        result = analyze_response_sentiment(response)

        assert result.overall_sentiment == "positive"
        assert result.breakdown.positive > result.breakdown.negative

    def test_sentiment_score(self):
        from promptbeacon.core.schemas import SentimentBreakdown

        breakdown = SentimentBreakdown(positive=0.7, neutral=0.2, negative=0.1)
        score = calculate_sentiment_score(breakdown)

        assert score == 0.6  # 0.7 - 0.1


class TestRankingExtraction:
    """Tests for ranking extraction."""

    def test_numbered_list_ranking(self):
        response = """
        Top running shoe brands:
        1. Nike
        2. Adidas
        3. New Balance
        """
        result = extract_rankings(response, "Nike", competitors=["Adidas", "New Balance"])

        assert result.has_explicit_ranking is True
        assert result.top_brand == "Nike"
        assert result.brand_positions.get("Nike") == 1
        assert result.brand_positions.get("Adidas") == 2

    def test_no_explicit_ranking(self):
        response = "Nike and Adidas are both good brands."
        result = extract_rankings(response, "Nike", competitors=["Adidas"])

        assert result.has_explicit_ranking is False

    def test_position_score(self):
        assert calculate_position_score(1, 10) == 1.0
        assert calculate_position_score(10, 10) == 0.1
        assert calculate_position_score(None) == 0.0


class TestMentionProminence:
    """Tests for mention prominence calculation."""

    def test_early_mention_prominence(self):
        response = "Nike is great. Other text here..." * 10
        prominence = calculate_mention_prominence(response, "Nike")

        assert prominence > 0.5  # Early mention should have high prominence

    def test_no_mention_prominence(self):
        response = "No brand mentioned here."
        prominence = calculate_mention_prominence(response, "Nike")

        assert prominence == 0.0

    def test_count_mentions(self):
        response = "Nike Nike Nike"
        count = count_brand_mentions(response, "Nike")

        assert count == 3
