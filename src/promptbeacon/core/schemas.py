"""Pydantic models for PromptBeacon data structures."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field

from promptbeacon.core.exceptions import VisibilityAssertionError


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


class Citation(BaseModel):
    """A single citation found in an LLM response."""

    url: str | None = Field(default=None, description="URL if one was cited")
    source_name: str = Field(..., description="Name of the cited source")
    context: str = Field(
        default="", description="Surrounding text where the citation appeared"
    )
    brand_associated: str | None = Field(
        default=None,
        description="Brand name nearest to this citation, if any",
    )
    source_rank: int | None = Field(
        default=None,
        description="Rank of this source among the engine's retrieved results "
        "(grounded mode only; None when unknown)",
    )
    source_type: str | None = Field(
        default=None,
        description="Classified source type (web, news, reddit, wikipedia, "
        "academic, review, social, code, video, attribution)",
    )
    query: str | None = Field(
        default=None,
        description="The prompt or sub-query that surfaced this citation",
    )
    retrieved_but_uncited: bool = Field(
        default=False,
        description="True if the engine retrieved this source but did not cite it "
        "in the final answer (grounded/funnel mode only)",
    )


class CitationSummary(BaseModel):
    """Aggregated citation summary for a report."""

    total_citations: int = Field(default=0, ge=0)
    unique_domains: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class SourceAttributionEntry(BaseModel):
    """How much a single source domain contributes to AI-search visibility."""

    domain: str = Field(..., description="Source domain or attribution name")
    source_type: str = Field(
        default="web", description="Classified source type (see Citation.source_type)"
    )
    citations: int = Field(default=0, ge=0, description="Citations from this source")
    share: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="citations / total citations across all sources",
    )
    brands_cited: list[str] = Field(
        default_factory=list,
        description="Distinct brands associated with citations from this source",
    )
    cites_target: bool = Field(
        default=False,
        description="True if the target brand was associated with this source",
    )


class SourceAttributionReport(BaseModel):
    """Which source domains drive (or are missing from) AI-search visibility.

    Web-grounded AI answers cite their sources; this aggregates those citations
    by domain so you can see which sites the engines trust for your category —
    the actionable GEO lever ("get cited on these sites"). Surfaces the
    Reddit/Wikipedia/news concentration that decides most brand visibility.
    """

    target_brand: str = Field(..., description="The brand being analyzed")
    total_citations: int = Field(default=0, ge=0)
    entries: list[SourceAttributionEntry] = Field(
        default_factory=list,
        description="Source domains ranked by citation count (descending)",
    )
    by_type: dict[str, int] = Field(
        default_factory=dict,
        description="Citation counts grouped by source type",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def target_cited_domains(self) -> list[str]:
        """Domains whose citations were associated with the target brand."""
        return [e.domain for e in self.entries if e.cites_target]


class ProviderResult(BaseModel):
    """Result from a single LLM provider query."""

    provider: str = Field(..., description="Name of the LLM provider")
    model: str = Field(..., description="Model name used")
    prompt: str = Field(..., description="The prompt sent to the LLM")
    response: str = Field(..., description="The LLM's response")
    mentions: list[BrandMention] = Field(
        default_factory=list, description="Brand mentions extracted from response"
    )
    citations: list[Citation] = Field(
        default_factory=list, description="Citations extracted from response"
    )
    latency_ms: float = Field(..., ge=0, description="Response latency in milliseconds")
    cost_usd: float | None = Field(
        default=None, ge=0, description="Estimated cost in USD"
    )
    error: str | None = Field(
        default=None, description="Error message if request failed"
    )
    grounded: bool = Field(
        default=False,
        description="True if this result came from a web-grounded query "
        "(provider web search) rather than a base-model completion",
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def success(self) -> bool:
        """Whether the request was successful."""
        return self.error is None

    @computed_field  # type: ignore[prop-decorator]
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


class ScoreBreakdown(BaseModel):
    """Breakdown of the four factors that compose the visibility score."""

    mention_frequency: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Mention frequency sub-score (0-100 before weighting)",
    )
    sentiment: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Sentiment sub-score (0-100 before weighting)",
    )
    position: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Position / prominence sub-score (0-100 before weighting)",
    )
    recommendation: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Recommendation rate sub-score (0-100 before weighting)",
    )


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
    score_breakdown: ScoreBreakdown | None = Field(
        default=None, description="Breakdown of the four scoring factors"
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


class ShareOfVoiceEntry(BaseModel):
    """Share-of-voice numbers for a single brand within a prompt set."""

    brand_name: str = Field(..., description="Brand or competitor name")
    appearances: int = Field(
        default=0, ge=0, description="Number of prompts where the brand appeared"
    )
    total_prompts: int = Field(
        default=0, ge=0, description="Number of prompts evaluated"
    )
    presence_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="appearances / total_prompts (how often the brand shows up at all)",
    )
    share_of_voice: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="appearances / sum(appearances across all tracked brands)",
    )


class ShareOfVoiceReport(BaseModel):
    """Presence-based Share of Voice across the brand and its competitors.

    This is the canonical GEO metric: of all the brand presence across the
    tracked set (target + competitors), what fraction is the target's. It is
    computed per prompt (a brand "appears" in a prompt if it is mentioned at
    least once) and aggregated overall and per provider.
    """

    target_brand: str = Field(..., description="The brand being analyzed")
    aggregate: dict[str, ShareOfVoiceEntry] = Field(
        default_factory=dict,
        description="brand -> share-of-voice entry across all providers",
    )
    by_provider: dict[str, dict[str, ShareOfVoiceEntry]] = Field(
        default_factory=dict,
        description="provider -> brand -> share-of-voice entry",
    )
    target_rank: int = Field(
        default=1, ge=1, description="Target's rank by appearances (1 = leader)"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def target_share(self) -> float:
        """The target brand's aggregate share of voice (0.0-1.0)."""
        entry = self.aggregate.get(self.target_brand)
        return entry.share_of_voice if entry else 0.0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def target_presence_rate(self) -> float:
        """The target brand's aggregate presence rate (0.0-1.0)."""
        entry = self.aggregate.get(self.target_brand)
        return entry.presence_rate if entry else 0.0


