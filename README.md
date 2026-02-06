# PromptBeacon

**The open-source Generative Engine Optimization (GEO) toolkit for Python.**
Track how AI sees your brand across ChatGPT, Claude, Gemini, Mistral, and more.

[![PyPI version](https://badge.fury.io/py/promptbeacon.svg)](https://badge.fury.io/py/promptbeacon)
[![Downloads](https://static.pepy.tech/badge/promptbeacon)](https://pepy.tech/project/promptbeacon)
[![CI](https://github.com/yotambraun/promptbeacon/actions/workflows/ci.yml/badge.svg)](https://github.com/yotambraun/promptbeacon/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![codecov](https://codecov.io/gh/yotambraun/promptbeacon/branch/main/graph/badge.svg)](https://codecov.io/gh/yotambraun/promptbeacon)

---

> **The AI visibility space is dominated by $99-300+/month SaaS tools.**
> PromptBeacon is the **only open-source alternative** — free, local-first, and extensible.

## What It Does

```
Prompt: "What are the best running shoe brands?"

     ChatGPT                    Claude                     Gemini
        |                         |                          |
        v                         v                          v
  "Nike is a top              "I'd recommend             "Popular brands
   choice for..."              Nike and..."               include Nike..."
        |                         |                          |
        +------------+------------+------------+-------------+
                     |
              PromptBeacon
                     |
     +---------------+----------------+
     |               |                |
  Visibility    Sentiment         Citations
  Score: 78/100  82% positive    nike.com (3x)
                                 runnersworld.com
```

**Three lines of code. Six providers. One score.**

```python
from promptbeacon import Beacon

report = Beacon("Nike").scan()
print(f"Visibility: {report.visibility_score}/100")  # 78.3
```

## Why PromptBeacon?

As AI assistants replace search engines, your brand's AI visibility is your new SEO.
PromptBeacon answers the questions that matter:

- **"How visible is my brand?"** — 0-100 score based on mention frequency, sentiment, position, and recommendation rate
- **"What do LLMs say about me?"** — Sentiment analysis with negation detection ("not great" = negative)
- **"How do I compare to competitors?"** — Side-by-side benchmarking across providers
- **"Why did my score change?"** — Evidence-based explanations with actual quotes from LLM responses
- **"Which sources does the AI cite?"** — Citation tracking: URLs, "According to X" patterns, brand associations
- **"Is my score statistically reliable?"** — Confidence intervals, volatility scoring, significance testing

## Features

| Feature | Description |
|---------|-------------|
| **6 LLM Providers** | OpenAI, Anthropic, Google, Mistral, Cohere, Perplexity — query them all simultaneously |
| **Citation Tracking** | See which sources LLMs cite when discussing your brand |
| **Brand Aliases** | "Nike Inc", "Nike Corporation" all count as Nike mentions |
| **Industry Templates** | Pre-built prompts for ecommerce, SaaS, finance, healthcare, travel, food, tech |
| **Response Caching** | Skip identical queries with file-based caching (configurable TTL) |
| **Score Breakdown** | See which of the 4 scoring factors (mentions, sentiment, position, recommendations) drags your score |
| **Fluent API** | Chainable, readable Python interface |
| **Historical Tracking** | DuckDB-powered local storage for trend analysis |
| **CLI + Python** | Full command-line and programmatic access |
| **5 Export Formats** | JSON, CSV, Markdown, HTML, pandas DataFrame |
| **Async-First** | Built for performance with concurrent provider queries |
| **Local-First** | All data stays on your machine — no cloud, no subscription |

## Installation

```bash
pip install promptbeacon
```

Or with [uv](https://github.com/astral-sh/uv) (recommended):

```bash
uv add promptbeacon
```

## Prerequisites

You need at least one LLM provider API key:

```bash
export OPENAI_API_KEY="sk-..."          # https://platform.openai.com/api-keys
export ANTHROPIC_API_KEY="sk-ant-..."   # https://console.anthropic.com/settings/keys
export GOOGLE_API_KEY="..."             # https://aistudio.google.com/apikey
```

Verify your setup:

```bash
promptbeacon providers
```

## Quick Start

### 3-Line Scan

```python
from promptbeacon import Beacon

report = Beacon("Nike").scan()
print(f"Visibility: {report.visibility_score}/100")
print(f"Mentions: {report.mention_count}")
print(f"Sentiment: {report.sentiment_breakdown.positive:.0%} positive")
```

### Full Competitive Analysis

```python
from promptbeacon import Beacon, Provider

report = (
    Beacon("Nike")
    .with_aliases("Nike Inc", "Nike Corporation")       # count all name variants
    .with_competitors("Adidas", "Puma", "New Balance")
    .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
    .with_industry("ecommerce")                          # industry-tuned prompts
    .with_cache()                                        # skip duplicate queries
    .with_storage("~/.promptbeacon/nike.db")             # track history
    .scan()
)

# Visibility score with factor breakdown
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

### Historical Tracking

```python
beacon = Beacon("Nike").with_storage("~/.promptbeacon/data.db")
report = beacon.scan()

history = beacon.get_history(days=30)
print(f"Trend: {history.trend_direction}")  # up, down, or stable

diff = beacon.compare_with_previous()
if diff:
    print(f"Change: {diff.score_change:+.1f} points")
```

## CLI Usage

```bash
# Quick 3-prompt scan (fast check)
promptbeacon quick "Nike"

# Full scan
promptbeacon scan "Nike"

# With competitors and multiple providers
promptbeacon scan "Nike" -c "Adidas" -c "Puma" -p openai -p anthropic

# Compare brands head-to-head
promptbeacon compare "Nike" --against "Adidas" --against "Puma"

# View 30-day history
promptbeacon history "Nike" --days 30

# Export as JSON or Markdown
promptbeacon scan "Nike" --format json
promptbeacon scan "Nike" --format markdown

# Check which providers are configured
promptbeacon providers
```

## Supported Providers

| Provider | Default Model | Env Variable |
|----------|---------------|--------------|
| OpenAI | gpt-4o-mini | `OPENAI_API_KEY` |
| Anthropic | claude-3-5-haiku-20241022 | `ANTHROPIC_API_KEY` |
| Google | gemini-2.0-flash | `GOOGLE_API_KEY` |
| Mistral | mistral-small-latest | `MISTRAL_API_KEY` |
| Cohere | command-r | `COHERE_API_KEY` |
| Perplexity | sonar | `PERPLEXITY_API_KEY` |

## API at a Glance

### Beacon Configuration

```python
beacon = Beacon("Nike")
```

| Method | Description |
|--------|-------------|
| `.with_competitors(*brands)` | Add competitor brands to track |
| `.with_aliases(*names)` | Alternative brand names (counted as primary) |
| `.with_providers(*providers)` | Set LLM providers to query |
| `.with_industry(name)` | Use industry-specific prompt templates |
| `.with_categories(*topics)` | Set custom analysis categories |
| `.with_prompt_count(n)` | Number of prompts per category |
| `.with_cache(ttl_seconds=...)` | Enable response caching |
| `.with_storage(path)` | Enable DuckDB historical storage |
| `.with_scoring_weights(...)` | Customise visibility score weights |
| `.with_prompts(list)` | Use fully custom prompt templates |
| `.with_temperature(t)` | LLM temperature (0.0-2.0) |
| `.with_timeout(seconds)` | Request timeout |
| `.scan()` | Run synchronous scan |
| `.scan_async()` | Run async scan |
| `.get_history(days)` | Get historical trend data |
| `.compare_with_previous()` | Compare with last scan |

### Report Object

```python
report.visibility_score        # 0-100 overall score
report.mention_count           # total brand mentions
report.sentiment_breakdown     # .positive / .neutral / .negative
report.competitor_comparison   # {name: CompetitorScore}
report.citation_summary        # .citations, .total_citations, .unique_domains
report.metrics.score_breakdown # .mention_frequency / .sentiment / .position / .recommendation
report.explanations            # evidence-based insights
report.recommendations         # prioritised action items
```

### Export Functions

```python
from promptbeacon import to_json, to_csv, to_markdown, to_html, to_dataframe

to_json(report)       # JSON string
to_csv(report)        # CSV string
to_markdown(report)   # Markdown report
to_html(report)       # Standalone HTML page
to_dataframe(report)  # pandas DataFrame
```

## Documentation

Full docs are in [docs/](docs/):

- [Quickstart Guide](docs/quickstart.md) - Up and running in 5 minutes
- [API Reference](docs/api-reference.md) - Complete API documentation
- [CLI Reference](docs/cli.md) - Command-line interface guide
- [Provider Setup](docs/providers.md) - Configure all 6 providers
- [Storage Guide](docs/storage.md) - Historical tracking with DuckDB
- [Advanced Usage](docs/advanced.md) - Custom prompts, async, integrations
- [Examples](docs/examples.md) - Real-world usage patterns

## Development

```bash
git clone https://github.com/yotambraun/promptbeacon
cd promptbeacon
uv venv && uv sync --all-extras

uv run pytest --cov -v        # tests
uv run ruff check .           # lint
uv run ruff format .          # format
```

## Contributing

Contributions welcome! See [TODO.md](TODO.md) for the roadmap.

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

## Acknowledgements

Built with [LiteLLM](https://github.com/BerriAI/litellm), [Pydantic](https://docs.pydantic.dev/), [DuckDB](https://duckdb.org/), [Typer](https://typer.tiangolo.com/), and [Rich](https://rich.readthedocs.io/).
