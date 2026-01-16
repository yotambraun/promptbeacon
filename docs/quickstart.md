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
- At least one LLM provider API key (OpenAI, Anthropic, or Google)

## Provider Setup

PromptBeacon needs API keys to query LLM providers. Set up at least one:

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

### Verify Setup

Check which providers are configured:

```bash
promptbeacon providers
```

## Your First Scan

### Basic Scan (Python)

```python
from promptbeacon import Beacon

# Create a beacon for your brand
beacon = Beacon("Nike")

# Run the scan
report = beacon.scan()

# View results
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

### Mention Count

Total number of times your brand was mentioned across all queries to all providers.

### Sentiment Breakdown

Distribution of positive, neutral, and negative mentions:

```python
print(f"Positive: {report.sentiment_breakdown.positive:.0%}")
print(f"Neutral: {report.sentiment_breakdown.neutral:.0%}")
print(f"Negative: {report.sentiment_breakdown.negative:.0%}")
```

## Adding Competitors

Compare your brand against competitors:

```python
from promptbeacon import Beacon

beacon = (
    Beacon("Nike")
    .with_competitors("Adidas", "Puma", "New Balance")
)

report = beacon.scan()

# Compare scores
print(f"{report.brand}: {report.visibility_score:.1f}")
for name, score in report.competitor_comparison.items():
    print(f"{name}: {score.visibility_score:.1f}")
```

### CLI Version

```bash
promptbeacon compare "Nike" --against "Adidas" --against "Puma"
```

## Customizing Your Scan

### Multiple Providers

Query multiple LLM providers for comprehensive coverage:

```python
from promptbeacon import Beacon, Provider

beacon = (
    Beacon("Nike")
    .with_providers(Provider.OPENAI, Provider.ANTHROPIC, Provider.GOOGLE)
)

report = beacon.scan()
print(f"Providers used: {', '.join(report.providers_used)}")
```

### Categories

Analyze specific categories or topics:

```python
beacon = (
    Beacon("Nike")
    .with_categories("running shoes", "athletic wear", "sports brand")
)

report = beacon.scan()
```

### Prompt Count

Control how many prompts to use per category:

```python
beacon = (
    Beacon("Nike")
    .with_prompt_count(20)  # Default is 10
)

report = beacon.scan()
```

## Complete Example

Here's a comprehensive scan combining all options:

```python
from promptbeacon import Beacon, Provider

beacon = (
    Beacon("Nike")
    .with_competitors("Adidas", "Puma")
    .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
    .with_categories("running shoes", "athletic wear")
    .with_prompt_count(15)
)

report = beacon.scan()

# Display results
print(f"\nVisibility Report for {report.brand}")
print(f"{'='*50}")
print(f"Score: {report.visibility_score:.1f}/100")
print(f"Mentions: {report.mention_count}")
print(f"Positive: {report.sentiment_breakdown.positive:.0%}")

print(f"\nCompetitor Comparison:")
for name, score in report.competitor_comparison.items():
    diff = report.visibility_score - score.visibility_score
    symbol = "+" if diff >= 0 else ""
    print(f"  {name}: {score.visibility_score:.1f} ({symbol}{diff:.1f})")

print(f"\nTop Insights:")
for exp in report.explanations[:3]:
    print(f"  [{exp.impact.upper()}] {exp.message}")
```

## Enabling Historical Tracking

Store scan results for trend analysis:

```python
from promptbeacon import Beacon

beacon = (
    Beacon("Nike")
    .with_storage("~/.promptbeacon/nike.db")
)

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

## Common Patterns

### Daily Brand Monitoring

```python
from promptbeacon import Beacon

def daily_scan(brand: str):
    """Run a daily brand visibility scan."""
    beacon = (
        Beacon(brand)
        .with_storage("~/.promptbeacon/data.db")
        .with_prompt_count(20)
    )

    report = beacon.scan()

    # Check for significant changes
    comparison = beacon.compare_with_previous()
    if comparison and abs(comparison.score_change) > 5:
        print(f"ALERT: Score changed by {comparison.score_change:+.1f} points")

    return report

# Schedule this to run daily
report = daily_scan("Nike")
```

### Competitive Analysis

```python
from promptbeacon import Beacon, Provider

def competitive_analysis(brand: str, competitors: list[str]):
    """Run comprehensive competitive analysis."""
    beacon = (
        Beacon(brand)
        .with_competitors(*competitors)
        .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
        .with_categories("product quality", "customer service", "value")
        .with_prompt_count(25)
    )

    report = beacon.scan()

    # Find market leader
    all_scores = [(brand, report.visibility_score)]
    all_scores.extend([
        (name, score.visibility_score)
        for name, score in report.competitor_comparison.items()
    ])

    leader = max(all_scores, key=lambda x: x[1])
    print(f"Market Leader: {leader[0]} ({leader[1]:.1f})")

    return report

report = competitive_analysis(
    "Nike",
    ["Adidas", "Puma", "New Balance", "Under Armour"]
)
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

**Solution**: Reduce concurrent requests:

```python
beacon = (
    Beacon("Nike")
    .with_prompt_count(5)  # Reduce from default 10
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
- [Configure multiple providers](providers.md)
- [Set up historical tracking](storage.md)
- [Check out advanced patterns](advanced.md)
- [See real-world examples](examples.md)

## Quick Reference

### Essential Methods

```python
# Configuration
Beacon(brand)
.with_competitors(*brands)
.with_providers(*providers)
.with_categories(*topics)
.with_prompt_count(n)
.with_storage(path)
.with_temperature(t)
.with_timeout(seconds)

# Execution
.scan()              # Sync scan
.scan_async()        # Async scan

# History
.get_history(days)
.compare_with_previous()
```

### Essential CLI Commands

```bash
promptbeacon scan "Brand"
promptbeacon compare "Brand" --against "Competitor"
promptbeacon history "Brand" --days 30
promptbeacon providers
```

### Essential Exports

```python
from promptbeacon import to_json, to_csv, to_markdown, to_dataframe

to_json(report)
to_csv(report)
to_markdown(report)
to_dataframe(report)
```
