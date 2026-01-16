# API Reference

Complete API documentation for PromptBeacon. This reference covers all classes, methods, and data structures.

## Table of Contents

- [Beacon Class](#beacon-class)
- [Configuration](#configuration)
- [Report Objects](#report-objects)
- [Data Schemas](#data-schemas)
- [Export Functions](#export-functions)
- [Exceptions](#exceptions)
- [Provider Enum](#provider-enum)

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

#### `with_prompts(prompts: list[str]) -> Beacon`

Use custom prompts instead of defaults. Use `{category}` as a placeholder.

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

### Execution Methods

#### `scan() -> Report`

Run a synchronous visibility scan.

**Returns:** Report object with scan results

**Raises:**
- `ConfigurationError`: No API keys found or invalid configuration
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

**Default Models:**
| Provider | Model |
|----------|-------|
| OPENAI | gpt-4o-mini |
| ANTHROPIC | claude-3-haiku-20240307 |
| GOOGLE | gemini-1.5-flash |

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
| `timestamp` | datetime | Scan timestamp |
| `scan_duration_seconds` | float | Duration in seconds |
| `total_cost_usd` | float \| None | Estimated API cost |

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
```

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

**Example:**
```python
history = beacon.get_history(days=30)

print(f"Trend: {history.trend_direction}")
print(f"Average: {history.average_score:.1f}")
print(f"Volatility: {history.volatility:.2f}")
print(f"Data points: {len(history.data_points)}")
```

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

**Example:**
```python
comparison = beacon.compare_with_previous()

if comparison:
    print(f"Current: {comparison.current_score:.1f}")
    print(f"Previous: {comparison.previous_score:.1f}")
    print(f"Change: {comparison.score_change:+.1f}")
    print(f"Direction: {comparison.change_direction}")
```

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
| `latency_ms` | float | Response latency (ms) |
| `cost_usd` | float \| None | Estimated cost |
| `error` | str \| None | Error message if failed |
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

**Example:**
```python
sentiment = report.sentiment_breakdown

print(f"Positive: {sentiment.positive:.0%}")
print(f"Neutral: {sentiment.neutral:.0%}")
print(f"Negative: {sentiment.negative:.0%}")
```

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

**Example:**
```python
metrics = report.metrics

print(f"Score: {metrics.visibility_score:.1f}")
print(f"Rec. rate: {metrics.recommendation_rate:.0%}")

if metrics.average_position:
    print(f"Avg. position: {metrics.average_position:.1f}")

if metrics.confidence_interval:
    lower, upper = metrics.confidence_interval
    print(f"95% CI: [{lower:.1f}, {upper:.1f}]")
```

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

**Example:**
```python
for exp in report.explanations:
    print(f"[{exp.impact.upper()}] {exp.message}")
    for quote in exp.evidence:
        print(f"  - {quote}")
```

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

**Example:**
```python
for rec in report.recommendations:
    print(f"[{rec.priority.upper()}] {rec.action}")
    print(f"  Why: {rec.rationale}")
    print(f"  Impact: {rec.expected_impact}")
```

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

## Export Functions

All export functions accept a Report object and return formatted output.

### `to_json(report: Report) -> str`

Export report as JSON string.

**Example:**
```python
from promptbeacon import to_json

json_output = to_json(report)
print(json_output)

# Save to file
with open("report.json", "w") as f:
    f.write(json_output)
```

---

### `to_csv(report: Report) -> str`

Export report as CSV string.

**Example:**
```python
from promptbeacon import to_csv

csv_output = to_csv(report)

with open("report.csv", "w") as f:
    f.write(csv_output)
```

---

### `to_markdown(report: Report) -> str`

Export report as Markdown.

**Example:**
```python
from promptbeacon import to_markdown

markdown = to_markdown(report)
print(markdown)

with open("report.md", "w") as f:
    f.write(markdown)
```

---

### `to_html(report: Report) -> str`

Export report as HTML page.

**Example:**
```python
from promptbeacon import to_html

html = to_html(report)

with open("report.html", "w") as f:
    f.write(html)
```

---

### `to_dataframe(report: Report) -> pd.DataFrame`

Export report as pandas DataFrame.

**Example:**
```python
from promptbeacon import to_dataframe

df = to_dataframe(report)
print(df.head())

# Analysis with pandas
print(df.groupby('provider')['visibility_score'].mean())
```

---

### `to_dict(report: Report) -> dict`

Export report as Python dictionary.

**Example:**
```python
from promptbeacon import to_dict

data = to_dict(report)
print(data['visibility_score'])
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
└── StorageError
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

**Example:**
```python
try:
    report = beacon.scan()
except ProviderAuthenticationError as e:
    print(f"Authentication failed: {e}")
    print("Check your API key")
```

---

#### `ProviderRateLimitError`

Raised when rate limit is exceeded.

**Example:**
```python
try:
    report = beacon.scan()
except ProviderRateLimitError as e:
    print(f"Rate limit exceeded: {e}")
    print("Reduce prompt_count or wait before retrying")
```

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

print(__version__)  # e.g., "0.1.0"
```

---

## Full Example

```python
from promptbeacon import Beacon, Provider, to_json, to_dataframe
from promptbeacon.core.exceptions import ConfigurationError, ScanError

try:
    # Configure beacon with full options
    beacon = (
        Beacon("Nike")
        .with_competitors("Adidas", "Puma", "New Balance")
        .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
        .with_categories("running shoes", "athletic wear", "sports brand")
        .with_prompt_count(20)
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

    # Competitor comparison
    for name, score in report.competitor_comparison.items():
        print(f"{name}: {score.visibility_score:.1f}")

    # Insights
    for exp in report.explanations[:3]:
        print(f"[{exp.impact}] {exp.message}")

    # Recommendations
    for rec in report.recommendations[:3]:
        print(f"[{rec.priority}] {rec.action}")

    # Export
    json_output = to_json(report)
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
finally:
    beacon.close()
```