class VolatilityMetrics(BaseModel):
    """Metrics for score volatility (run-to-run or period-to-period)."""

    volatility_score: float = Field(ge=0.0, description="Standard deviation of changes")
    max_swing: float = Field(ge=0.0, description="Maximum single-period change")
    average_change: float = Field(description="Average period-to-period change")
    stability_rating: Literal["stable", "moderate", "volatile"]


class PromptStability(BaseModel):
    """How consistently a single prompt surfaces the brand across repeated runs."""

    prompt: str = Field(..., description="The prompt that was repeated")
    runs: int = Field(..., ge=1, description="Number of times the prompt was run")
    appearances: int = Field(
        default=0, ge=0, description="Runs where the brand appeared"
    )
    presence_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="appearances / runs"
    )
    flip_flopped: bool = Field(
        default=False,
        description="True if the brand appeared in some runs but not others",
    )


class StabilityReport(BaseModel):
    """Trustworthiness of a single scan, measured by repeating it N times.

    Answer engines are probabilistic, so a single visibility number can be
    misleading. A stability scan repeats every prompt ``runs`` times and reports
    how consistent the result is — the headline ``stability_score`` (0-100) tells
    you how much to trust a one-shot scan.
    """

    brand: str = Field(..., description="The brand being analyzed")
    runs: int = Field(..., ge=1, description="Number of repeated scans")
    score_per_run: list[float] = Field(
        default_factory=list, description="Visibility score from each run"
    )
    mean_score: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Mean visibility score across runs"
    )
    score_confidence_interval: tuple[float, float] = Field(
        default=(0.0, 0.0), description="95% confidence interval for the score"
    )
    volatility: VolatilityMetrics = Field(
        ..., description="Run-to-run volatility of the visibility score"
    )
    stability_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="0-100: how trustworthy a single scan is (100 = perfectly stable)",
    )
    overall_presence_consistency: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Mean per-prompt presence rate (1.0 = brand appears in every run)",
    )
    prompt_stability: list[PromptStability] = Field(
        default_factory=list, description="Per-prompt stability detail"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def flip_flop_count(self) -> int:
        """Number of prompts that flip-flopped (inconsistent) across runs."""
        return sum(1 for p in self.prompt_stability if p.flip_flopped)


class Report(BaseModel):
    """Complete visibility report for a brand scan."""

    brand: str = Field(..., description="The brand being analyzed")
    visibility_score: float = Field(
        ..., ge=0.0, le=100.0, description="Overall visibility score"
    )
    mention_count: int = Field(
        ..., ge=0, description="Total mentions across all queries"
    )
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
    citation_summary: CitationSummary = Field(
        default_factory=CitationSummary,
        description="Aggregated citations from all provider responses",
    )
    share_of_voice: ShareOfVoiceReport | None = Field(
        default=None,
        description="Presence-based Share of Voice vs competitors",
    )
    stability: StabilityReport | None = Field(
        default=None,
        description="Run-to-run stability of the visibility score (if measured)",
    )
    source_attribution: SourceAttributionReport | None = Field(
        default=None,
        description="Which source domains the engines cite for this brand/category",
    )
    measurement_tier: Literal["demo", "base_model", "api_grounded"] = Field(
        default="base_model",
        description="How this scan was measured: 'demo' (mock data), 'base_model' "
        "(LLM completion, no web search — measures training memory), or "
        "'api_grounded' (provider web search — approximates, but does NOT equal, "
        "the consumer product).",
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    scan_duration_seconds: float = Field(default=0.0, ge=0)
    total_cost_usd: float | None = Field(default=None, ge=0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def providers_used(self) -> list[str]:
        """List of providers used in this scan."""
        return list({r.provider for r in self.provider_results})

    @computed_field  # type: ignore[prop-decorator]
    @property
    def success_rate(self) -> float:
        """Rate of successful provider queries."""
        if not self.provider_results:
            return 0.0
        return sum(1 for r in self.provider_results if r.success) / len(
            self.provider_results
        )

    def assert_visibility(
        self,
        min_score: float | None = None,
        min_share_of_voice: float | None = None,
        min_presence_rate: float | None = None,
        min_stability_score: float | None = None,
        max_rank: int | None = None,
    ) -> Report:
        """Assert that this report meets visibility thresholds.

        Designed for CI/CD: raises :class:`VisibilityAssertionError` (an
        ``AssertionError`` subclass) listing every unmet threshold, so a
        failing gate stops the pipeline. Returns ``self`` on success for
        chaining, e.g. ``Beacon("Nike").scan().assert_visibility(min_score=50)``.

        Args:
            min_score: Minimum overall visibility score (0-100).
            min_share_of_voice: Minimum target Share of Voice (0.0-1.0). Requires
                a report that includes share-of-voice data.
            min_presence_rate: Minimum target presence rate (0.0-1.0).
            min_stability_score: Minimum stability score (0-100). Requires a
                stability scan (``.with_stability()``).
            max_rank: Maximum acceptable Share-of-Voice rank (1 = leader).

        Returns:
            Self, for chaining.

        Raises:
            VisibilityAssertionError: If any provided threshold is unmet.
        """
        failures: list[str] = []

        if min_score is not None and self.visibility_score < min_score:
            failures.append(
                f"visibility_score {self.visibility_score:.1f} < {min_score}"
            )

        if min_share_of_voice is not None:
            sov = self.share_of_voice.target_share if self.share_of_voice else 0.0
            if sov < min_share_of_voice:
                failures.append(f"share_of_voice {sov:.3f} < {min_share_of_voice}")

        if min_presence_rate is not None:
            presence = (
                self.share_of_voice.target_presence_rate if self.share_of_voice else 0.0
            )
            if presence < min_presence_rate:
                failures.append(f"presence_rate {presence:.3f} < {min_presence_rate}")

        if min_stability_score is not None:
            stability = self.stability.stability_score if self.stability else 0.0
            if stability < min_stability_score:
                failures.append(
                    f"stability_score {stability:.1f} < {min_stability_score} "
                    "(run a stability scan with .with_stability())"
                    if self.stability is None
                    else f"stability_score {stability:.1f} < {min_stability_score}"
                )

        if max_rank is not None:
            rank = self.share_of_voice.target_rank if self.share_of_voice else 999
            if rank > max_rank:
                failures.append(f"share_of_voice rank {rank} > {max_rank}")

        if failures:
            raise VisibilityAssertionError(
                f"Visibility assertion failed for '{self.brand}': "
                + "; ".join(failures),
                failures=failures,
            )

        return self


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

    @computed_field  # type: ignore[prop-decorator]
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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def change_direction(self) -> Literal["up", "down", "stable"]:
        """Direction of score change."""
        if self.score_change > 1.0:
            return "up"
        elif self.score_change < -1.0:
            return "down"
        return "stable"
