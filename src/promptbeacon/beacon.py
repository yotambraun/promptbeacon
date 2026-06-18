"""Main Beacon class for LLM visibility monitoring."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Self
else:
    try:
        from typing import Self
    except ImportError:
        from typing_extensions import Self

from promptbeacon.analysis.explainer import (
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
)
from promptbeacon.analysis.sources import aggregate_source_attribution
from promptbeacon.analysis.stability import aggregate_stability
from promptbeacon.analysis.statistics import calculate_confidence_interval
from promptbeacon.core.config import BeaconConfig, Provider
from promptbeacon.core.exceptions import ConfigurationError, ScanError
from promptbeacon.core.schemas import (
    Citation,
    CitationSummary,
    HistoryReport,
    ProviderResult,
    Report,
    ScanComparison,
)
from promptbeacon.extraction.citations import extract_citations
from promptbeacon.extraction.llm_extraction import (
    build_extraction_prompt,
    parse_llm_extraction,
)
from promptbeacon.extraction.mentions import MentionExtractionResult, extract_mentions
from promptbeacon.prompts.templates import get_industry_prompts
from promptbeacon.providers.base import BaseLLMClient
from promptbeacon.providers.litellm_client import LiteLLMClient, get_available_providers
from promptbeacon.providers.mock_client import MockLLMClient
from promptbeacon.storage.cache import ResponseCache
from promptbeacon.storage.database import Database

logger = logging.getLogger(__name__)

# Default prompts for brand visibility analysis
DEFAULT_PROMPTS = [
    "What are the best {category} brands?",
    "Can you recommend a good {category} company?",
    "What are the top options for {category}?",
    "Which {category} brand should I choose?",
    "What is the most popular {category} brand?",
    "Can you compare {category} brands?",
    "What {category} would you recommend?",
    "Which company is the leader in {category}?",
    "What are the pros and cons of different {category} brands?",
    "Who makes the best {category} products?",
]


class Beacon:
    """Main class for LLM brand visibility monitoring.

    Provides a fluent API for configuring and running brand visibility scans.

    Example:
        >>> beacon = Beacon("Acme Corp")
        >>> report = beacon.scan()
        >>> print(report.visibility_score)
        73.2

        >>> # Advanced usage with fluent API
        >>> beacon = (
        ...     Beacon("Acme Corp")
        ...     .with_competitors(["Competitor A", "Competitor B"])
        ...     .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
        ...     .with_categories(["product quality", "pricing"])
        ...     .with_prompt_count(50)
        ... )
        >>> report = beacon.scan()
    """

    def __init__(self, brand: str):
        """Initialize a Beacon for a brand.

        Args:
            brand: The brand name to monitor.
        """
        self._config = BeaconConfig(brand=brand)
        self._database: Database | None = None
        self._custom_prompts: list[str] | None = None
        self._scoring_weights: ScoringWeights | None = None
        self._cache: ResponseCache | None = None
        self._demo_mode: bool = False
        self._grounded: bool = False
        self._stability_runs: int | None = None
        self._smart_extraction: bool = False
        self._extraction_model: str | None = None
        self._smart_recommendations: bool = False

    @property
    def brand(self) -> str:
        """The brand being monitored."""
        return self._config.brand

    @property
    def config(self) -> BeaconConfig:
        """The current configuration."""
        return self._config

    def with_aliases(self, *aliases: str) -> Self:
        """Add alternative names for the brand.

        Aliases are matched in LLM responses and counted as mentions of
        the primary brand.  For example, ``"Nike Inc"`` and
        ``"Nike Corporation"`` would both count as Nike mentions.

        Args:
            *aliases: Alternative brand names.

        Returns:
            Self for chaining.
        """
        flat_aliases = []
        for a in aliases:
            if isinstance(a, (list, tuple)):
                flat_aliases.extend(a)
            else:
                flat_aliases.append(a)
        self._config = self._config.model_copy(update={"brand_aliases": flat_aliases})
        return self

    def with_competitors(self, *competitors: str) -> Self:
        """Add competitors to track.

        Args:
            *competitors: Competitor brand names.

        Returns:
            Self for chaining.
        """
        flat_competitors = []
        for c in competitors:
            if isinstance(c, (list, tuple)):
                flat_competitors.extend(c)
            else:
                flat_competitors.append(c)
        self._config = self._config.model_copy(update={"competitors": flat_competitors})
        return self

    def with_providers(self, *providers: Provider) -> Self:
        """Set the LLM providers to use.

        Args:
            *providers: Provider enum values.

        Returns:
            Self for chaining.
        """
        flat_providers = []
        for p in providers:
            if isinstance(p, (list, tuple)):
                flat_providers.extend(p)
            else:
                flat_providers.append(p)
        self._config = self._config.model_copy(update={"providers": flat_providers})
        return self

    def with_categories(self, *categories: str) -> Self:
        """Set the categories to analyze.

        Args:
            *categories: Category/topic names.

        Returns:
            Self for chaining.
        """
        flat_categories = []
        for c in categories:
            if isinstance(c, (list, tuple)):
                flat_categories.extend(c)
            else:
                flat_categories.append(c)
        self._config = self._config.model_copy(update={"categories": flat_categories})
        return self

    def with_prompt_count(self, count: int) -> Self:
        """Set the number of prompts per category.

        Args:
            count: Number of prompts (1-1000).

        Returns:
            Self for chaining.
        """
        self._config = self._config.model_copy(update={"prompt_count": count})
        return self

    def with_storage(self, path: str | Path) -> Self:
        """Enable storage with a DuckDB file.

        Args:
            path: Path to the DuckDB file.

        Returns:
            Self for chaining.
        """
        path = Path(path).expanduser()
        self._config = self._config.model_copy(update={"storage_path": path})
        self._database = Database(path)
        return self

    def with_temperature(self, temperature: float) -> Self:
        """Set the temperature for LLM queries.

        Args:
            temperature: Temperature value (0.0-2.0).

        Returns:
            Self for chaining.
        """
        self._config = self._config.model_copy(update={"temperature": temperature})
        return self

    def with_max_tokens(self, max_tokens: int) -> Self:
        """Set the maximum tokens for LLM responses.

        Args:
            max_tokens: Maximum tokens (1-32768).

        Returns:
            Self for chaining.
        """
        self._config = self._config.model_copy(update={"max_tokens": max_tokens})
        return self

    def with_timeout(self, timeout: float) -> Self:
        """Set the request timeout.

        Args:
            timeout: Timeout in seconds.

        Returns:
            Self for chaining.
        """
        self._config = self._config.model_copy(update={"timeout": timeout})
        return self

    def with_prompts(self, prompts: list[str]) -> Self:
        """Set custom prompts for scanning.

        Use {category} as a placeholder for category names.

        Args:
            prompts: List of prompt templates.

        Returns:
            Self for chaining.
        """
        self._custom_prompts = prompts
        return self

    def with_industry(self, industry: str) -> Self:
        """Use industry-specific prompt templates.

        Replaces the default prompts with templates tuned for a specific
        industry vertical. Available industries: ecommerce, saas, finance,
        healthcare, travel, food, tech.

        Args:
            industry: Industry name (case-insensitive).

        Returns:
            Self for chaining.

        Raises:
            ValueError: If the industry is not recognized.
        """
        self._custom_prompts = get_industry_prompts(industry)
        return self

    def with_scoring_weights(
        self,
        mention_frequency: float = 0.3,
        sentiment: float = 0.25,
        position: float = 0.25,
        recommendation: float = 0.2,
    ) -> Self:
        """Customise the weights used when calculating the visibility score.

        The four weights control how much each signal contributes to the
        final 0-100 score.  They should sum to 1.0 for a meaningful result.

        Args:
            mention_frequency: Weight for how often the brand is mentioned.
            sentiment: Weight for sentiment polarity.
            position: Weight for ranking / early-mention prominence.
            recommendation: Weight for explicit recommendation signals.

        Returns:
            Self for chaining.
        """
        self._scoring_weights = ScoringWeights(
            mention_frequency=mention_frequency,
            sentiment=sentiment,
            position=position,
            recommendation=recommendation,
        )
        return self

    def with_cache(
        self,
        cache_dir: str | Path | None = None,
        ttl_seconds: int = 86400,
    ) -> Self:
        """Enable response caching to skip identical LLM queries.

        Cached responses are stored as JSON files keyed by a SHA-256 hash
        of (prompt, provider, model).

        Args:
            cache_dir: Directory for cache files.
                Defaults to ``~/.promptbeacon/cache/``.
            ttl_seconds: Time-to-live in seconds. Defaults to 24 hours.

        Returns:
            Self for chaining.
        """
        dir_path = Path(cache_dir).expanduser() if cache_dir else None
        self._cache = ResponseCache(cache_dir=dir_path, ttl_seconds=ttl_seconds)
        return self

    def demo(self) -> Self:
        """Run with realistic canned responses — no API keys required.

        Demo mode swaps the real LLM clients for an offline mock that returns
        believable, deterministic answers weaving in your brand and competitors.
        Perfect for a ``pip install promptbeacon`` first run, CI smoke checks,
        and reproducible tests.

        Returns:
            Self for chaining.
        """
        self._demo_mode = True
        return self

    def with_grounding(self, enabled: bool = True) -> Self:
        """Measure web-grounded answers — what AI *search* returns, not memory.

        By default a scan queries plain LLM completions, which reflect the
        model's training memory. Grounded mode enables each provider's native
        web-search/grounding tool so the scan reflects what users actually see
        when the engine searches the live web, and captures the real sources it
        cites. The report is tagged ``measurement_tier="api_grounded"``.

        Honesty note: the provider APIs approximate but do **not** equal the
        consumer products (ChatGPT.com etc.), which run extra orchestration.

        Costs more per scan (search fees + tokens) and is billed to your own
        keys; ``demo()`` stays free. No effect in demo mode.

        Args:
            enabled: Whether to enable web-grounded scanning.

        Returns:
            Self for chaining.
        """
        self._grounded = enabled
        return self

    def with_stability(self, runs: int = 5) -> Self:
        """Repeat every prompt ``runs`` times to measure answer-to-answer stability.

        Answer engines are probabilistic, so a single visibility number can be
        misleading. A stability scan reruns the whole scan ``runs`` times and
        reports how trustworthy that number is (see ``report.stability``).

        WARNING: this multiplies API calls — and therefore cost — by ``runs``.
        It is opt-in and bypasses the response cache (otherwise every run would
        be identical and report fake-perfect stability). Use a non-zero
        temperature, or the runs will not vary.

        Args:
            runs: Number of times to repeat the scan (>= 2 to be meaningful).

        Returns:
            Self for chaining.
        """
        if runs < 1:
            raise ValueError("stability runs must be >= 1")
        self._stability_runs = runs
        return self

    def with_smart_extraction(self, model: str | None = None) -> Self:
        """Use an LLM (not regex) to extract mentions, sentiment, and recommendations.

        Smart mode reads each response with a cheap model and structured output,
        catching paraphrases and nuance that regex misses — at the cost of one
        extra LLM call per response. Opt-in; falls back to regex on any error.
        Not used in demo mode (which makes no real API calls).

        Args:
            model: Optional model override for the extraction call (defaults to
                the provider's default model).

        Returns:
            Self for chaining.
        """
        self._smart_extraction = True
        self._extraction_model = model
        return self

    def with_smart_recommendations(self) -> Self:
        """Generate evidence-linked recommendations with an LLM instead of rules.

        Produces "why you're invisible and how to fix it" guidance grounded in
        the scan's own data, at the cost of one extra LLM call per scan. Opt-in;
        falls back to rule-based recommendations on any error. Requires API keys.

        Returns:
            Self for chaining.
        """
        self._smart_recommendations = True
        return self

    def _make_client(self, provider: Provider, variation: int = 0) -> BaseLLMClient:
        """Create the LLM client for a provider (real or demo mock)."""
        if self._demo_mode:
            return MockLLMClient(
                provider,
                brand=self._config.brand,
                competitors=self._config.competitors,
                variation=variation,
            )
        return LiteLLMClient(
            provider=provider,
            timeout=self._config.timeout,
            max_retries=self._config.max_retries,
        )

    def _resolve_providers(self) -> list[Provider]:
        """Determine which providers to query, honouring demo mode."""
        if self._demo_mode:
            # No API keys needed; use the configured providers as-is.
            return list(self._config.providers)

        available = get_available_providers()
        providers_to_use = [p for p in self._config.providers if p in available]
        if not providers_to_use:
            raise ConfigurationError(
                f"No API keys found for configured providers: {self._config.providers}. "
                "Set environment variables like OPENAI_API_KEY, ANTHROPIC_API_KEY, etc. "
                "Or try keyless demo mode: Beacon(...).demo().scan()"
            )
        return providers_to_use

    def _get_prompts(self) -> list[str]:
        """Generate the list of prompts to use."""
        base_prompts = self._custom_prompts or DEFAULT_PROMPTS
        prompts = []

        for category in self._config.categories:
            for prompt_template in base_prompts[: self._config.prompt_count]:
                prompts.append(prompt_template.format(category=category))

        return prompts

    def _get_database(self) -> Database | None:
        """Get or create the database connection."""
        if self._config.storage_path and self._database is None:
            self._database = Database(self._config.storage_path)
        return self._database

    def scan(self) -> Report:
        """Run a synchronous visibility scan.

        Returns:
            Report with visibility analysis.
        """
        return asyncio.run(self.scan_async())

    async def scan_async(self) -> Report:
        """Run an asynchronous visibility scan.

        Returns:
            Report with visibility analysis.
        """
        start_time = time.time()
        results, total_cost = await self._collect_results()
        if not results:
            raise ScanError("All provider queries failed. Check API keys and network.")
        report = self._build_report(results, total_cost, start_time)
        await self._apply_smart_recommendations(report)

        db = self._get_database()
        if db:
            db.save_report(report)

        return report

    def scan_stability(self) -> Report:
        """Run a synchronous stability scan (repeats the scan N times).

        Configure with ``.with_stability(runs)`` first. The returned Report is a
        normal single-scan report with ``report.stability`` populated.

        Returns:
            Report with a populated ``stability`` field.
        """
        return asyncio.run(self.scan_stability_async())

    async def scan_stability_async(self) -> Report:
        """Run an asynchronous stability scan.

        Repeats the full scan ``runs`` times (cache bypassed) and attaches a
        :class:`StabilityReport` describing how trustworthy a single scan is.

        Returns:
            Report with a populated ``stability`` field.
        """
        runs = self._stability_runs or 5
        start_time = time.time()

        all_runs: list[list[ProviderResult]] = []
        total_cost = 0.0
        for i in range(runs):
            results, cost = await self._collect_results(variation=i, use_cache=False)
            if results:
                all_runs.append(results)
                total_cost += cost

        if not all_runs:
            raise ScanError("All provider queries failed. Check API keys and network.")

        report = self._build_report(all_runs[0], total_cost, start_time)
        report.stability = aggregate_stability(
            all_runs, self._config.brand, weights=self._scoring_weights
        )
        await self._apply_smart_recommendations(report)

        db = self._get_database()
        if db:
            db.save_report(report)

        return report

    async def _collect_results(
        self, variation: int = 0, use_cache: bool = True
    ) -> tuple[list[ProviderResult], float]:
        """Query all providers once and collect the raw results.

        Args:
            variation: Seed passed to demo clients so repeated runs differ.
            use_cache: Whether to use the response cache (False for stability).

        Returns:
            Tuple of (results, total_cost_usd).
        """
        providers_to_use = self._resolve_providers()

        prompts = self._get_prompts()
        if not prompts:
            raise ConfigurationError(
                "No prompts generated. Check categories configuration."
            )

        results: list[ProviderResult] = []
        total_cost = 0.0

        for provider in providers_to_use:
            client = self._make_client(provider, variation=variation)

            # Run prompts concurrently with semaphore for rate limiting
            semaphore = asyncio.Semaphore(self._config.concurrent_requests)

            async def query_with_semaphore(
                prompt: str,
                sem: asyncio.Semaphore = semaphore,
                cli: BaseLLMClient = client,
            ) -> ProviderResult:
                async with sem:
                    return await self._query_provider(cli, prompt, use_cache=use_cache)

            provider_results = await asyncio.gather(
                *[query_with_semaphore(p) for p in prompts],
                return_exceptions=True,
            )

            for result in provider_results:
                if isinstance(result, ProviderResult):
                    results.append(result)
                    if result.cost_usd:
                        total_cost += result.cost_usd
                elif isinstance(result, Exception):
                    logger.warning("Provider query failed: %s", result)

        return results, total_cost

    def _build_report(
        self,
        results: list[ProviderResult],
        total_cost: float,
        start_time: float,
    ) -> Report:
        """Build a Report from collected provider results."""
        # Calculate metrics
        visibility_score = calculate_visibility_score(
            results, self._config.brand, weights=self._scoring_weights
        )
        metrics = calculate_metrics(
            results, self._config.brand, weights=self._scoring_weights
        )

        # Calculate confidence interval
        scores = [
            calculate_visibility_score(
                [r], self._config.brand, weights=self._scoring_weights
            )
            for r in results
            if r.success
        ]
        if scores:
            metrics.confidence_interval = calculate_confidence_interval(scores)

        # Calculate competitor scores
        competitor_comparison = {}
        if self._config.competitors:
            competitor_comparison = calculate_competitor_scores(
                results, self._config.competitors
            )

        # Calculate Share of Voice (always — cheap, local)
        share_of_voice = calculate_share_of_voice(
            results, self._config.brand, self._config.competitors
        )

        # Generate explanations and recommendations
        explanations = generate_explanations(
            results,
            self._config.brand,
            visibility_score,
            self._config.competitors,
        )
        recommendations = generate_recommendations(
            results,
            self._config.brand,
            visibility_score,
            metrics.sentiment,
            self._config.competitors,
        )

        # Aggregate citations across all results
        all_citations = [c for r in results for c in r.citations]
        unique_domains = sorted({c.source_name for c in all_citations if c.url})
        citation_summary = CitationSummary(
            total_citations=len(all_citations),
            unique_domains=unique_domains,
            citations=all_citations,
        )

        # Rank the source domains the engines cite (actionable GEO lever)
        source_attribution = aggregate_source_attribution(
            results, self._config.brand, self._config.competitors
        )

        scan_duration = time.time() - start_time
        return Report(
            brand=self._config.brand,
            visibility_score=visibility_score,
            mention_count=metrics.mention_count,
            sentiment_breakdown=metrics.sentiment,
            competitor_comparison=competitor_comparison,
            provider_results=results,
            metrics=metrics,
            explanations=explanations,
            recommendations=recommendations,
            citation_summary=citation_summary,
            share_of_voice=share_of_voice,
            source_attribution=source_attribution,
            measurement_tier=self._measurement_tier(),
            timestamp=datetime.utcnow(),
            scan_duration_seconds=round(scan_duration, 2),
            total_cost_usd=round(total_cost, 4) if total_cost > 0 else None,
        )

    def _measurement_tier(self) -> str:
        """How this scan was measured (drives the honesty label on the report)."""
        if self._demo_mode:
            return "demo"
        if self._grounded:
            return "api_grounded"
        return "base_model"

    async def _apply_smart_recommendations(self, report: Report) -> None:
        """Replace rule-based recommendations with LLM-generated ones (opt-in)."""
        if not self._smart_recommendations or self._demo_mode:
            return
        try:
            providers = self._resolve_providers()
            client = self._make_client(providers[0])
            prompt = build_recommendations_prompt(report)
            resp = await client.complete(
                prompt=prompt,
                model=self._extraction_model,
                temperature=0.3,
                max_tokens=900,
            )
            recs = parse_recommendations(resp.content)
            if recs:
                report.recommendations = recs
        except Exception as e:  # noqa: BLE001 — keep rule-based recs on any failure
            logger.warning("Smart recommendations failed, keeping rule-based: %s", e)

    async def _extract(
        self, client: BaseLLMClient, response_content: str
    ) -> MentionExtractionResult:
        """Extract mentions via LLM smart mode (if enabled) or regex fallback."""
        if self._smart_extraction and not self._demo_mode:
            try:
                prompt = build_extraction_prompt(
                    response_content,
                    self._config.brand,
                    self._config.competitors,
                    self._config.brand_aliases or None,
                )
                resp = await client.complete(
                    prompt=prompt,
                    model=self._extraction_model,
                    temperature=0.0,
                    max_tokens=800,
                )
                return parse_llm_extraction(
                    resp.content,
                    response_content,
                    self._config.brand,
                    self._config.competitors,
                    self._config.brand_aliases or None,
                )
            except Exception as e:  # noqa: BLE001 — any failure falls back to regex
                logger.warning("Smart extraction failed, using regex: %s", e)

        return extract_mentions(
            response_content,
            self._config.brand,
            self._config.competitors,
            aliases=self._config.brand_aliases or None,
        )

    async def _query_provider(
        self, client: BaseLLMClient, prompt: str, use_cache: bool = True
    ) -> ProviderResult:
        """Query a single provider with a prompt.

        Args:
            client: The LLM client.
            prompt: The prompt to send.

        Returns:
            ProviderResult with the response.
        """
        try:
            # Check cache first (bypassed during stability scans)
            cached_content: str | None = None
            if use_cache and self._cache:
                cached_content = self._cache.get(
                    prompt, client.provider_name, client.model
                )

            if cached_content is not None:
                response_content = cached_content
                latency_ms = 0.0
                cost_usd = None
                provider_name = client.provider_name
                model_name = client.model
            else:
                response = await client.complete(
                    prompt=prompt,
                    temperature=self._config.temperature,
                    max_tokens=self._config.max_tokens,
                )
                response_content = response.content
                latency_ms = response.latency_ms
                cost_usd = response.cost_usd
                provider_name = response.provider
                model_name = response.model

                # Store in cache (skipped during stability scans)
                if use_cache and self._cache:
                    self._cache.set(
                        prompt, client.provider_name, client.model, response_content
                    )

            # Extract mentions from response (LLM smart mode or regex)
            extraction = await self._extract(client, response_content)

            # Extract citations
            all_brands = (
                [self._config.brand]
                + (self._config.brand_aliases or [])
                + (self._config.competitors or [])
            )
            citation_result = extract_citations(response_content, brands=all_brands)

            return ProviderResult(
                provider=provider_name,
                model=model_name,
                prompt=prompt,
                response=response_content,
                mentions=extraction.mentions,
                citations=[
                    Citation(
                        url=c.url,
                        source_name=c.source_name,
                        context=c.context,
                        brand_associated=c.brand_associated,
                        query=prompt,
                    )
                    for c in citation_result.citations
                ],
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            return ProviderResult(
                provider=client.provider_name,
                model=client.model,
                prompt=prompt,
                response="",
                mentions=[],
                latency_ms=0,
                cost_usd=None,
                error=str(e),
                timestamp=datetime.utcnow(),
            )

    def get_history(self, days: int = 30) -> HistoryReport:
        """Get historical visibility data.

        Args:
            days: Number of days of history to retrieve.

        Returns:
            HistoryReport with historical data.
        """
        db = self._get_database()
        if not db:
            raise ConfigurationError(
                "Storage not configured. Use .with_storage() to enable history."
            )
        return db.get_history(self._config.brand, days)

    def compare_with_previous(self) -> ScanComparison | None:
        """Compare the latest scan with the previous one.

        Returns:
            ScanComparison or None if not enough data.
        """
        db = self._get_database()
        if not db:
            raise ConfigurationError(
                "Storage not configured. Use .with_storage() to enable comparisons."
            )
        return db.compare_with_previous(self._config.brand)

    def close(self) -> None:
        """Close database connections and clean up resources."""
        if self._database:
            self._database.close()
            self._database = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
