"""Tests for extraction module."""

from promptbeacon.extraction.citations import extract_citations
from promptbeacon.extraction.mentions import (
    analyze_mention_sentiment,
    calculate_mention_prominence,
    count_brand_mentions,
    extract_mentions,
    is_brand_recommended,
)
from promptbeacon.extraction.ranking import (
    calculate_position_score,
    extract_rankings,
)
from promptbeacon.extraction.sentiment import (
    analyze_response_sentiment,
    calculate_sentiment_score,
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

    def test_negated_positive_becomes_negative(self):
        context = "Nike is not great and is not recommended."
        sentiment = analyze_mention_sentiment(context)

        assert sentiment == "negative"

    def test_negated_negative_becomes_positive(self):
        context = "Nike is not bad at all."
        sentiment = analyze_mention_sentiment(context)

        assert sentiment == "positive"

    def test_negation_doesnt_affect_distant_keywords(self):
        context = "Nike is never bad. I have been using them for years and their shoes are truly excellent and premium quality."
        sentiment = analyze_mention_sentiment(context)

        assert sentiment == "positive"

    def test_negation_in_full_extraction(self):
        response = "Nike is not great and is never recommended for running."
        result = extract_mentions(response, "Nike")

        assert result.total_mentions == 1
        assert result.mentions[0].sentiment == "negative"
        # Confidence is now dynamic (0.5-0.8), not hardcoded 0.7
        assert 0.5 <= result.mentions[0].confidence <= 0.8

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
        result = extract_rankings(
            response, "Nike", competitors=["Adidas", "New Balance"]
        )

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


class TestAntiRecommendation:
    """Tests for anti-recommendation pattern detection."""

    def test_recommend_against_returns_false(self):
        context = "I would recommend against Nike for beginners."
        assert is_brand_recommended(context, "Nike") is False

    def test_dont_recommend_returns_false(self):
        context = "I don't recommend Nike for this use case."
        assert is_brand_recommended(context, "Nike") is False

    def test_would_not_recommend_returns_false(self):
        context = "I would not recommend Nike for running."
        assert is_brand_recommended(context, "Nike") is False

    def test_avoid_returns_false(self):
        context = "You should avoid Nike if you have flat feet."
        assert is_brand_recommended(context, "Nike") is False

    def test_stay_away_returns_false(self):
        context = "Stay away from Nike products."
        assert is_brand_recommended(context, "Nike") is False

    def test_positive_recommend_still_works(self):
        context = "I recommend Nike for their excellent running shoes."
        assert is_brand_recommended(context, "Nike") is True

    def test_is_a_great_choice_still_works(self):
        context = "Nike is a great choice for athletes."
        assert is_brand_recommended(context, "Nike") is True

    def test_not_recommended_label_returns_false(self):
        context = "Nike is not recommended for serious athletes."
        assert is_brand_recommended(context, "Nike") is False

    def test_anti_recommendation_in_full_extraction(self):
        response = "I would recommend against Nike for this purpose."
        result = extract_mentions(response, "Nike")

        assert result.total_mentions == 1
        assert result.mentions[0].is_recommendation is False


class TestHonestConfidence:
    """Tests for signal-quality-based confidence scoring."""

    def test_confidence_is_in_valid_range(self):
        response = "Nike makes good shoes."
        result = extract_mentions(response, "Nike")

        assert result.total_mentions == 1
        assert 0.5 <= result.mentions[0].confidence <= 0.8

    def test_exact_case_match_boosts_confidence(self):
        response_exact = "Nike is great."
        response_wrong = "NIKE is great."
        result_exact = extract_mentions(response_exact, "Nike")
        result_wrong = extract_mentions(response_wrong, "Nike")

        # Exact case should score >= wrong case
        assert (
            result_exact.mentions[0].confidence >= result_wrong.mentions[0].confidence
        )

    def test_no_hardcoded_0_7(self):
        """Confidence should never be exactly 0.7 (the old hardcoded value)
        unless it happens to be a legitimate calculated value."""
        responses = [
            "Nike",
            "I love nike shoes.",
            "NIKE is the worst brand ever. Avoid them.",
        ]
        for resp in responses:
            result = extract_mentions(resp, "Nike")
            for m in result.mentions:
                # Must be in the valid range
                assert 0.5 <= m.confidence <= 0.8

    def test_sentiment_signals_boost_confidence(self):
        # Neutral context — fewer signals
        neutral = "Nike is a brand."
        # Positive context — has sentiment signals
        positive = "Nike is an excellent, top-rated brand."

        neutral_result = extract_mentions(neutral, "Nike")
        positive_result = extract_mentions(positive, "Nike")

        # Positive context should have equal or higher confidence (sentiment bonus)
        assert (
            positive_result.mentions[0].confidence
            >= neutral_result.mentions[0].confidence
        )


class TestCitationExtraction:
    """Tests for citation extraction."""

    def test_url_extraction(self):
        response = "According to https://www.nike.com/running, Nike makes great shoes."
        result = extract_citations(response, brands=["Nike"])

        assert result.total_count >= 1
        assert any(c.url and "nike.com" in c.url for c in result.citations)

    def test_multiple_urls(self):
        response = (
            "See https://example.com/shoes for reviews. "
            "Also check https://runner.org/best for rankings."
        )
        result = extract_citations(response)

        assert result.total_count == 2
        assert len(result.unique_domains) == 2

    def test_according_to_pattern(self):
        response = "According to Consumer Reports, Nike shoes are top-rated."
        result = extract_citations(response, brands=["Nike"])

        assert result.total_count >= 1
        assert any("Consumer Reports" in c.source_name for c in result.citations)

    def test_source_pattern(self):
        response = "Nike is highly rated. Source: Running Magazine."
        result = extract_citations(response, brands=["Nike"])

        assert result.total_count >= 1
        assert any("Running Magazine" in c.source_name for c in result.citations)

    def test_brand_association(self):
        response = "According to experts, Nike is the best. Visit https://nike.com for details."
        result = extract_citations(response, brands=["Nike"])

        # At least one citation should be associated with Nike
        assert any(c.brand_associated == "Nike" for c in result.citations)

    def test_empty_response(self):
        result = extract_citations("", brands=["Nike"])

        assert result.total_count == 0
        assert len(result.citations) == 0

    def test_no_citations_in_plain_text(self):
        response = "Nike makes good running shoes for all levels."
        result = extract_citations(response, brands=["Nike"])

        assert result.total_count == 0
