"""Extraction module for PromptBeacon."""

from promptbeacon.extraction.mentions import (
    MentionExtractionResult,
    calculate_mention_prominence,
    count_brand_mentions,
    extract_mentions,
    get_mention_positions,
)
from promptbeacon.extraction.ranking import (
    RankingAnalysis,
    RankingResult,
    calculate_position_score,
    extract_rankings,
    get_average_position,
)
from promptbeacon.extraction.sentiment import (
    SentimentAnalysisResult,
    aggregate_mention_sentiment,
    analyze_response_sentiment,
    calculate_sentiment_score,
    compare_sentiment,
)

__all__ = [
    # Mentions
    "MentionExtractionResult",
    "calculate_mention_prominence",
    "count_brand_mentions",
    "extract_mentions",
    "get_mention_positions",
    # Ranking
    "RankingAnalysis",
    "RankingResult",
    "calculate_position_score",
    "extract_rankings",
    "get_average_position",
    # Sentiment
    "SentimentAnalysisResult",
    "aggregate_mention_sentiment",
    "analyze_response_sentiment",
    "calculate_sentiment_score",
    "compare_sentiment",
]
