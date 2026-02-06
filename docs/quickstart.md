# Quickstart Guide

Get started with PromptBeacon in less than 5 minutes. This guide will walk you through installation, setup, and your first brand visibility scan.

## Installation

### Using pip

```bash
pip install promptbeacon
```

### Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package manager. If you're using uv:

```bash
uv add promptbeacon
```

### Requirements

- Python 3.10 or higher
- At least one LLM provider API key

## Provider Setup

PromptBeacon supports 6 LLM providers. Set up at least one:

### OpenAI

```bash
export OPENAI_API_KEY="sk-..."
```

Get your key from [platform.openai.com](https://platform.openai.com/api-keys)

### Anthropic

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Get your key from [console.anthropic.com](https://console.anthropic.com/settings/keys)

### Google (Gemini)

```bash
export GOOGLE_API_KEY="..."
```

Get your key from [aistudio.google.com](https://aistudio.google.com/app/apikey)

### Mistral

```bash
export MISTRAL_API_KEY="..."
```

Get your key from [console.mistral.ai](https://console.mistral.ai/api-keys)

### Cohere

```bash
export COHERE_API_KEY="..."
```

Get your key from [dashboard.cohere.com](https://dashboard.cohere.com/api-keys)

### Perplexity

```bash
export PERPLEXITY_API_KEY="pplx-..."
```

Get your key from [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api)

### Verify Setup

Check which providers are configured:

```bash
promptbeacon providers
```

## Your First Scan

### Quick Scan (CLI)

The fastest way to check brand visibility:

```bash
promptbeacon quick "Nike"
```

### Basic Scan (Python)

```python
from promptbeacon import Beacon

report = Beacon("Nike").scan()
print(f"Visibility Score: {report.visibility_score}/100")
print(f"Total Mentions: {report.mention_count}")
print(f"Positive Sentiment: {report.sentiment_breakdown.positive:.0%}")
```

### Basic Scan (CLI)

```bash
promptbeacon scan "Nike"
```

That's it! You've just completed your first brand visibility scan.

## Understanding Your Results

### Visibility Score

The visibility score (0-100) measures how prominently your brand appears in AI responses:

- **70-100**: Excellent visibility - frequently mentioned and recommended
- **40-69**: Moderate visibility - mentioned but not always prominently
- **0-39**: Low visibility - rarely mentioned or recommended

### Score Breakdown

See which factors drive your score:

```python
bd = report.metrics.score_breakdown
print(f"Mention Frequency: {bd.mention_frequency:.0f}/100")
print(f"Sentiment: {bd.sentiment:.0f}/100")
print(f"Position: {bd.position:.0f}/100")
print(f"Recommendation: {bd.recommendation:.0f}/100")
```

### Mention Count

Total number of times your brand was mentioned across all queries to all providers.

### Sentiment Breakdown

Distribution of positive, neutral, and negative mentions:

```python
print(f"Positive: {report.sentiment_breakdown.positive:.0%}")
print(f"Neutral: {report.sentiment_breakdown.neutral:.0%}")
print(f"Negative: {report.sentiment_breakdown.negative:.0%}")
```

### Citations

See which sources LLMs cite when discussing your brand:

```python
for cit in report.citation_summary.citations[:5]:
    print(f"Source: {cit.source_name} -> {cit.brand_associated}")
```

## Adding Competitors

Compare your brand against competitors:

```python
from promptbeacon import Beacon

report = (
    Beacon("Nike")
    .with_competitors("Adidas", "Puma", "New Balance")
    .scan()
)

print(f"{report.brand}: {report.visibility_score:.1f}")
for name, score in report.competitor_comparison.items():
    print(f"{name}: {score.visibility_score:.1f}")
```

### CLI Version

```bash
promptbeacon compare "Nike" --against "Adidas" --against "Puma"
```

## Brand Aliases

Count all name variants as the same brand:

```python
report = (
    Beacon("Nike")
    .with_aliases("Nike Inc", "Nike Corporation")
    .scan()
)
```

## Industry Templates

Use pre-built prompts tuned for your industry:

```python
report = (
    Beacon("Nike")
    .with_industry("ecommerce")  # ecommerce, saas, finance, healthcare, travel, food, tech
    .scan()
)
```

## Customizing Your Scan

### Multiple Providers

Query multiple LLM providers for comprehensive coverage:

```python
from promptbeacon import Beacon, Provider

report = (
    Beacon("Nike")
    .with_providers(Provider.OPENAI, Provider.ANTHROPIC, Provider.GOOGLE)
    .scan()
)
print(f"Providers used: {', '.join(report.providers_used)}")
```

### Response Caching

Skip duplicate queries to save time and money:

```python
report = (
    Beacon("Nike")
    .with_cache()  # Default 24h TTL
    .scan()
)
```

### Categories

Analyze specific categories or topics:

```python
report = (
    Beacon("Nike")
    .with_categories("running shoes", "athletic wear", "sports brand")
    .scan()
)
```

## Complete Example

Here's a comprehensive scan combining all options:

```python
from promptbeacon import Beacon, Provider

report = (
    Beacon("Nike")
    .with_aliases("Nike Inc", "Nike Corporation")
    .with_competitors("Adidas", "Puma")
    .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
    .with_industry("ecommerce")
    .with_cache()
    .scan()
)

# Score with breakdown
print(f"\nVisibility Report for {report.brand}")
print(f"{'='*50}")
print(f"Score: {report.visibility_score:.1f}/100")

bd = report.metrics.score_breakdown
print(f"  Mentions: {bd.mention_frequency:.0f}  Sentiment: {bd.sentiment:.0f}")
print(f"  Position: {bd.position:.0f}  Recommendations: {bd.recommendation:.0f}")

# Competitors
print(f"\nCompetitor Comparison:")
for name, score in report.competitor_comparison.items():
    diff = report.visibility_score - score.visibility_score
    print(f"  {name}: {score.visibility_score:.1f} ({diff:+.1f})")

# Citations
if report.citation_summary.total_citations > 0:
    print(f"\nSources Cited ({report.citation_summary.total_citations}):")
    for cit in report.citation_summary.citations[:5]:
        print(f"  {cit.source_name} -> {cit.brand_associated}")

# Insights
print(f"\nTop Insights:")
for exp in report.explanations[:3]:
    print(f"  [{exp.impact.upper()}] {exp.message}")
```

## Enabling Historical Tracking

Store scan results for trend analysis:

```python
from promptbeacon import Beacon

beacon = Beacon("Nike").with_storage("~/.promptbeacon/nike.db")

# This scan will be automatically saved
report = beacon.scan()

# View historical data
history = beacon.get_history(days=30)
print(f"Trend: {history.trend_direction}")  # up, down, or stable

# Compare with previous scan
comparison = beacon.compare_with_previous()
if comparison:
    print(f"Score change: {comparison.score_change:+.1f} points")
```

See the [Storage Guide](storage.md) for more details.

## Exporting Results

### JSON Export

```python
from promptbeacon import to_json

json_output = to_json(report)
with open("nike_report.json", "w") as f:
    f.write(json_output)
```

### CSV Export

```python
from promptbeacon import to_csv

csv_output = to_csv(report)
with open("nike_report.csv", "w") as f:
    f.write(csv_output)
```

### Markdown Export

```python
from promptbeacon import to_markdown

markdown = to_markdown(report)
print(markdown)
```

### pandas DataFrame

```python
from promptbeacon import to_dataframe

df = to_dataframe(report)
print(df.head())
```

### CLI Export

```bash
# JSON
promptbeacon scan "Nike" --format json > nike.json

# Markdown
promptbeacon scan "Nike" --format markdown > nike.md
```

## Async Usage

For better performance when making multiple scans:

```python
import asyncio
from promptbeacon import Beacon

async def scan_multiple_brands():
    brands = ["Nike", "Adidas", "Puma"]
    beacons = [Beacon(brand) for brand in brands]

    # Run scans concurrently
    reports = await asyncio.gather(*[
        beacon.scan_async() for beacon in beacons
    ])

    for report in reports:
        print(f"{report.brand}: {report.visibility_score:.1f}")

asyncio.run(scan_multiple_brands())
```

## Troubleshooting

### No API Keys Found

**Error**: `ConfigurationError: No API keys found for configured providers`

**Solution**: Set environment variables for at least one provider:

```bash
export OPENAI_API_KEY="sk-..."
# OR
export ANTHROPIC_API_KEY="sk-ant-..."
# OR
export GOOGLE_API_KEY="..."
```

### Rate Limiting

**Error**: `ProviderRateLimitError: Rate limit exceeded`

**Solution**: Enable caching and reduce prompts:

```python
beacon = (
    Beacon("Nike")
    .with_cache()            # Don't repeat queries
    .with_prompt_count(5)    # Reduce from default 10
)
```

### Timeout Errors

**Error**: `Request timeout`

**Solution**: Increase timeout:

```python
beacon = (
    Beacon("Nike")
    .with_timeout(60.0)  # Default is 30.0 seconds
)
```

## Next Steps

- [Explore the complete API Reference](api-reference.md)
- [Learn about CLI commands](cli.md)
- [Configure all 6 providers](providers.md)
- [Set up historical tracking](storage.md)
- [Check out advanced patterns](advanced.md)
- [See real-world examples](examples.md)

## Quick Reference

### Essential Methods

```python
# Configuration
Beacon(brand)
.with_aliases(*names)          # Alternative brand names
.with_competitors(*brands)     # Competitor brands
.with_providers(*providers)    # LLM providers
.with_industry(name)           # Industry prompt templates
.with_categories(*topics)      # Custom categories
.with_prompt_count(n)          # Prompts per category
.with_cache(ttl_seconds=...)   # Response caching
.with_storage(path)            # DuckDB storage
.with_scoring_weights(...)     # Custom score weights
.with_temperature(t)           # LLM temperature
.with_timeout(seconds)         # Request timeout
.with_prompts(list)            # Fully custom prompts

# Execution
.scan()              # Sync scan
.scan_async()        # Async scan

# History
.get_history(days)
.compare_with_previous()
```

### Essential CLI Commands

```bash
promptbeacon quick "Brand"                           # Fast 3-prompt scan
promptbeacon scan "Brand"                            # Full scan
promptbeacon compare "Brand" --against "Competitor"  # Compare brands
promptbeacon history "Brand" --days 30               # View trends
promptbeacon providers                               # Check API keys
```

### Essential Exports

```python
from promptbeacon import to_json, to_csv, to_markdown, to_html, to_dataframe

to_json(report)
to_csv(report)
to_markdown(report)
to_html(report)
to_dataframe(report)
```
