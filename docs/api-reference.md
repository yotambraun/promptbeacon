# API Reference

Complete API documentation for PromptBeacon v1.0. This reference covers all classes, methods, and data structures.

## Table of Contents

- [Beacon Class](#beacon-class)
- [BeaconGuard](#beaconguard)
- [Configuration](#configuration)
- [Report Objects](#report-objects)
- [Data Schemas](#data-schemas)
- [Share of Voice](#share-of-voice)
- [Source Attribution](#source-attribution)
- [Agentic Funnel](#agentic-funnel)
- [Stability](#stability)
- [Export Functions](#export-functions)
- [Integrations](#integrations)
- [Exceptions](#exceptions)
- [Provider Enum](#provider)

---

## Beacon Class

The main interface for brand visibility monitoring.

### Constructor

```python
Beacon(brand: str)
```

Creates a new Beacon instance for monitoring a brand.

**Parameters:**
- `brand` (str): The brand name to monitor (required, min length: 1)

**Returns:** Beacon instance

**Example:**
```python
from promptbeacon import Beacon

beacon = Beacon("Nike")
```

---

### Configuration Methods

All configuration methods return `self` for method chaining.

#### `demo() -> Beacon`

Enable keyless demo mode. Returns realistic canned data without making any API calls. No provider keys are required. This is the recommended first-run experience.

**Returns:** Self for chaining

**Example:**
```python
report = Beacon("Nike").demo().scan()
print(report.visibility_score)  # realistic canned value
```

The `--demo` CLI flag is equivalent:
```bash
promptbeacon scan "Nike" --demo
promptbeacon quick "Nike" --demo
promptbeacon dashboard "Nike" --demo -o report.html
```

---

#### `with_aliases(*aliases: str) -> Beacon`

Add alternative brand names that should be counted as the primary brand.

**Parameters:**
- `*aliases` (str): One or more alternative brand names

**Returns:** Self for chaining

**Example:**
```python
beacon = Beacon("Nike").with_aliases("Nike Inc", "Nike Corporation")
```

---

#### `with_competitors(*competitors: str) -> Beacon`

Add competitor brands to track alongside your brand.

**Parameters:**
- `*competitors` (str): One or more competitor brand names

**Returns:** Self for chaining

**Example:**
```python
beacon = Beacon("Nike").with_competitors("Adidas", "Puma")

# Or pass as list
competitors = ["Adidas", "Puma", "New Balance"]
beacon = Beacon("Nike").with_competitors(*competitors)
```

---

#### `with_providers(*providers: Provider) -> Beacon`

Set which LLM providers to query.

**Parameters:**
- `*providers` (Provider): One or more Provider enum values

**Returns:** Self for chaining

**Default:** `[Provider.OPENAI]`

**Example:**
```python
from promptbeacon import Beacon, Provider

beacon = Beacon("Nike").with_providers(
    Provider.OPENAI,
    Provider.ANTHROPIC,
    Provider.GOOGLE
)
```

---

#### `with_categories(*categories: str) -> Beacon`

Set the categories or topics to analyze.

**Parameters:**
- `*categories` (str): One or more category/topic names

**Returns:** Self for chaining

**Default:** `["general"]`

**Example:**
```python
beacon = Beacon("Nike").with_categories(
    "running shoes",
    "athletic wear",
    "sports brand"
)
```

---

#### `with_prompt_count(count: int) -> Beacon`

Set the number of prompts to use per category.

**Parameters:**
- `count` (int): Number of prompts (1-1000)

**Returns:** Self for chaining

**Default:** `10`

**Example:**
```python
beacon = Beacon("Nike").with_prompt_count(25)
```

---

#### `with_storage(path: str | Path) -> Beacon`

Enable DuckDB storage for historical tracking.

**Parameters:**
- `path` (str | Path): Path to DuckDB file (will be created if doesn't exist)

**Returns:** Self for chaining

**Default:** `None` (no storage)

**Example:**
```python
from pathlib import Path

# Using string path
beacon = Beacon("Nike").with_storage("~/.promptbeacon/data.db")

# Using Path object
beacon = Beacon("Nike").with_storage(Path.home() / ".promptbeacon" / "data.db")
```

---

#### `with_temperature(temperature: float) -> Beacon`

Set the temperature for LLM queries.

**Parameters:**
- `temperature` (float): Temperature value (0.0-2.0)

**Returns:** Self for chaining

**Default:** `0.7`

**Note:** Stability scanning requires a non-zero temperature to produce meaningful variance across runs. Using `temperature=0.0` with `.with_stability()` will produce identical results per run.

**Example:**
```python
beacon = Beacon("Nike").with_temperature(0.5)
```

---

#### `with_max_tokens(max_tokens: int) -> Beacon`

Set the maximum tokens for LLM responses.

**Parameters:**
- `max_tokens` (int): Maximum tokens (1-32768)

**Returns:** Self for chaining

**Default:** `1024`

**Example:**
```python
beacon = Beacon("Nike").with_max_tokens(2048)
```

---

#### `with_timeout(timeout: float) -> Beacon`

Set the request timeout in seconds.

**Parameters:**
- `timeout` (float): Timeout in seconds (minimum: 1.0)

**Returns:** Self for chaining

**Default:** `30.0`

**Example:**
```python
beacon = Beacon("Nike").with_timeout(60.0)
```

---

#### `with_industry(industry: str) -> Beacon`

Use industry-specific prompt templates instead of defaults.

**Parameters:**
- `industry` (str): Industry name. Available: `ecommerce`, `saas`, `finance`, `healthcare`, `travel`, `food`, `tech`

**Returns:** Self for chaining

**Raises:**
- `ValueError`: If the industry is not recognized

**Example:**
```python
beacon = Beacon("Nike").with_industry("ecommerce")
```

---

#### `with_cache(cache_dir: str | Path | None = None, ttl_seconds: int = 86400) -> Beacon`

Enable file-based response caching. Cached responses are keyed by (prompt, provider, model).

**Parameters:**
- `cache_dir` (str | Path | None): Cache directory (default: `~/.promptbeacon/cache`)
- `ttl_seconds` (int): Cache time-to-live in seconds (default: 86400 = 24 hours)

**Returns:** Self for chaining

**Example:**
```python
# Default cache (24h TTL)
beacon = Beacon("Nike").with_cache()

# Custom cache directory and 1-hour TTL
beacon = Beacon("Nike").with_cache(cache_dir="/tmp/pb_cache", ttl_seconds=3600)
```

---

#### `with_scoring_weights(mention_frequency: float = 0.3, sentiment: float = 0.25, position: float = 0.25, recommendation: float = 0.2) -> Beacon`

Customize the four scoring factor weights. Weights must sum to 1.0.

**Parameters:**
- `mention_frequency` (float): Weight for mention frequency (default: 0.3)
- `sentiment` (float): Weight for sentiment (default: 0.25)
- `position` (float): Weight for position/prominence (default: 0.25)
- `recommendation` (float): Weight for recommendation rate (default: 0.2)

**Returns:** Self for chaining

**Example:**
```python
# Weight sentiment more heavily
beacon = Beacon("Nike").with_scoring_weights(
    mention_frequency=0.2,
    sentiment=0.4,
    position=0.2,
    recommendation=0.2,
)
```

---

#### `with_prompts(prompts: list[str]) -> Beacon`

Use fully custom prompts instead of defaults. Use `{category}` as a placeholder.

**Parameters:**
- `prompts` (list[str]): List of prompt templates

**Returns:** Self for chaining

**Example:**
```python
custom_prompts = [
    "What is the best {category} brand?",
    "Can you recommend a {category} company?",
    "Which {category} should I buy?"
]

beacon = Beacon("Nike").with_prompts(custom_prompts)
```

---

#### `with_stability(runs: int) -> Beacon`

Configure stability scanning. When set, `.scan_stability()` runs the full scan `runs` times and computes a `StabilityReport` measuring how consistently AI mentions your brand.

**Parameters:**
- `runs` (int): Number of scan repetitions (typically 3-10)

**Returns:** Self for chaining

**Warning:** Multiplies API calls (and cost) by `runs`. Bypasses the response cache (each run must be fresh). Requires a non-zero temperature to produce meaningful variance.

**Example:**
```python
report = Beacon("Nike").with_stability(5).scan_stability()
print(f"Stability: {report.stability.stability_score}/100")
print(f"Rating: {report.stability.volatility.stability_rating}")  # stable/moderate/volatile
```

CLI equivalent:
```bash
promptbeacon scan "Nike" --stability 5
# short form:
promptbeacon scan "Nike" -r 5
```

---

#### `with_smart_extraction(model: str | None = None) -> Beacon`

Enable LLM-powered mention extraction and sentiment analysis instead of regex-based extraction. Uses structured output for higher accuracy on complex or ambiguous responses.

**Parameters:**
- `model` (str | None): Model to use for extraction (default: provider's default)

**Returns:** Self for chaining

**Notes:**
- Opt-in; adds one extra LLM call per provider result
- Falls back to regex extraction on error
- Not used in demo mode
- Requires at least one provider API key

**Example:**
```python
report = Beacon("Nike").with_smart_extraction().scan()
```

---

#### `with_smart_recommendations() -> Beacon`

Enable LLM-powered recommendation generation. Produces evidence-linked, prioritized recommendations based on scan results.

**Returns:** Self for chaining

**Notes:**
- Opt-in; adds one extra LLM call
- Falls back to rule-based recommendations on error
- Not used in demo mode

**Example:**
```python
report = Beacon("Nike").with_smart_recommendations().scan()
for rec in report.recommendations:
    print(f"[{rec.priority.upper()}] {rec.action}")
    print(f"  Evidence: {rec.rationale}")
```

CLI equivalent (enables both smart extraction and smart recommendations):
```bash
promptbeacon scan "Nike" --smart
```

---

#### `with_grounding(enabled: bool = True) -> Beacon`

Measure **web-grounded** answers — what AI *search* returns — instead of base-model memory. Enables the provider's native web-search tool (via its official SDK) and captures the real cited sources. The report is tagged `measurement_tier="api_grounded"` when grounding actually runs.

**Parameters:**
- `enabled` (bool): Whether to enable web-grounded scanning (default: True)

**Returns:** Self for chaining

**Notes:**
- Requires the `[grounded]` extra: `pip install 'promptbeacon[grounded]'`
- Covered: OpenAI (Responses `web_search`), Anthropic (Brave-backed web search), Gemini (Google Search grounding), and Perplexity (sonar) — set the matching provider key. Mistral/Cohere fall back to base completion, and the scan stays labelled `base_model`.
- Costs more per scan (search fees + tokens), billed to your own keys. No effect in demo mode.
- The provider API approximates, but does **not** equal, the consumer product (ChatGPT.com etc.).

**Example:**
```python
report = Beacon("Nike").with_grounding().scan()
print(report.measurement_tier)  # "api_grounded" when grounding ran
```

CLI equivalent:
```bash
promptbeacon scan "Nike" --grounded
```

---

### Execution Methods

#### `scan() -> Report`

Run a synchronous visibility scan.

**Returns:** Report object with scan results

**Raises:**
- `ConfigurationError`: No API keys found or invalid configuration (not raised in demo mode)
- `ScanError`: All provider queries failed

**Example:**
```python
beacon = Beacon("Nike")
report = beacon.scan()

print(f"Score: {report.visibility_score}")
```

---

#### `async scan_async() -> Report`

Run an asynchronous visibility scan (recommended for better performance).

**Returns:** Report object with scan results

**Raises:**
- `ConfigurationError`: No API keys found or invalid configuration
- `ScanError`: All provider queries failed

**Example:**
```python
import asyncio
from promptbeacon import Beacon

async def main():
    beacon = Beacon("Nike")
    report = await beacon.scan_async()
    print(f"Score: {report.visibility_score}")

asyncio.run(main())
```

---

#### `scan_stability() -> Report`

Run a synchronous stability scan. Requires `.with_stability(n)` to be called first. Runs the full scan `n` times and populates `report.stability` with a `StabilityReport`.

**Returns:** Report object (with `report.stability` populated)

**Raises:**
- `ConfigurationError`: Storage not configured or no API keys
- `ScanError`: All provider queries failed

**Example:**
```python
report = Beacon("Nike").with_stability(5).scan_stability()
print(f"Stability score: {report.stability.stability_score}/100")
print(f"Flip-flop count: {report.stability.flip_flop_count}")
```

---

#### `async scan_stability_async() -> Report`

Asynchronous version of `scan_stability()`.

**Example:**
```python
import asyncio
from promptbeacon import Beacon

async def main():
    report = await Beacon("Nike").with_stability(5).scan_stability_async()
    print(f"Stability: {report.stability.stability_score}/100")

asyncio.run(main())
```

---

### History Methods

#### `get_history(days: int = 30) -> HistoryReport`

Retrieve historical visibility data.

**Parameters:**
- `days` (int): Number of days of history to retrieve (default: 30)

**Returns:** HistoryReport object

**Raises:**
- `ConfigurationError`: Storage not configured

**Example:**
```python
beacon = Beacon("Nike").with_storage("~/.promptbeacon/data.db")
beacon.scan()  # Run at least one scan first

history = beacon.get_history(days=30)
print(f"Trend: {history.trend_direction}")  # up, down, or stable
print(f"Average: {history.average_score:.1f}")
```

---

#### `compare_with_previous() -> ScanComparison | None`

Compare the latest scan with the previous one.

**Returns:** ScanComparison object or None if no previous scan exists

**Raises:**
- `ConfigurationError`: Storage not configured

**Example:**
```python
beacon = Beacon("Nike").with_storage("~/.promptbeacon/data.db")
report = beacon.scan()

comparison = beacon.compare_with_previous()
if comparison:
    print(f"Change: {comparison.score_change:+.1f} points")
    print(f"Direction: {comparison.change_direction}")
```

---

### Utility Methods

#### `close() -> None`

Close database connections and clean up resources.

**Example:**
```python
beacon = Beacon("Nike").with_storage("data.db")
beacon.scan()
beacon.close()
```

---

#### Context Manager Support

Beacon supports context manager protocol for automatic cleanup.

**Example:**
```python
with Beacon("Nike").with_storage("data.db") as beacon:
    report = beacon.scan()
    # Database automatically closed when exiting context
```

---

### Properties

#### `brand -> str`

The brand being monitored (read-only).

```python
beacon = Beacon("Nike")
print(beacon.brand)  # "Nike"
```

---

#### `config -> BeaconConfig`

The current configuration (read-only).

```python
beacon = Beacon("Nike").with_competitors("Adidas")
print(beacon.config.competitors)  # ["Adidas"]
```

---

## BeaconGuard

Real-time brand safety analysis for LLM outputs. No API calls, pure local processing.

### Constructor

```python
BeaconGuard(
    brand: str,
    competitors: list[str] | None = None,
    aliases: list[str] | None = None,
    *,
    flag_competitor_mention: bool = True,
    flag_negative_sentiment: bool = True,
    flag_no_brand_mention: bool = False,
    flag_anti_recommendation: bool = True,
)
```

**Parameters:**
- `brand` (str): The brand to protect
- `competitors` (list[str] | None): Competitor brand names to flag
- `aliases` (list[str] | None): Alternative brand names (credited to primary)
- `flag_competitor_mention` (bool): Flag when competitors are mentioned (default: True)
- `flag_negative_sentiment` (bool): Flag negative sentiment (default: True)
- `flag_no_brand_mention` (bool): Flag when brand is absent (default: False)
- `flag_anti_recommendation` (bool): Flag anti-recommendations (default: True)

**Example:**
```python
from promptbeacon import BeaconGuard

guard = BeaconGuard(
    "Nike",
    competitors=["Adidas", "Puma"],
    aliases=["Nike Inc"],
    flag_no_brand_mention=True,
)
```

---

### `analyze(text: str) -> GuardResult`

Analyze text for brand safety concerns.

**Parameters:**
- `text` (str): The LLM output text to analyze

**Returns:** GuardResult with analysis details

**Example:**
```python
result = guard.analyze("Try Adidas instead of Nike.")
print(result.risk_level)     # "high"
print(result.flags)          # ["Competitor mentioned: Adidas"]
print(result.sentiment)      # "neutral"
```

---

### GuardResult

Pydantic model returned by `BeaconGuard.analyze()`.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `text` | str | Input text analyzed |
| `mentions_brand` | bool | Target brand was found |
| `mentions_competitor` | bool | Any competitor was found |
| `competitor_names` | list[str] | Which competitors were found |
| `sentiment` | "positive" \| "neutral" \| "negative" | Overall sentiment |
| `sentiment_details` | SentimentAnalysisResult | Full sentiment breakdown |
| `has_citations` | bool | Whether citations were found |
| `citations` | list[Citation] | Citations found in text |
| `is_recommendation` | bool | Brand explicitly recommended |
| `is_anti_recommendation` | bool | Brand explicitly warned against |
| `risk_level` | "low" \| "medium" \| "high" | Risk level (0 flags=low, 1=medium, 2+=high) |
| `flags` | list[str] | Human-readable triggered rules |

---

## Configuration

### BeaconConfig

Configuration dataclass for Beacon instances.

**Attributes:**

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `brand` | str | required | Brand to monitor |
| `competitors` | list[str] | [] | Competitor brands |
| `providers` | list[Provider] | [Provider.OPENAI] | LLM providers |
| `categories` | list[str] | ["general"] | Analysis categories |
| `prompt_count` | int | 10 | Prompts per category (1-1000) |
| `storage_path` | Path \| None | None | DuckDB file path |
| `temperature` | float | 0.7 | LLM temperature (0.0-2.0) |
| `max_tokens` | int | 1024 | Max response tokens (1-32768) |
| `timeout` | float | 30.0 | Request timeout (seconds) |
| `max_retries` | int | 3 | Max retry attempts (0-10) |
| `concurrent_requests` | int | 5 | Concurrent requests (1-50) |

---

### Provider

Enum of supported LLM providers.

**Values:**
- `Provider.OPENAI` - OpenAI (GPT models)
- `Provider.ANTHROPIC` - Anthropic (Claude models)
- `Provider.GOOGLE` - Google (Gemini models)
- `Provider.MISTRAL` - Mistral AI
- `Provider.COHERE` - Cohere
- `Provider.PERPLEXITY` - Perplexity AI

**Default Models:**
| Provider | Model |
|----------|-------|
| OPENAI | gpt-4o-mini |
| ANTHROPIC | claude-haiku-4-5 |
| GOOGLE | gemini-2.0-flash |
| MISTRAL | mistral-small-latest |
| COHERE | command-r |
| PERPLEXITY | sonar |

**Example:**
```python
from promptbeacon import Provider

# Use all providers
beacon = Beacon("Nike").with_providers(*Provider.all())

# Check provider availability
from promptbeacon.core.config import has_api_key

if has_api_key(Provider.OPENAI):
    print("OpenAI is configured")
```

---

## Report Objects

### Report

Main report object containing scan results.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `brand` | str | Brand analyzed |
| `visibility_score` | float | Overall score (0-100) |
| `mention_count` | int | Total mentions |
| `sentiment_breakdown` | SentimentBreakdown | Sentiment distribution |
| `competitor_comparison` | dict[str, CompetitorScore] | Competitor scores |
| `provider_results` | list[ProviderResult] | Raw provider responses |
| `metrics` | VisibilityMetrics | Detailed metrics |
| `explanations` | list[Explanation] | Insight explanations |
| `recommendations` | list[Recommendation] | Actionable recommendations |
| `citation_summary` | CitationSummary | Aggregated citations from all responses |
| `share_of_voice` | ShareOfVoiceReport | Share of Voice across all brands |
| `stability` | StabilityReport \| None | Stability data (populated by `scan_stability()`) |
| `source_attribution` | SourceAttributionReport \| None | Source domains the engines cite (see [Source Attribution](#source-attribution)) |
| `measurement_tier` | "demo" \| "base_model" \| "api_grounded" | How the scan was measured (honesty label) |
| `timestamp` | datetime | Scan timestamp |
| `scan_duration_seconds` | float | Duration in seconds |
| `total_cost_usd` | float \| None | Estimated API cost |

**Measurement tier** — `demo` (canned data), `base_model` (LLM completion, no web search — training memory), or `api_grounded` (provider web search; approximates but does not equal the consumer product). Surfaced in the CLI banner and JSON.

**Computed Properties:**

- `providers_used` (list[str]): List of providers used
- `success_rate` (float): Rate of successful queries

**Example:**
```python
report = beacon.scan()

print(f"Brand: {report.brand}")
print(f"Score: {report.visibility_score}/100")
print(f"Mentions: {report.mention_count}")
print(f"Duration: {report.scan_duration_seconds:.1f}s")
print(f"Providers: {', '.join(report.providers_used)}")
print(f"Success rate: {report.success_rate:.1%}")

if report.total_cost_usd:
    print(f"Cost: ${report.total_cost_usd:.4f}")

# Share of Voice
sov = report.share_of_voice
print(f"SoV: {sov.target_share:.0%} | Rank: {sov.target_rank}")
```

---

### `assert_visibility(...) -> Report`

Assert that the report meets minimum visibility thresholds. Raises `VisibilityAssertionError` (an `AssertionError` subclass) listing all unmet thresholds. Returns `self` for chaining.

**Parameters** (all optional, omit to skip that check):
- `min_score` (float): Minimum visibility score (0-100)
- `min_share_of_voice` (float): Minimum Share of Voice (0-1)
- `min_presence_rate` (float): Minimum presence rate (0-1)
- `min_stability_score` (float): Minimum stability score (0-100; requires stability data)
- `max_rank` (int): Maximum acceptable SoV rank (1 = must be the most-mentioned brand)

**Raises:**
- `VisibilityAssertionError`: One or more thresholds were not met (contains list of failures)

**Returns:** Self for chaining

**Example:**
```python
# Raises VisibilityAssertionError if any threshold fails
report.assert_visibility(
    min_score=40,
    min_share_of_voice=0.15,
    max_rank=3,
)

# Chain with export
json_output = report.assert_visibility(min_score=50).to_json()
```

In pytest, use the pytest plugin instead (see [CI/CD section](advanced.md#cicd-gate-deploys-on-ai-visibility)).

---

### HistoryReport

Historical trend data for a brand.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `brand` | str | Brand name |
| `data_points` | list[HistoricalDataPoint] | Historical data |
| `trend_direction` | "up" \| "down" \| "stable" \| None | Trend direction |
| `average_score` | float \| None | Average score (0-100) |
| `volatility` | float \| None | Score volatility (≥0) |

**Computed Properties:**

- `visibility_trend` (list[float]): List of scores over time

---

### ScanComparison

Comparison between two scans.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `brand` | str | Brand name |
| `current_score` | float | Current score (0-100) |
| `previous_score` | float | Previous score (0-100) |
| `score_change` | float | Score delta |
| `current_timestamp` | datetime | Current scan time |
| `previous_timestamp` | datetime | Previous scan time |
| `changes` | list[Explanation] | Change explanations |

**Computed Properties:**

- `change_direction` ("up" | "down" | "stable"): Direction of change

---

## Data Schemas

### BrandMention

Represents a single brand mention.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `brand_name` | str | Brand mentioned |
| `sentiment` | "positive" \| "neutral" \| "negative" | Sentiment |
| `position` | int | Position in response (0-indexed) |
| `context` | str | Surrounding text |
| `confidence` | float | Confidence (0.0-1.0) |
| `is_recommendation` | bool | Explicitly recommended |

---

### ProviderResult

Result from a single provider query.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `provider` | str | Provider name |
| `model` | str | Model used |
| `prompt` | str | Prompt sent |
| `response` | str | Response received |
| `mentions` | list[BrandMention] | Extracted mentions |
| `citations` | list[Citation] | Extracted citations |
| `latency_ms` | float | Response latency (ms) |
| `cost_usd` | float \| None | Estimated cost |
| `error` | str \| None | Error message if failed |
| `grounded` | bool | True if this result came from a web-grounded query (provider web search) |
| `timestamp` | datetime | Query timestamp |

**Computed Properties:**

- `success` (bool): Whether query succeeded
- `mention_count` (int): Number of mentions

---

### SentimentBreakdown

Sentiment distribution across mentions.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `positive` | float | Positive ratio (0.0-1.0) |
| `neutral` | float | Neutral ratio (0.0-1.0) |
| `negative` | float | Negative ratio (0.0-1.0) |

---

### CompetitorScore

Visibility score for a competitor.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `brand_name` | str | Competitor name |
| `visibility_score` | float | Score (0-100) |
| `mention_count` | int | Total mentions |
| `sentiment` | SentimentBreakdown | Sentiment distribution |

---

### VisibilityMetrics

Detailed visibility metrics.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `visibility_score` | float | Overall score (0-100) |
| `mention_count` | int | Total mentions |
| `recommendation_rate` | float | Recommendation rate (0.0-1.0) |
| `average_position` | float \| None | Average mention position |
| `sentiment` | SentimentBreakdown | Sentiment breakdown |
| `confidence_interval` | tuple[float, float] \| None | 95% CI for score |
| `score_breakdown` | ScoreBreakdown \| None | Breakdown of the 4 scoring factors |

---

### ScoreBreakdown

Breakdown of the four factors that compose the visibility score. Each factor is scored 0-100 before weighting.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `mention_frequency` | float | Mention frequency sub-score (0-100) |
| `sentiment` | float | Sentiment sub-score (0-100) |
| `position` | float | Position/prominence sub-score (0-100) |
| `recommendation` | float | Recommendation rate sub-score (0-100) |

---

### Citation

A single citation found in an LLM response.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `url` | str \| None | URL if one was cited |
| `source_name` | str | Name of the cited source (domain for URL citations) |
| `context` | str | Surrounding text where the citation appeared |
| `brand_associated` | str \| None | Brand name nearest to this citation |
| `source_rank` | int \| None | Rank among the engine's retrieved results (grounded mode) |
| `source_type` | str \| None | Classified type (reddit / wikipedia / news / review / ...) |
| `query` | str \| None | The prompt/sub-query that surfaced this citation |
| `retrieved_but_uncited` | bool | Retrieved by the engine but not cited in the answer (grounded/funnel mode) |

---

### CitationSummary

Aggregated citation summary for a report.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `total_citations` | int | Total number of citations found |
| `unique_domains` | list[str] | List of unique domains cited |
| `citations` | list[Citation] | All individual citations |

---

### Explanation

An insight explanation.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `category` | str | Explanation category |
| `message` | str | Human-readable message |
| `evidence` | list[str] | Supporting quotes |
| `impact` | "high" \| "medium" \| "low" | Impact level |

---

### Recommendation

An actionable recommendation.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `action` | str | Recommended action |
| `rationale` | str | Why recommended |
| `priority` | "high" \| "medium" \| "low" | Priority level |
| `expected_impact` | str | Expected impact |

---

### HistoricalDataPoint

A single historical data point.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `timestamp` | datetime | Data point timestamp |
| `visibility_score` | float | Score (0-100) |
| `mention_count` | int | Mentions |
| `sentiment` | SentimentBreakdown | Sentiment |

---

## Share of Voice

Share of Voice (SoV) is computed automatically on every scan. It measures what fraction of all brand mentions across all prompts belongs to each brand.

### `calculate_share_of_voice(results, target, competitors) -> ShareOfVoiceReport`

Standalone function to compute SoV from a list of provider results.

```python
from promptbeacon import calculate_share_of_voice

sov = calculate_share_of_voice(
    results=report.provider_results,
    target="Nike",
    competitors=["Adidas", "Puma"],
)
```

---

### ShareOfVoiceReport

Top-level SoV report, available as `report.share_of_voice`.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `target_share` | float | Target brand's SoV (0-1) |
| `target_presence_rate` | float | Fraction of prompts where target was mentioned (0-1) |
| `target_rank` | int | Target brand's rank (1 = most-mentioned) |
| `aggregate` | dict[str, ShareOfVoiceEntry] | SoV entry per brand |
| `by_provider` | dict[str, ShareOfVoiceReport] | Per-provider breakdown |

**Example:**
```python
sov = report.share_of_voice

print(f"Nike SoV: {sov.target_share:.0%}")
print(f"Nike presence: {sov.target_presence_rate:.0%}")
print(f"Nike rank: #{sov.target_rank}")

for brand, entry in sov.aggregate.items():
    print(f"  {brand}: {entry.share_of_voice:.0%} ({entry.appearances}/{entry.total_prompts} prompts)")
```

---

### ShareOfVoiceEntry

SoV data for a single brand.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `brand_name` | str | Brand name |
| `appearances` | int | Number of prompts the brand appeared in |
| `total_prompts` | int | Total prompts run |
| `presence_rate` | float | appearances / total_prompts (0-1) |
| `share_of_voice` | float | This brand's fraction of all brand mentions (0-1) |

---

## Source Attribution

Every scan aggregates the citations in AI answers by **source domain** so you can see which sites the engines cite for your category — and which cite your brand. Available as `report.source_attribution`.

### `aggregate_source_attribution(results, target_brand, competitors=None) -> SourceAttributionReport`

Standalone function in `promptbeacon.analysis.sources` to compute attribution from provider results.

```python
from promptbeacon.analysis.sources import aggregate_source_attribution

sa = aggregate_source_attribution(report.provider_results, "Nike", ["Adidas"])
```

### SourceAttributionReport

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `target_brand` | str | Brand being analyzed |
| `total_citations` | int | Total citations counted |
| `entries` | list[SourceAttributionEntry] | Domains ranked by citation count (descending) |
| `by_type` | dict[str, int] | Citation counts grouped by source type |

**Computed Properties:**

- `target_cited_domains` (list[str]): Domains whose citations were associated with the target brand

### SourceAttributionEntry

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `domain` | str | Source domain or attribution name |
| `source_type` | str | reddit / wikipedia / news / review / academic / social / video / code / web / attribution |
| `citations` | int | Citations from this source |
| `share` | float | citations / total citations (0-1) |
| `brands_cited` | list[str] | Distinct brands associated with this source |
| `cites_target` | bool | Whether the target brand was associated with this source |

**Example:**
```python
sa = report.source_attribution
print(f"{sa.total_citations} citations across {len(sa.entries)} domains")
for entry in sa.entries[:10]:
    print(f"{entry.domain} ({entry.source_type}): {entry.citations} "
          f"— cites you: {entry.cites_target}")
print(sa.by_type)               # {'reddit': 4, 'news': 2, ...}
print(sa.target_cited_domains)  # ['reddit.com', ...]
```

---

## Agentic Funnel

Glass-box funnel measurement — where a brand survives or drops out of agentic search. In `promptbeacon.funnel`.

### `run_funnel(brand, prompt, *, backend, competitors=None, n_sub_queries=8, retrieve_k=8, top_k=5, cite_k=3) -> FunnelReport`

Async. Fans `prompt` into sub-queries, retrieves per sub-query via `backend`, reranks to `top_k`, "cites" the top `cite_k`, and reports where the brand drops out.

```python
import asyncio
from promptbeacon.funnel import MockSearchBackend, run_funnel

report = asyncio.run(
    run_funnel(
        "Nike",
        "What are the best running shoes?",
        backend=MockSearchBackend("Nike", competitors=["Adidas"]),
        competitors=["Adidas"],
    )
)
```

**Backends** (in `promptbeacon.funnel`): `MockSearchBackend(brand, competitors)` (keyless, deterministic) and `TavilyBackend(api_key)` (live web search via httpx). Both implement the `SearchBackend` interface.

### FunnelReport

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `brand` | str | Target brand |
| `prompt` | str | The prompt that was fanned out |
| `sub_queries` | list[str] | Generated sub-queries |
| `sub_query_results` | list[SubQueryResult] | Per-sub-query funnel detail (retrieved/reranked/cited flags) |
| `sub_query_coverage` | float | Fraction of sub-queries whose retrieval includes the brand |
| `rerank_survival_rate` | float | Of those retrieved, fraction surviving reranking |
| `retrieval_to_citation_ratio` | float | Of those retrieved, fraction surviving to citation |
| `stage_failure` | str | Dominant drop-off: `retrieval` / `rerank` / `citation` / `none` |
| `measurement_tier` | str | Always `funnel_model` (a local model of agentic search) |

---

## Stability

Stability scanning runs the full scan `N` times and measures how consistently AI mentions your brand. Enable with `.with_stability(N)` and run via `.scan_stability()`.

### StabilityReport

Available as `report.stability` after a stability scan.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `stability_score` | float | Overall stability (0-100; 100 = perfectly consistent) |
| `score_confidence_interval` | tuple[float, float] | 95% CI across runs (normal approximation) |
| `score_bootstrap_interval` | tuple[float, float] | 95% percentile-bootstrap CI (distribution-free) |
| `score_per_run` | list[float] | Visibility score for each run |
| `volatility` | VolatilityMetrics | Volatility breakdown |
| `overall_presence_consistency` | float | Fraction of runs where brand appeared (0-1) |
| `flip_flop_count` | int | Number of times brand appeared in one run but not the next |
| `prompt_stability` | list[PromptStability] | Per-prompt stability breakdown |
| `source_stability` | list[SourceStability] | Per-source-domain citation consistency across runs |

**Example:**
```python
report = Beacon("Nike").with_stability(5).scan_stability()
s = report.stability

print(f"Stability score: {s.stability_score:.1f}/100")
lower, upper = s.score_confidence_interval
print(f"95% CI: [{lower:.1f}, {upper:.1f}]")
print(f"Per-run scores: {[f'{x:.1f}' for x in s.score_per_run]}")
print(f"Presence consistency: {s.overall_presence_consistency:.0%}")
print(f"Flip-flops: {s.flip_flop_count}")
print(f"Rating: {s.volatility.stability_rating}")  # stable / moderate / volatile
```

---

### VolatilityMetrics

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `stability_rating` | "stable" \| "moderate" \| "volatile" | Human-readable rating |
| (additional numeric fields) | float | Raw volatility measures |

---

### PromptStability

Per-prompt stability breakdown.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `prompt` | str | The prompt text |
| `presence_rate` | float | Fraction of runs where brand appeared (0-1) |
| `score_variance` | float | Variance of visibility score across runs |

---

### SourceStability

Per-source-domain citation consistency across stability runs.

**Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `domain` | str | Source domain (or attribution name) |
| `runs` | int | Number of repeated runs |
| `appearances` | int | Runs in which this source was cited |
| `presence_rate` | float | appearances / runs (0-1) |
| `flip_flopped` | bool | Cited in some runs but not others |

---

## Protocols & Prompt Sets

### `generate_buyer_intent_prompts(category: str, n: int = 50) -> list[str]`

Generate `n` distinct buyer-intent prompts for a category — the kinds of questions real buyers ask AI when choosing. Use for the recommended 50–200 prompt measurement protocol.

```python
from promptbeacon.prompts.templates import generate_buyer_intent_prompts

prompts = generate_buyer_intent_prompts("running shoes", n=50)
report = Beacon("Nike").with_prompts(prompts).scan()
```

### ScanProtocol

A pinned, reproducible scan configuration (in `promptbeacon.protocol`). Load from JSON with `load_protocol(path)` and build a configured `Beacon` with `build_beacon(protocol)`, so a scan re-runs identically over time.

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `brand` | str | required | Brand to scan |
| `competitors` | list[str] | [] | Competitor brands |
| `providers` | list[str] | [] | Provider names (e.g. `"openai"`) |
| `categories` | list[str] | [] | Categories/topics |
| `prompts` | list[str] | [] | Explicit, pinned prompt set |
| `prompt_count` | int \| None | None | Prompts per category |
| `runs` | int | 0 | Stability runs (0 = single scan) |
| `grounded` | bool | False | Web-grounded scanning |
| `smart` | bool | False | LLM extraction + recommendations |

```python
from promptbeacon.protocol import build_beacon, load_protocol

beacon = build_beacon(load_protocol("nike-protocol.json"))
report = beacon.scan()  # or .scan_stability() when the protocol sets "runs"
```

CLI: `promptbeacon scan --protocol nike-protocol.json`

---

## Export Functions

All export functions accept a Report object and return formatted output.

### `to_json(report: Report) -> str`

Export report as JSON string.

**Example:**
```python
from promptbeacon import to_json

json_output = to_json(report)
with open("report.json", "w") as f:
    f.write(json_output)
```

---

### `to_csv(report: Report) -> str`

Export report as CSV string.

---

### `to_markdown(report: Report) -> str`

Export report as Markdown.

---

### `to_html(report: Report) -> str`

Export report as a basic HTML page.

---

### `to_dashboard_html(report: Report, history: HistoryReport | None = None) -> str`

Export report as a single self-contained HTML dashboard with interactive charts: Share of Voice bar chart, score breakdown, sentiment donut, stability band (if stability data present), and optional history sparkline.

**Parameters:**
- `report` (Report): The scan report
- `history` (HistoryReport | None): Optional historical data to include a sparkline

**Returns:** Self-contained HTML string (no external dependencies)

**Example:**
```python
from promptbeacon import to_dashboard_html

html = to_dashboard_html(report)
with open("dashboard.html", "w") as f:
    f.write(html)
```

CLI equivalent (auto-opens in browser):
```bash
promptbeacon dashboard "Nike" -o report.html
promptbeacon dashboard "Nike" --demo -o demo_report.html
promptbeacon dashboard "Nike" -o report.html --no-open
```

---

### `to_dataframe(report: Report) -> pd.DataFrame`

Export report as pandas DataFrame.

---

### `to_dict(report: Report) -> dict`

Export report as Python dictionary.

---

## Integrations

### BeaconGuardMiddleware

Generic callable middleware for any LLM pipeline.

```python
from promptbeacon import BeaconGuard
from promptbeacon.integrations.middleware import BeaconGuardMiddleware

guard = BeaconGuard("Acme", competitors=["CompetitorX"])
mw = BeaconGuardMiddleware(
    guard,
    on_high_risk=lambda r: print(f"ALERT: {r.flags}"),
)

result = mw("Try CompetitorX instead of Acme.")
```

---

### LangChain Integration

Requires `langchain-core`: `pip install 'promptbeacon[langchain]'`

#### BeaconGuardCallbackHandler

LangChain callback handler that runs BeaconGuard on LLM outputs.

```python
from promptbeacon import BeaconGuard
from promptbeacon.integrations.langchain import BeaconGuardCallbackHandler

guard = BeaconGuard("Acme", competitors=["CompetitorX"])
handler = BeaconGuardCallbackHandler(guard, on_high_risk=lambda r: alert(r))
# Pass to your chain's callbacks
```

#### BeaconGuardOutputParser

LangChain output parser that returns `GuardResult`.

```python
from promptbeacon.integrations.langchain import BeaconGuardOutputParser

parser = BeaconGuardOutputParser(guard=guard)
# Use in a chain: chain | parser
```

---

## Exceptions

All PromptBeacon exceptions inherit from `PromptBeaconError`.

### Exception Hierarchy

```
PromptBeaconError
├── ConfigurationError
├── ValidationError
├── ProviderError
│   ├── ProviderAuthenticationError
│   ├── ProviderRateLimitError
│   └── ProviderAPIError
├── ExtractionError
├── ScanError
├── StorageError
└── VisibilityAssertionError  (also subclasses AssertionError)
```

### Exception Details

#### `PromptBeaconError`

Base exception for all PromptBeacon errors.

---

#### `ConfigurationError`

Raised for configuration errors (missing API keys, invalid config).

**Example:**
```python
try:
    beacon = Beacon("Nike")
    report = beacon.scan()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    # Use demo mode as fallback
    report = Beacon("Nike").demo().scan()
```

---

#### `ValidationError`

Raised for validation errors (invalid parameters).

---

#### `ProviderError`

Base exception for provider-related errors.

---

#### `ProviderAuthenticationError`

Raised when API key authentication fails.

---

#### `ProviderRateLimitError`

Raised when rate limit is exceeded.

---

#### `ProviderAPIError`

Raised for general API errors.

**Attributes:**
- `status_code` (int | None): HTTP status code if available

---

#### `ExtractionError`

Raised when mention extraction fails.

---

#### `ScanError`

Raised when scan execution fails.

---

#### `StorageError`

Raised for database/storage errors.

---

#### `VisibilityAssertionError`

Raised by `report.assert_visibility(...)` when one or more thresholds are not met. Subclasses `AssertionError` so it integrates naturally with pytest and `assert` statements.

**Attributes:**
- `failures` (list[str]): Human-readable list of unmet thresholds

**Example:**
```python
from promptbeacon.core.exceptions import VisibilityAssertionError

try:
    report.assert_visibility(min_score=70, min_share_of_voice=0.3)
except VisibilityAssertionError as e:
    print(f"CI check failed:")
    for failure in e.failures:
        print(f"  - {failure}")
    sys.exit(1)
```

---

## Type Hints

PromptBeacon is fully type-hinted. Use with type checkers like mypy:

```python
from promptbeacon import Beacon, Report, Provider

beacon: Beacon = Beacon("Nike")
report: Report = beacon.scan()
score: float = report.visibility_score
```

---

## Version Information

```python
from promptbeacon import __version__

print(__version__)  # e.g., "1.1.0"
```

---

## Full Example

```python
from promptbeacon import Beacon, Provider, to_json, to_dashboard_html, to_dataframe
from promptbeacon.core.exceptions import ConfigurationError, ScanError, VisibilityAssertionError

try:
    # Configure beacon with full options
    beacon = (
        Beacon("Nike")
        .with_aliases("Nike Inc", "Nike Corporation")
        .with_competitors("Adidas", "Puma", "New Balance")
        .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
        .with_industry("ecommerce")
        .with_cache()
        .with_storage("~/.promptbeacon/nike.db")
        .with_temperature(0.7)
        .with_timeout(60.0)
    )

    # Run scan
    report = beacon.scan()

    # Access results
    print(f"Visibility: {report.visibility_score:.1f}/100")
    print(f"Mentions: {report.mention_count}")
    print(f"Sentiment: {report.sentiment_breakdown.positive:.0%} positive")

    # Share of Voice
    sov = report.share_of_voice
    print(f"SoV: {sov.target_share:.0%} (rank #{sov.target_rank})")

    # Competitor comparison
    for name, score in report.competitor_comparison.items():
        print(f"{name}: {score.visibility_score:.1f}")

    # Score breakdown
    bd = report.metrics.score_breakdown
    print(f"Mentions: {bd.mention_frequency:.0f}  Sentiment: {bd.sentiment:.0f}")

    # Citations
    for cit in report.citation_summary.citations[:5]:
        print(f"  {cit.source_name} -> {cit.brand_associated}")

    # Recommendations
    for rec in report.recommendations[:3]:
        print(f"[{rec.priority}] {rec.action}")

    # CI assertion
    report.assert_visibility(min_score=40, min_share_of_voice=0.1)

    # Export
    json_output = to_json(report)
    html = to_dashboard_html(report)
    df = to_dataframe(report)

    # Historical analysis
    history = beacon.get_history(days=30)
    print(f"Trend: {history.trend_direction}")

    comparison = beacon.compare_with_previous()
    if comparison:
        print(f"Change: {comparison.score_change:+.1f} points")

except ConfigurationError as e:
    print(f"Configuration error: {e}")
except ScanError as e:
    print(f"Scan failed: {e}")
except VisibilityAssertionError as e:
    print(f"Visibility check failed: {e.failures}")
finally:
    beacon.close()
```
