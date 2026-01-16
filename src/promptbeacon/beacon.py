"""Main Beacon class for LLM visibility monitoring."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Self

from promptbeacon.analysis.explainer import generate_explanations, generate_recommendations
from promptbeacon.analysis.scorer import (
    calculate_competitor_scores,
    calculate_metrics,
    calculate_visibility_score,
)
from promptbeacon.analysis.statistics import calculate_confidence_interval
from promptbeacon.core.config import BeaconConfig, Provider
from promptbeacon.core.exceptions import ConfigurationError, ScanError
from promptbeacon.core.schemas import (
    HistoryReport,
    ProviderResult,
    Report,
    ScanComparison,
    SentimentBreakdown,
    VisibilityMetrics,
)
from promptbeacon.extraction.mentions import extract_mentions
from promptbeacon.providers.litellm_client import LiteLLMClient, get_available_providers
from promptbeacon.storage.database import Database


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

    @property
    def brand(self) -> str:
        """The brand being monitored."""
        return self._config.brand

    @property
    def config(self) -> BeaconConfig:
        """The current configuration."""
        return self._config

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

        # Check for available providers
        available = get_available_providers()
        providers_to_use = [p for p in self._config.providers if p in available]

        if not providers_to_use:
            raise ConfigurationError(
                f"No API keys found for configured providers: {self._config.providers}. "
                "Set environment variables like OPENAI_API_KEY, ANTHROPIC_API_KEY, etc."
            )

        # Generate prompts
        prompts = self._get_prompts()
        if not prompts:
            raise ConfigurationError("No prompts generated. Check categories configuration.")

        # Query all providers concurrently
        results: list[ProviderResult] = []
        total_cost = 0.0

        for provider in providers_to_use:
            client = LiteLLMClient(
                provider=provider,
                timeout=self._config.timeout,
                max_retries=self._config.max_retries,
            )

            # Run prompts concurrently with semaphore for rate limiting
            semaphore = asyncio.Semaphore(self._config.concurrent_requests)

            async def query_with_semaphore(prompt: str) -> ProviderResult:
                async with semaphore:
                    return await self._query_provider(client, prompt)

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
                    # Log error but continue
                    pass

        if not results:
            raise ScanError("All provider queries failed. Check API keys and network.")

        # Calculate metrics
        visibility_score = calculate_visibility_score(results, self._config.brand)
        metrics = calculate_metrics(results, self._config.brand)

        # Calculate confidence interval
        scores = [
            calculate_visibility_score([r], self._config.brand)
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

        # Build report
        scan_duration = time.time() - start_time
        report = Report(
            brand=self._config.brand,
            visibility_score=visibility_score,
            mention_count=metrics.mention_count,
            sentiment_breakdown=metrics.sentiment,
            competitor_comparison=competitor_comparison,
            provider_results=results,
            metrics=metrics,
            explanations=explanations,
            recommendations=recommendations,
            timestamp=datetime.utcnow(),
            scan_duration_seconds=round(scan_duration, 2),
            total_cost_usd=round(total_cost, 4) if total_cost > 0 else None,
        )

        # Save to storage if configured
        db = self._get_database()
        if db:
            db.save_report(report)

        return report

    async def _query_provider(
        self, client: LiteLLMClient, prompt: str
    ) -> ProviderResult:
        """Query a single provider with a prompt.

        Args:
            client: The LLM client.
            prompt: The prompt to send.

        Returns:
            ProviderResult with the response.
        """
        try:
            response = await client.complete(
                prompt=prompt,
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens,
            )

            # Extract mentions from response
            extraction = extract_mentions(
                response.content,
                self._config.brand,
                self._config.competitors,
            )

            return ProviderResult(
                provider=response.provider,
                model=response.model,
                prompt=prompt,
                response=response.content,
                mentions=extraction.mentions,
                latency_ms=response.latency_ms,
                cost_usd=response.cost_usd,
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
