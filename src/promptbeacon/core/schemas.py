"""Pydantic models for PromptBeacon data structures."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field


class BrandMention(BaseModel):
    """Represents a single brand mention in an LLM response."""

    brand_name: str = Field(..., description="Name of the mentioned brand")
    sentiment: Literal["positive", "neutral", "negative"] = Field(
        ..., description="Sentiment of the mention"
    )
    position: int = Field(
        ..., ge=0, description="Position in the response (0-indexed, by mention order)"
    )
    context: str = Field(..., description="Surrounding text context of the mention")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score for this extraction"
    )
    is_recommendation: bool = Field(
        default=False, description="Whether the brand was explicitly recommended"
    )


class ProviderResult(BaseModel):
    """Result from a single LLM provider query."""

    provider: str = Field(..., description="Name of the LLM provider")
    model: str = Field(..., description="Model name used")
    prompt: str = Field(..., description="The prompt sent to the LLM")
    response: str = Field(..., description="The LLM's response")
    mentions: list[BrandMention] = Field(
        default_factory=list, description="Brand mentions extracted from response"
    )
    latency_ms: float = Field(..., ge=0, description="Response latency in milliseconds")
    cost_usd: float | None = Field(default=None, ge=0, description="Estimated cost in USD")
    error: str | None = Field(default=None, description="Error message if request failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @computed_field
    @property
    def success(self) -> bool:
        """Whether the request was successful."""
        return self.error is None

    @computed_field
    @property
    def mention_count(self) -> int:
        """Number of brand mentions in this result."""
        return len(self.mentions)


class SentimentBreakdown(BaseModel):
    """Breakdown of sentiment across mentions."""

    positive: float = Field(default=0.0, ge=0.0, le=1.0)
    neutral: float = Field(default=0.0, ge=0.0, le=1.0)
    negative: float = Field(default=0.0, ge=0.0, le=1.0)

    @classmethod
    def from_mentions(cls, mentions: list[BrandMention]) -> SentimentBreakdown:
        """Calculate sentiment breakdown from a list of mentions."""
        if not mentions:
            return cls()

        total = len(mentions)
        positive = sum(1 for m in mentions if m.sentiment == "positive") / total
        neutral = sum(1 for m in mentions if m.sentiment == "neutral") / total
        negative = sum(1 for m in mentions if m.sentiment == "negative") / total

        return cls(positive=positive, neutral=neutral, negative=negative)


class CompetitorScore(BaseModel):
    """Visibility score for a competitor."""

    brand_name: str
    visibility_score: float = Field(ge=0.0, le=100.0)
    mention_count: int = Field(ge=0)
    sentiment: SentimentBreakdown


class VisibilityMetrics(BaseModel):
    """Core visibility metrics for a brand."""

    visibility_score: float = Field(
        ..., ge=0.0, le=100.0, description="Overall visibility score (0-100)"
    )
    mention_count: int = Field(..., ge=0, description="Total number of mentions")
    recommendation_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Rate at which brand is recommended"
    )
    average_position: float | None = Field(
        default=None, ge=0, description="Average position when mentioned"
    )
    sentiment: SentimentBreakdown = Field(default_factory=SentimentBreakdown)
    confidence_interval: tuple[float, float] | None = Field(
        default=None, description="95% confidence interval for visibility score"
    )


class Explanation(BaseModel):
    """An explanation for visibility changes or patterns."""

    category: str = Field(..., description="Category of the explanation")
    message: str = Field(..., description="Human-readable explanation")
    evidence: list[str] = Field(
        default_factory=list, description="Supporting evidence quotes"
    )
    impact: Literal["high", "medium", "low"] = Field(
        default="medium", description="Impact level"
    )


class Recommendation(BaseModel):
    """An actionable recommendation for improving visibility."""

    action: str = Field(..., description="Recommended action to take")
    rationale: str = Field(..., description="Why this action is recommended")
    priority: Literal["high", "medium", "low"] = Field(
        default="medium", description="Priority level"
    )
    expected_impact: str = Field(
        default="", description="Expected impact of taking this action"
    )


class Report(BaseModel):
    """Complete visibility report for a brand scan."""

    brand: str = Field(..., description="The brand being analyzed")
    visibility_score: float = Field(
        ..., ge=0.0, le=100.0, description="Overall visibility score"
    )
    mention_count: int = Field(..., ge=0, description="Total mentions across all queries")
    sentiment_breakdown: SentimentBreakdown = Field(default_factory=SentimentBreakdown)
    competitor_comparison: dict[str, CompetitorScore] = Field(
        default_factory=dict, description="Competitor visibility scores"
    )
    provider_results: list[ProviderResult] = Field(
        default_factory=list, description="Raw results from each provider query"
    )
    metrics: VisibilityMetrics = Field(..., description="Detailed visibility metrics")
    explanations: list[Explanation] = Field(
        default_factory=list, description="Explanations for visibility patterns"
    )
    recommendations: list[Recommendation] = Field(
        default_factory=list, description="Actionable recommendations"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    scan_duration_seconds: float = Field(default=0.0, ge=0)
    total_cost_usd: float | None = Field(default=None, ge=0)

    @computed_field
    @property
    def providers_used(self) -> list[str]:
        """List of providers used in this scan."""
        return list({r.provider for r in self.provider_results})

    @computed_field
    @property
    def success_rate(self) -> float:
        """Rate of successful provider queries."""
        if not self.provider_results:
            return 0.0
        return sum(1 for r in self.provider_results if r.success) / len(self.provider_results)


class HistoricalDataPoint(BaseModel):
    """A single historical data point for trend analysis."""

    timestamp: datetime
    visibility_score: float = Field(ge=0.0, le=100.0)
    mention_count: int = Field(ge=0)
    sentiment: SentimentBreakdown


class HistoryReport(BaseModel):
    """Historical trend data for a brand."""

    brand: str
    data_points: list[HistoricalDataPoint] = Field(default_factory=list)
    trend_direction: Literal["up", "down", "stable"] | None = Field(default=None)
    average_score: float | None = Field(default=None, ge=0.0, le=100.0)
    volatility: float | None = Field(default=None, ge=0.0)

    @computed_field
    @property
    def visibility_trend(self) -> list[float]:
        """List of visibility scores over time."""
        return [dp.visibility_score for dp in self.data_points]


class ScanComparison(BaseModel):
    """Comparison between two scans."""

    brand: str
    current_score: float = Field(ge=0.0, le=100.0)
    previous_score: float = Field(ge=0.0, le=100.0)
    score_change: float
    current_timestamp: datetime
    previous_timestamp: datetime
    changes: list[Explanation] = Field(
        default_factory=list, description="Explanations for changes"
    )

    @computed_field
    @property
    def change_direction(self) -> Literal["up", "down", "stable"]:
        """Direction of score change."""
        if self.score_change > 1.0:
            return "up"
        elif self.score_change < -1.0:
            return "down"
        return "stable"
