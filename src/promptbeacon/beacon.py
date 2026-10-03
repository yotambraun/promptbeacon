"""Main Beacon class for LLM visibility monitoring."""

from __future__ import annotations

import asyncio
import logging
import time
import warnings
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from typing_extensions import Self
else:
    try:
        from typing import Self
    except ImportError:
        from typing_extensions import Self

from promptbeacon.analysis.category import (
    build_category_prompt,
    competitor_alternative_prompts,
    parse_profile,
)
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
from promptbeacon.prompts.templates import (
    _BUYER_INTENT_TEMPLATES,
    expand_prompt_templates,
    get_industry_prompts,
)
from promptbeacon.providers.base import BaseLLMClient
from promptbeacon.providers.grounding import (
    GroundedClient,
    associate_brands,
    get_grounded_client,
)
from promptbeacon.providers.litellm_client import LiteLLMClient, get_available_providers
from promptbeacon.providers.mock_client import MockLLMClient
from promptbeacon.storage.cache import ResponseCache
from promptbeacon.storage.database import Database

if TYPE_CHECKING:
    from promptbeacon.projects import HttpResponse, ProjectProfile

logger = logging.getLogger(__name__)

PromptStrategy = Literal[
    "category", "inferred_category", "competitor_alternatives", "custom", "generic"
]

