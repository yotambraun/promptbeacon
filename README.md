# PromptBeacon

**Track how AI sees your brand.** Monitor your brand's visibility across ChatGPT, Claude, Gemini, and other LLMs.

[![PyPI version](https://badge.fury.io/py/promptbeacon.svg)](https://badge.fury.io/py/promptbeacon)
[![CI](https://github.com/yotambraun/promptbeacon/actions/workflows/ci.yml/badge.svg)](https://github.com/yotambraun/promptbeacon/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/yotambraun/promptbeacon/branch/main/graph/badge.svg)](https://codecov.io/gh/yotambraun/promptbeacon)

---

## Why PromptBeacon?

As AI assistants become the new search engines, brands need to understand how they appear in AI-generated responses. PromptBeacon provides:

- **Visibility Scoring**: Measure how often and prominently your brand is mentioned (0-100 scale)
- **Sentiment Analysis**: Understand if AI talks about your brand positively, neutrally, or negatively
- **Competitor Benchmarking**: Compare your visibility against competitors
- **Explainable Insights**: Not just "score dropped 5%" but *why* with actual quotes
- **Statistical Rigor**: Confidence intervals, volatility scoring, significance testing
- **Local-First**: All data stays on your machine with DuckDB storage

## Features

| Feature | Description |
|---------|-------------|
| **Multi-Provider** | Query OpenAI, Anthropic, and Google simultaneously |
| **Fluent API** | Chainable, readable Python interface |
| **Historical Tracking** | DuckDB-powered local storage for trend analysis |
| **CLI Interface** | Full command-line support for automation |
| **Export Formats** | JSON, CSV, Markdown, HTML, pandas DataFrame |
| **Async Support** | Built for performance with async-first design |

## Installation

```bash
pip install promptbeacon
```

With [uv](https://github.com/astral-sh/uv) (recommended):

```bash
uv add promptbeacon
```

## Quick Start

### Simple Usage

```python
from promptbeacon import Beacon

beacon = Beacon("Nike")
report = beacon.scan()

print(f"Visibility: {report.visibility_score}/100")
print(f"Mentions: {report.mention_count}")
print(f"Sentiment: {report.sentiment_breakdown.positive:.0%} positive")
```

### Competitor Analysis

```python
from promptbeacon import Beacon, Provider

beacon = (
    Beacon("Nike")
    .with_competitors("Adidas", "Puma", "New Balance")
    .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
    .with_categories("running shoes", "athletic wear", "sports brand")
    .with_prompt_count(20)
)

report = beacon.scan()

# Compare against competitors
for name, score in report.competitor_comparison.items():
    print(f"{name}: {score.visibility_score:.1f}")
```

### Historical Tracking

```python
from promptbeacon import Beacon

beacon = Beacon("Nike").with_storage("~/.promptbeacon/data.db")

# Scan and auto-save
report = beacon.scan()

# Get 30-day trends
history = beacon.get_history(days=30)
print(f"Trend: {history.trend_direction}")  # up, down, or stable

# Compare with previous scan
diff = beacon.compare_with_previous()
if diff:
    print(f"Change: {diff.score_change:+.1f} points")
```

### Actionable Insights

```python
# Get explanations for your visibility
for exp in report.explanations:
    print(f"[{exp.impact.upper()}] {exp.message}")

# Get prioritized recommendations
for rec in report.recommendations:
    print(f"[{rec.priority}] {rec.action}")
    print(f"  Why: {rec.rationale}")
```

## CLI Usage

```bash
# Basic scan
promptbeacon scan "Nike"

# With competitors
promptbeacon scan "Nike" -c "Adidas" -c "Puma" -p openai -p anthropic

# Compare brands
promptbeacon compare "Nike" --against "Adidas" --against "Puma"

# View history
promptbeacon history "Nike" --days 30

# Output formats
promptbeacon scan "Nike" --format json
promptbeacon scan "Nike" --format markdown

# Check provider status
promptbeacon providers
```

## Configuration

### Environment Variables

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
```

### Default Models

| Provider | Model |
|----------|-------|
| OpenAI | gpt-4o-mini |
| Anthropic | claude-3-haiku-20240307 |
| Google | gemini-1.5-flash |

## API Reference

### Beacon Class

```python
beacon = Beacon(brand: str)
```

| Method | Description |
|--------|-------------|
| `.with_competitors(*brands)` | Add competitor brands |
| `.with_providers(*providers)` | Set LLM providers |
| `.with_categories(*topics)` | Set analysis categories |
| `.with_prompt_count(n)` | Prompts per category |
| `.with_storage(path)` | Enable DuckDB storage |
| `.with_temperature(t)` | LLM temperature (0-2) |
| `.with_timeout(seconds)` | Request timeout |
| `.scan()` | Run synchronous scan |
| `.scan_async()` | Run async scan |
| `.get_history(days)` | Get historical data |
| `.compare_with_previous()` | Compare scans |

### Report Object

```python
report.visibility_score      # 0-100 score
report.mention_count         # Total mentions
report.sentiment_breakdown   # positive/neutral/negative
report.competitor_comparison # Competitor scores
report.explanations          # Why insights
report.recommendations       # Action items
report.metrics              # Detailed metrics
```

### Export Functions

```python
from promptbeacon import to_json, to_csv, to_markdown, to_html, to_dataframe

to_json(report)       # JSON string
to_csv(report)        # CSV string
to_markdown(report)   # Markdown
to_html(report)       # HTML page
to_dataframe(report)  # pandas DataFrame
```

## Development

```bash
git clone https://github.com/yotambraun/promptbeacon
cd promptbeacon

# Setup with uv
uv venv
uv sync --all-extras

# Run tests
uv run pytest --cov -v

# Lint
uv run ruff check .
uv run ruff format .
uv run mypy src/promptbeacon
```

## Documentation

Full documentation is available in the [docs/](docs/) folder:

- [**Quickstart Guide**](docs/quickstart.md) - Get up and running in 5 minutes
- [**API Reference**](docs/api-reference.md) - Complete API documentation
- [**CLI Reference**](docs/cli.md) - Command-line interface guide
- [**Provider Setup**](docs/providers.md) - Configure OpenAI, Anthropic, Google
- [**Storage Guide**](docs/storage.md) - Historical tracking with DuckDB
- [**Advanced Usage**](docs/advanced.md) - Custom prompts, async, advanced analysis
- [**Examples**](docs/examples.md) - Real-world usage patterns

## Contributing

Contributions welcome! See [TODO.md](TODO.md) for the roadmap.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgements

Built with [LiteLLM](https://github.com/BerriAI/litellm), [Pydantic](https://docs.pydantic.dev/), [DuckDB](https://duckdb.org/), [Typer](https://typer.tiangolo.com/), and [Rich](https://rich.readthedocs.io/).
