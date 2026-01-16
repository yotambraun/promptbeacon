# PromptBeacon Documentation

Welcome to PromptBeacon - a comprehensive toolkit for monitoring how your brand appears in AI-generated responses across multiple LLM providers.

## What is PromptBeacon?

PromptBeacon helps brands understand and track their visibility in the AI ecosystem. As large language models become the new search engines, knowing how AI assistants represent your brand is crucial for modern brand management.

## Key Features

- **Visibility Scoring**: Quantifiable metrics (0-100) measuring brand prominence in AI responses
- **Multi-Provider Support**: Query OpenAI, Anthropic, and Google simultaneously
- **Sentiment Analysis**: Track positive, neutral, and negative mentions
- **Competitor Benchmarking**: Compare your visibility against competitors
- **Historical Tracking**: DuckDB-powered local storage for trend analysis
- **Explainable Insights**: Understand why scores change with evidence-backed explanations
- **Statistical Rigor**: Confidence intervals, volatility scoring, and significance testing
- **Fluent API**: Chainable, readable Python interface
- **CLI Interface**: Full command-line support for automation
- **Export Formats**: JSON, CSV, Markdown, HTML, pandas DataFrame

## Quick Links

### Getting Started
- [Quickstart Guide](quickstart.md) - Get up and running in 5 minutes
- [Installation](quickstart.md#installation)
- [First Scan](quickstart.md#your-first-scan)

### Core Documentation
- [API Reference](api-reference.md) - Complete API documentation
- [CLI Reference](cli.md) - Command-line interface guide
- [Provider Configuration](providers.md) - Setup for OpenAI, Anthropic, Google
- [Storage Guide](storage.md) - Historical tracking with DuckDB

### Advanced Usage
- [Advanced Patterns](advanced.md) - Custom prompts, async, advanced analysis
- [Examples](examples.md) - Real-world usage patterns

## Architecture Overview

PromptBeacon is built on a modular architecture:

```
┌─────────────┐
│   Beacon    │  Fluent API for configuration
└──────┬──────┘
       │
       ├─────────────┐
       │             │
┌──────▼──────┐ ┌───▼────────┐
│  Providers  │ │  Storage   │
│  (LiteLLM)  │ │  (DuckDB)  │
└──────┬──────┘ └───┬────────┘
       │            │
       ├────────────┤
       │            │
┌──────▼──────┐ ┌──▼─────────┐
│  Analysis   │ │ Reporting  │
│  & Scoring  │ │  Formats   │
└─────────────┘ └────────────┘
```

### Components

- **Beacon**: Main interface with fluent configuration API
- **Providers**: Multi-provider LLM access via LiteLLM (OpenAI, Anthropic, Google)
- **Storage**: Local-first DuckDB storage for historical data
- **Analysis**: Visibility scoring, sentiment analysis, competitor comparison
- **Reporting**: Export to JSON, CSV, Markdown, HTML, pandas

## Installation

```bash
pip install promptbeacon
```

With [uv](https://github.com/astral-sh/uv) (recommended):

```bash
uv add promptbeacon
```

## Simple Example

```python
from promptbeacon import Beacon

# Basic scan
beacon = Beacon("Nike")
report = beacon.scan()

print(f"Visibility: {report.visibility_score}/100")
print(f"Mentions: {report.mention_count}")
print(f"Sentiment: {report.sentiment_breakdown.positive:.0%} positive")
```

## Advanced Example

```python
from promptbeacon import Beacon, Provider

# Comprehensive competitive analysis
beacon = (
    Beacon("Nike")
    .with_competitors("Adidas", "Puma", "New Balance")
    .with_providers(Provider.OPENAI, Provider.ANTHROPIC, Provider.GOOGLE)
    .with_categories("running shoes", "athletic wear", "sustainability")
    .with_prompt_count(25)
    .with_storage("~/.promptbeacon/nike.db")
)

report = beacon.scan()

# Compare against competitors
print(f"\n{report.brand}: {report.visibility_score:.1f}")
for name, score in report.competitor_comparison.items():
    diff = report.visibility_score - score.visibility_score
    print(f"{name}: {score.visibility_score:.1f} ({diff:+.1f})")

# Get actionable insights
print("\nKey Recommendations:")
for rec in report.recommendations[:3]:
    print(f"  [{rec.priority.upper()}] {rec.action}")
```

## Use Cases

### Brand Managers
- Track brand visibility across AI platforms
- Monitor sentiment trends over time
- Identify areas for improvement
- Benchmark against competitors

### Marketing Teams
- Measure impact of PR campaigns on AI visibility
- Understand how AI describes your products
- Track competitor positioning
- Generate reports for stakeholders

### Product Teams
- Monitor product mention rates
- Track feature visibility in AI responses
- Understand user perception through AI lens
- Identify gaps in AI knowledge

### Agencies
- Multi-brand monitoring dashboards
- Competitive intelligence gathering
- Campaign effectiveness measurement
- Client reporting automation

## Why Local-First?

PromptBeacon stores all data locally using DuckDB:

- **Privacy**: Your competitive intelligence stays on your machine
- **Speed**: Fast queries without network overhead
- **Cost**: No cloud storage fees
- **Control**: Full ownership of your data
- **Portability**: Single file database, easy to backup and share

## Data Flow

```
1. Configure Beacon with brand, competitors, categories
2. Generate prompts from templates and categories
3. Query multiple LLM providers concurrently
4. Extract brand mentions with sentiment
5. Calculate visibility scores and metrics
6. Generate explanations and recommendations
7. Store results in DuckDB (if enabled)
8. Export to desired format
```

## Philosophy

PromptBeacon is built on three core principles:

1. **Measurement Over Guesswork**: Quantifiable metrics backed by statistical rigor
2. **Explainability Over Black Boxes**: Every score comes with evidence and explanations
3. **Local-First Over Cloud**: Your competitive data belongs to you

## Contributing

We welcome contributions! See the [GitHub repository](https://github.com/yotambraun/promptbeacon) for contribution guidelines.

## Support

- **Issues**: [GitHub Issues](https://github.com/yotambraun/promptbeacon/issues)
- **Documentation**: You're reading it!
- **Examples**: See [examples.md](examples.md)

## License

PromptBeacon is released under the MIT License. See [LICENSE](../LICENSE) for details.

## Next Steps

- [Get Started with the Quickstart Guide](quickstart.md)
- [Explore the API Reference](api-reference.md)
- [Set Up Provider Configuration](providers.md)
- [Learn About Historical Tracking](storage.md)
