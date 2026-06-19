# PromptBeacon Documentation

PromptBeacon is the **open-source GEO engine to measure, track, and CI-test how AI (ChatGPT, Claude, Gemini) recommends your brand.**

> **Does AI recommend your brand?** `pip install promptbeacon`, zero keys to start.

## What is PromptBeacon?

PromptBeacon gives developers, GEO/SEO agencies, and AI/eval engineers a production-grade toolkit to measure and improve brand visibility across large language models. As AI assistants replace traditional search for product discovery, knowing how they represent your brand is essential — and now measurable.

> **The AI visibility space is dominated by $29-490+/month SaaS tools.**
> PromptBeacon is the **only open-source alternative** — free, local-first, and extensible.

## Zero-Key Quick Start

No API keys needed to see what PromptBeacon can do:

```bash
pip install promptbeacon
promptbeacon demo "Nike"
```

Or in Python:

```python
from promptbeacon import Beacon

report = Beacon("Nike").demo().scan()
print(f"Visibility: {report.visibility_score}/100")
print(f"Share of Voice: {report.share_of_voice.target_share:.0%}")
```

The demo mode returns realistic canned data so you can explore the full report structure — including Share of Voice, stability, and CI assertions — without spending a cent.

## Key Features

### v1.1 Highlights — measure real AI search
- **Web-grounded scanning** — `--grounded` queries each provider's **native web search** (OpenAI, Anthropic, Gemini, Perplexity) and captures the **real cited sources**; every report carries an honest `measurement_tier` (`demo` / `base_model` / `api_grounded`).
- **Source attribution** — rank the source **domains** AI cites for your category, and which cite you (`promptbeacon sources`).
- **Glass-box funnel** — `promptbeacon funnel` models the agentic-search funnel (fan-out → retrieve → rerank → cite) and shows **where your brand drops out**.
- **Distribution-grade rigor** — percentile-bootstrap confidence intervals, per-source stability across runs, buyer-intent prompt sets, and pinned **`--protocol`** runs for reproducible CI trends.

### v1.0 Highlights
- **Keyless demo mode** — explore the full API with no setup (`Beacon("Nike").demo().scan()` or `promptbeacon demo "Nike"`)
- **Share of Voice** — quantify your brand's share of AI mindshare vs. competitors
- **Stability scanning** — measure how consistently AI mentions your brand across repeated runs
- **CI-native testing** — `report.assert_visibility(...)`, pytest plugin, and GitHub Action to gate deploys on brand health
- **HTML dashboard** — `to_dashboard_html(report)` generates a single self-contained visual report
- **Smart mode** — opt-in LLM extraction and evidence-linked recommendations (`--smart`)

### Core capabilities
- **Beacon**: Fluent measurement API — scan any brand across 6 LLM providers
- **BeaconGuard**: Real-time brand safety for LLM outputs — flag competitors, negative sentiment, anti-recommendations. No API calls, pure local processing.
- **LangChain Integration**: Callback handler + output parser for LangChain pipelines (optional dependency)
- **6 LLM Providers**: Query OpenAI, Anthropic, Google, Mistral, Cohere, and Perplexity simultaneously
- **Source Attribution**: Rank the source domains AI cites for your category — and which cite you (`promptbeacon sources`)
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
- **CLI Interface**: Full command-line support for automation including quick scans and dashboards
- **Export Formats**: JSON, CSV, Markdown, HTML dashboard, pandas DataFrame

## Quick Links