_NO_CATEGORY_MESSAGE = (
    "No category set for '{brand}', so prompts are generic (\"What are the best "
    'general brands?") and the score says little. Set one with '
    ".with_category('running shoes') (CLI: --category), add competitors, or "
    "opt in to .with_category_inference()."
)

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
        self._prompt_count_set: bool = False
        self._categories_set: bool = False
        self._infer_category: bool = False
        self._category_hints: list[str] = []
        self._category_inferred: bool = False
        self._fallback_category: str | None = None
        self._competitors_inferred: bool = False
        self.project: ProjectProfile | None = None
        self._extra_cost: float = 0.0
        self._explicit_prompts: bool = False
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
        self._categories_set = bool(flat_categories)
        return self

    def with_category(self, category: str) -> Self:
        """Set the category the prompts ask about (e.g. ``"running shoes"``).

        The category is what makes a scan meaningful: prompts become real buyer
        questions such as "What are the best running shoes?". Equivalent to
        ``with_categories(category)``.

        Args:
            category: The product/service category, phrased the way a buyer
                would (e.g. ``"crm software"``, ``"python http client"``).

        Returns:
            Self for chaining.
        """
        return self.with_categories(category)

    def with_category_inference(
        self, enabled: bool = True, hints: list[str] | None = None
    ) -> Self:
        """Infer the category with one cheap LLM call when none is set (opt-in).

        Only used when no category was given. Makes exactly one extra LLM call
        before the scan (logged, and its cost is included in the report), and
        records ``report.prompt_strategy == "inferred_category"``. Never runs in
        demo mode. For trend tracking, pin the inferred category with
        :meth:`with_category` so every run asks the same questions.

        Args:
            enabled: Whether to infer the category.
            hints: Optional context (e.g. a project description) for the model.

        Returns:
            Self for chaining.
        """
        self._infer_category = enabled
        self._category_hints = list(hints or [])
        return self

    def with_prompt_count(self, count: int) -> Self:
        """Set the number of prompts per category.

        Counts above the number of built-in templates are honoured: the set is
        extended deterministically with additional buyer-intent templates and
        phrasing variants. If ``count`` distinct prompts cannot be built, the
        scan raises :class:`ConfigurationError` instead of silently using fewer.

        Args:
            count: Number of prompts (1-1000).

        Returns:
            Self for chaining.
        """
        self._config = BeaconConfig.model_validate(
            {**self._config.model_dump(), "prompt_count": count}
        )
        self._prompt_count_set = True
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
        self._explicit_prompts = True
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
        self._explicit_prompts = False
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

    def _get_templates(self) -> list[str]:
        """The prompt templates for one category, honouring the prompt count.

        Custom prompts (``with_prompts``/``with_industry``/protocols) are used in
        full unless a prompt count was set explicitly. Counts larger than the
        template set are extended deterministically; impossible counts raise.
        """
        custom = self._custom_prompts
        if custom and not self._prompt_count_set:
            return list(custom)
        base = custom or DEFAULT_PROMPTS
        extra = None if custom else _BUYER_INTENT_TEMPLATES
        try:
            return expand_prompt_templates(base, self._config.prompt_count, extra)
        except ValueError as e:
            raise ConfigurationError(str(e)) from None

    def _prompt_plan(self) -> tuple[list[str], PromptStrategy]:
        """Resolve the prompts to send and how they were chosen.

        Order: an explicit (or inferred) category; custom prompts that need no
        category; competitor-anchored "alternatives to X" prompts when only
        competitors are known; otherwise the legacy generic set (with a warning
        emitted by the scan).
        """
        templates = self._get_templates()
        uses_category = any("{category}" in t for t in templates)

        if self._categories_set or not uses_category:
            prompts = [
                t.format(category=category)
                for category in self._config.categories
                for t in templates
            ]
            strategy: PromptStrategy
            if not uses_category:
                strategy = "custom"
            elif self._category_inferred:
                strategy = "inferred_category"
            else:
                strategy = "category"
            return prompts, strategy

        if self._config.competitors and not self._explicit_prompts:
            try:
                prompts = competitor_alternative_prompts(
                    self._config.competitors, self._config.prompt_count
                )
            except ValueError as e:
                raise ConfigurationError(str(e)) from None
            return prompts, "competitor_alternatives"

        prompts = [
            t.format(category=category)
            for category in self._config.categories
            for t in templates
        ]
        return prompts, "generic"

    def _get_prompts(self) -> list[str]:
        """Generate the list of prompts to use."""
        return self._prompt_plan()[0]

    async def _prepare_categories(self) -> None:
        """Resolve the category before a scan (opt-in inference) and warn if absent."""
        self._extra_cost = 0.0  # only this scan's inference call is billed to it
        if (
            self._infer_category
            and not self._categories_set
            and not self._demo_mode
            and any("{category}" in t for t in self._get_templates())
        ):
            category, competitors = await self._infer_profile_llm()
            if category:
                self.with_categories(category)
                self._category_inferred = True
            if competitors and not self._config.competitors:
                self.with_competitors(*competitors)
                self._competitors_inferred = True

        if not self._categories_set and self._fallback_category:
            self.with_categories(self._fallback_category)

        if self._prompt_plan()[1] == "generic":
            message = _NO_CATEGORY_MESSAGE.format(brand=self._config.brand)
            logger.warning(message)
            warnings.warn(message, UserWarning, stacklevel=3)

    async def _infer_profile_llm(self) -> tuple[str | None, list[str]]:
        """Ask one model for the category (and competitors, if none are set)."""
        want_competitors = not self._config.competitors
        try:
            provider = self._resolve_providers()[0]
            client = self._make_client(provider)
            prompt = build_category_prompt(
                self._config.brand,
                competitors=self._config.competitors,
                hints=self._category_hints,
                want_competitors=want_competitors,
            )
            resp = await client.complete(
                prompt=prompt,
                temperature=0.0,
                max_tokens=120 if want_competitors else 20,
            )
            if resp.cost_usd:
                self._extra_cost += resp.cost_usd
            category, competitors = parse_profile(resp.content, self._config.brand)
        except Exception as e:  # noqa: BLE001 — inference is best-effort
            logger.warning("Category inference failed: %s", e)
            return None, []
        if category:
            logger.info(
                "Inferred category %r%s for %s with one %s call; pin it with "
                "with_category() for reproducible trends.",
                category,
                f" and competitors {competitors}" if competitors else "",
                self._config.brand,
                provider.value,
            )
        else:
            logger.warning(
                "Category inference returned no usable category: %r", resp.content
            )
        return category, competitors

    @classmethod
    def from_project(
        cls,
        ref: str,
        *,
        kind: str | None = None,
        infer: bool = False,
        http: Callable[[str, dict[str, str]], HttpResponse] | None = None,
        cache: bool = True,
    ) -> Beacon:
        """Create a Beacon for an open-source project or package.

        Reads public metadata (GitHub repository, PyPI or npm package — see
        :mod:`promptbeacon.projects`), then sets the brand (project name),
        developer-oriented prompts, a category guessed offline from the
        description and topics, and competitor candidates the README compares
        itself to. Inspect ``beacon.project`` to see the guesses; override
        them with :meth:`with_category` / :meth:`with_competitors`.

        Args:
            ref: ``"github:owner/name"``, ``"pypi:package"``, ``"npm:package"``,
                or a bare ref together with ``kind``.
            kind: Source kind when ``ref`` has no ``kind:`` prefix.
            infer: Refine the category (and competitors, if none were found)
                with one LLM call when the scan runs; the offline guess is the
                fallback, and is used as-is in demo mode.
            http: Optional HTTP getter (tests, proxies).
            cache: Cache metadata responses on disk for a day.

        Raises:
            ProjectMetadataError: If the metadata cannot be fetched.
        """
        from promptbeacon.projects import fetch_project, profile_project

        meta = fetch_project(ref, kind, http=http, cache=cache)
        profile = profile_project(meta)
        beacon = cls(meta.name).with_industry("developer-tools")
        if meta.aliases:
            beacon = beacon.with_aliases(*meta.aliases)
        if profile.competitors:
            beacon = beacon.with_competitors(*profile.competitors)
        guess = profile.category.category
        if infer:
            beacon = beacon.with_category_inference(hints=meta.hints())
            beacon._fallback_category = guess
        elif guess:
            beacon = beacon.with_category(guess)
        beacon.project = profile
        return beacon

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
        await self._prepare_categories()
        results, total_cost = await self._collect_results()
        total_cost += self._extra_cost
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

        await self._prepare_categories()
        all_runs: list[list[ProviderResult]] = []
        total_cost = self._extra_cost
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

        prompts, _ = self._prompt_plan()
        if not prompts:
            raise ConfigurationError(
                "No prompts generated. Check categories configuration."
            )

        async def run_provider(
            provider: Provider,
        ) -> list[ProviderResult | BaseException]:
            client = self._make_client(provider, variation=variation)
            # Each provider gets its own concurrency limit, so providers run in
            # parallel without exceeding any single provider's rate limit.
            semaphore = asyncio.Semaphore(self._config.concurrent_requests)

            async def query(prompt: str) -> ProviderResult:
                async with semaphore:
                    return await self._query_provider(
                        client, prompt, use_cache=use_cache
                    )

            return await asyncio.gather(
                *[query(p) for p in prompts], return_exceptions=True
            )

        per_provider = await asyncio.gather(
            *[run_provider(p) for p in providers_to_use]
        )

        results: list[ProviderResult] = []
        total_cost = 0.0
        for provider_results in per_provider:  # provider order is preserved
            for result in provider_results:
                if isinstance(result, ProviderResult):
                    results.append(result)
                    if result.cost_usd:
                        total_cost += result.cost_usd
                elif isinstance(result, BaseException):
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

        prompt_strategy = self._prompt_plan()[1]
        categories = (
            list(self._config.categories)
            if prompt_strategy in ("category", "inferred_category")
            else []
        )
        scan_duration = time.time() - start_time
        return Report(
            brand=self._config.brand,
            categories=categories,
            prompt_strategy=prompt_strategy,
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
            measurement_tier=self._measurement_tier(results),
            timestamp=datetime.utcnow(),
            scan_duration_seconds=round(scan_duration, 2),
            total_cost_usd=round(total_cost, 6) if total_cost > 0 else None,
            cost_status=self._cost_status(results, total_cost),
        )

    def _cost_status(
        self, results: list[ProviderResult], total_cost: float
    ) -> Literal["complete", "partial", "unknown", "none"]:
        """How complete the cost estimate is (never a silent $0)."""
        if self._demo_mode:
            return "none"
        paid = [r for r in results if r.success and not r.cached]
        if not paid:
            return "none"
        priced = [r for r in paid if r.cost_usd is not None]
        if not priced:
            return "unknown"
        if len(priced) < len(paid) or any(not r.search_fees_included for r in paid):
            return "partial"
        return "complete" if total_cost > 0 else "unknown"

    def _measurement_tier(
        self, results: list[ProviderResult]
    ) -> Literal["demo", "base_model", "api_grounded"]:
        """How this scan was measured (drives the honesty label on the report).

        Truthful: ``api_grounded`` only when web-grounded queries actually ran.
        If grounding was requested but every provider fell back to base
        completion, the tier stays ``base_model``.
        """
        if self._demo_mode:
            return "demo"
        if any(r.grounded for r in results):
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

    async def _query_provider_grounded(
        self, gclient: GroundedClient, prompt: str
    ) -> ProviderResult:
        """Query a provider's native web search and build a grounded result."""
        resp = await gclient.complete_grounded(
            prompt, max_tokens=self._config.max_tokens
        )
        extraction = extract_mentions(
            resp.content,
            self._config.brand,
            self._config.competitors,
            aliases=self._config.brand_aliases or None,
        )
        brands = (
            [self._config.brand]
            + (self._config.brand_aliases or [])
            + (self._config.competitors or [])
        )
        citations = associate_brands(resp.citations, brands)
        return ProviderResult(
            provider=resp.provider,
            model=resp.model,
            prompt=prompt,
            response=resp.content,
            mentions=extraction.mentions,
            citations=citations,
            latency_ms=resp.latency_ms,
            cost_usd=resp.cost_usd,
            grounded=True,
            search_count=resp.search_count,
            search_fees_included=resp.search_fees_included,
            timestamp=datetime.utcnow(),
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
        # Web-grounded path: provider-native web search via the official SDK.
        # Falls back to the base-model path on any failure or unsupported provider.
        if self._grounded and not self._demo_mode:
            try:
                provider: Provider | None = Provider(client.provider_name)
            except ValueError:
                provider = None
            gclient = get_grounded_client(provider) if provider else None
            if gclient is not None and gclient.is_available():
                try:
                    return await self._query_provider_grounded(gclient, prompt)
                except Exception as e:  # noqa: BLE001 — any failure falls back to base
                    logger.warning(
                        "Grounded query failed for %s, falling back to base: %s",
                        client.provider_name,
                        e,
                    )

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
                cached=cached_content is not None,
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
