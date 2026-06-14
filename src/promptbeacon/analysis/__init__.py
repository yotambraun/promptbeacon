"""Analysis module for PromptBeacon."""

from promptbeacon.analysis.explainer import (
    explain_change,
    generate_explanations,
    generate_recommendations,
)
from promptbeacon.analysis.llm_recommendations import (
    build_recommendations_prompt,
    parse_recommendations,
)
from promptbeacon.analysis.scorer import (
    ScoringWeights,
    calculate_competitor_scores,
    calculate_metrics,
    calculate_share_of_voice,
    calculate_visibility_score,
    compare_to_competitors,
)
from promptbeacon.analysis.stability import aggregate_stability
from promptbeacon.analysis.statistics import (
    SignificanceTest,
    StatisticalSummary,
    VolatilityMetrics,
    calculate_confidence_interval,
    calculate_statistical_summary,
    calculate_trend,
    calculate_volatility,
    check_significance,
)

__all__ = [
    # Scorer
    "ScoringWeights",
    "calculate_competitor_scores",
    "calculate_metrics",
    "calculate_share_of_voice",
    "calculate_visibility_score",
    "compare_to_competitors",
    # Stability
    "aggregate_stability",
    # Statistics
    "SignificanceTest",
    "StatisticalSummary",
    "VolatilityMetrics",
    "calculate_confidence_interval",
    "calculate_statistical_summary",
    "calculate_trend",
    "calculate_volatility",
    "check_significance",
    # Explainer
    "explain_change",
    "generate_explanations",
    "generate_recommendations",
    # LLM recommendations
    "build_recommendations_prompt",
    "parse_recommendations",
]