### Getting Started
- [Quickstart Guide](quickstart.md) - Get up and running in minutes (keyless demo first)
- [Installation](quickstart.md#installation)
- [First Scan](quickstart.md#your-first-real-scan)

### Core Documentation
- [API Reference](api-reference.md) - Complete API documentation
- [CLI Reference](cli.md) - Command-line interface guide
- [Provider Configuration](providers.md) - Setup for all 6 providers
- [Storage Guide](storage.md) - Historical tracking with DuckDB

### Advanced Usage
- [Advanced Patterns](advanced.md) - Stability, smart mode, CI/CD gating, async, custom analysis
- [Examples](examples.md) - Keyless demo, SoV comparison, stability scan, CI testing, dashboards

### Hosted Documentation
Full documentation is also available at [https://yotambraun.github.io/promptbeacon/](https://yotambraun.github.io/promptbeacon/).

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

- **Beacon**: Main interface with fluent configuration API; includes `.demo()`, `.with_stability()`, `.with_smart_extraction()`, `.with_smart_recommendations()`
- **BeaconGuard**: Real-time brand safety analysis for LLM outputs
- **Providers**: Multi-provider LLM access via LiteLLM (OpenAI, Anthropic, Google, Mistral, Cohere, Perplexity)
- **Extraction**: Brand mention detection, sentiment analysis, citation tracking; optional LLM-powered smart extraction
- **Integrations**: LangChain callback handler/output parser, generic middleware
- **Storage**: Local-first DuckDB storage for historical data, file-based response caching
- **Analysis**: Visibility scoring, Share of Voice computation, stability analysis, competitor comparison
- **Reporting**: Export to JSON, CSV, Markdown, HTML dashboard, pandas; `assert_visibility()` for CI gating

## Installation

```bash
pip install promptbeacon
```

With [uv](https://github.com/astral-sh/uv) (recommended):

```bash
uv add promptbeacon
```

## Simple Example (Keyless Demo)

```python
from promptbeacon import Beacon

report = Beacon("Nike").demo().scan()
print(f"Visibility: {report.visibility_score}/100")
print(f"Share of Voice: {report.share_of_voice.target_share:.0%}")
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

# Share of Voice
sov = report.share_of_voice
print(f"SoV: {sov.target_share:.0%} | Presence: {sov.target_presence_rate:.0%} | Rank: {sov.target_rank}")

# Competitor comparison
for name, score in report.competitor_comparison.items():
    print(f"{name}: {score.visibility_score:.1f}")

# CI assertion — raises VisibilityAssertionError if thresholds not met
report.assert_visibility(min_score=40, min_share_of_voice=0.15)
```

## Use Cases

### Developers & AI/Eval Engineers
- Gate deploys on brand visibility with `assert_visibility()` or the GitHub Action
- Track GEO metrics in CI with the pytest plugin
- Integrate brand safety into LLM pipelines via BeaconGuard

### GEO/SEO Agencies
- Benchmark client brands vs. competitors across 6 AI providers
- Produce self-contained HTML dashboards for client reporting
- Automate weekly scans and trend analysis

### Brand Managers
- Track brand visibility across AI platforms
- Monitor sentiment trends over time
- Identify areas for improvement with evidence-linked recommendations

### Marketing Teams
- Measure impact of PR campaigns on AI visibility
- Understand how AI describes your products
- Track competitor positioning

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
   (demo mode: return canned data, no network calls)
4. Query multiple LLM providers concurrently
5. Extract brand mentions with sentiment + citations
   (smart mode: LLM-powered extraction with structured output)
6. Calculate visibility scores with configurable weights
7. Compute Share of Voice across all brands mentioned
8. Run stability analysis if .with_stability(N) was set
9. Generate evidence-based explanations and recommendations
10. Store results in DuckDB (if enabled)
11. Export to desired format; assert CI thresholds if configured
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
- **Documentation**: [https://yotambraun.github.io/promptbeacon/](https://yotambraun.github.io/promptbeacon/)
- **Examples**: See [examples.md](examples.md)

## License

PromptBeacon is released under the Apache License 2.0. See [LICENSE](../LICENSE) for details.

## Next Steps

- [Get Started with the Quickstart Guide](quickstart.md)
- [Explore the API Reference](api-reference.md)
- [Set Up Provider Configuration](providers.md)
- [Learn About Historical Tracking](storage.md)
- [Advanced: CI/CD, Stability, Smart Mode](advanced.md)
