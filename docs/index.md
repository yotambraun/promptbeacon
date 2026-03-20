# PromptBeacon Documentation

Welcome to PromptBeacon - the open-source Generative Engine Optimization (GEO) toolkit for Python. Track how AI sees your brand across ChatGPT, Claude, Gemini, Mistral, and more.

## What is PromptBeacon?

PromptBeacon helps brands understand and track their visibility in the AI ecosystem. As large language models become the new search engines, knowing how AI assistants represent your brand is crucial for modern brand management.

> **The AI visibility space is dominated by $99-300+/month SaaS tools.**
> PromptBeacon is the **only open-source alternative** — free, local-first, and extensible.

## Key Features

- **BeaconGuard**: Real-time brand safety for LLM outputs — flag competitors, negative sentiment, anti-recommendations. No API calls, pure local processing.
- **LangChain Integration**: Callback handler + output parser for LangChain pipelines (optional dependency)
- **6 LLM Providers**: Query OpenAI, Anthropic, Google, Mistral, Cohere, and Perplexity simultaneously
- **Citation Tracking**: See which sources LLMs cite when discussing your brand
- **Brand Aliases**: "Nike Inc", "Nike Corporation" all count as Nike mentions
- **Industry Templates**: Pre-built prompts for ecommerce, SaaS, finance, healthcare, travel, food, tech
- **Response Caching**: Skip identical queries with file-based caching (configurable TTL)
- **Score Breakdown**: See which of the 4 scoring factors drags your score
- **Visibility Scoring**: Quantifiable metrics (0-100) measuring brand prominence in AI responses
- **Sentiment Analysis**: Track positive, neutral, and negative mentions with negation detection
- **Competitor Benchmarking**: Compare your visibility against competitors
- **Historical Tracking**: DuckDB-powered local storage for trend analysis
- **Explainable Insights**: Understand why scores change with evidence-backed explanations
- **Statistical Rigor**: Confidence intervals, volatility scoring, and significance testing
- **Fluent API**: Chainable, readable Python interface
- **CLI Interface**: Full command-line support for automation including quick scans
- **Export Formats**: JSON, CSV, Markdown, HTML, pandas DataFrame

## Quick Links

### Getting Started
- [Quickstart Guide](quickstart.md) - Get up and running in 5 minutes
- [Installation](quickstart.md#installation)
- [First Scan](quickstart.md#your-first-scan)

### Core Documentation
- [API Reference](api-reference.md) - Complete API documentation
- [CLI Reference](cli.md) - Command-line interface guide
- [Provider Configuration](providers.md) - Setup for all 6 providers
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
- **BeaconGuard**: Real-time brand safety analysis for LLM outputs
- **Providers**: Multi-provider LLM access via LiteLLM (OpenAI, Anthropic, Google, Mistral, Cohere, Perplexity)
- **Extraction**: Brand mention detection, sentiment analysis, citation tracking
- **Integrations**: LangChain callback handler/output parser, generic middleware
- **Storage**: Local-first DuckDB storage for historical data, file-based response caching
- **Analysis**: Visibility scoring with configurable weights, competitor comparison
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

report = Beacon("Nike").scan()
print(f"Visibility: {report.visibility_score}/100")
print(f"Mentions: {report.mention_count}")
print(f"Sentiment: {report.sentiment_breakdown.positive:.0%} positive")
```

## Advanced Example

```python
from promptbeacon import Beacon, Provider

report = (
    Beacon("Nike")
    .with_aliases("Nike Inc", "Nike Corporation")
    .with_competitors("Adidas", "Puma", "New Balance")
    .with_providers(Provider.OPENAI, Provider.ANTHROPIC, Provider.GOOGLE)
    .with_industry("ecommerce")
    .with_cache()
    .with_storage("~/.promptbeacon/nike.db")
    .scan()
)

# Score with factor breakdown
print(f"Score: {report.visibility_score}/100")
bd = report.metrics.score_breakdown
print(f"  Mentions: {bd.mention_frequency:.0f}  Sentiment: {bd.sentiment:.0f}")
print(f"  Position: {bd.position:.0f}  Recommendations: {bd.recommendation:.0f}")

# Competitor comparison
for name, score in report.competitor_comparison.items():
    print(f"{name}: {score.visibility_score:.1f}")

# Citations the LLM used
for cit in report.citation_summary.citations[:5]:
    print(f"  Source: {cit.source_name} -> {cit.brand_associated}")

# Evidence-based recommendations
for rec in report.recommendations[:3]:
    print(f"[{rec.priority.upper()}] {rec.action}")
```

## Use Cases

### Brand Safety for AI Apps
- Ensure customer-facing chatbots don't recommend competitors
- Flag negative sentiment or anti-recommendations in real time
- Integrate with LangChain or any LLM pipeline via middleware
- No API calls required — pure local processing

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
1. Configure Beacon with brand, aliases, competitors, categories
2. Generate prompts from templates (or industry-specific templates)
3. Check response cache; skip queries with cached responses
4. Query multiple LLM providers concurrently
5. Extract brand mentions with sentiment + citations
6. Calculate visibility scores with configurable weights
7. Generate evidence-based explanations and recommendations
8. Store results in DuckDB (if enabled)
9. Export to desired format
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

PromptBeacon is released under the Apache License 2.0. See [LICENSE](../LICENSE) for details.

## Next Steps

- [Get Started with the Quickstart Guide](quickstart.md)
- [Explore the API Reference](api-reference.md)
- [Set Up Provider Configuration](providers.md)
- [Learn About Historical Tracking](storage.md)
