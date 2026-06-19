# Advanced Usage

Advanced patterns and techniques for power users of PromptBeacon.

## Table of Contents

- [Custom Prompts](#custom-prompts)
- [Async Operations](#async-operations)
- [Batch Processing](#batch-processing)
- [Custom Analysis](#custom-analysis)
- [Error Handling](#error-handling)
- [Performance Optimization](#performance-optimization)
- [Integration Patterns](#integration-patterns)
- [Custom Scoring](#custom-scoring)
- [Stability & Confidence](#stability-confidence)
- [Smart Mode (LLM Extraction & Recommendations)](#smart-mode-llm-extraction-recommendations)
- [Source Attribution & Measurement Tiers](#source-attribution-measurement-tiers)
- [Glass-Box Agentic Funnel](#glass-box-agentic-funnel)
- [CI/CD: Gate Deploys on AI Visibility](#cicd-gate-deploys-on-ai-visibility)
- [Real-Time Brand Safety](#real-time-brand-safety)

---

## Custom Prompts

### Basic Custom Prompts

Replace default prompts with your own:

```python
from promptbeacon import Beacon

custom_prompts = [
    "What {category} brands do you recommend?",
    "I need help choosing a {category} company",
    "What's your opinion on {category} brands?",
    "Can you compare different {category} options?",
    "Which {category} brand offers the best value?",
]

beacon = (
    Beacon("Nike")
    .with_prompts(custom_prompts)
    .with_categories("running shoes", "athletic wear")
)

report = beacon.scan()
```

### Industry-Specific Prompts

PromptBeacon includes built-in industry prompt templates for 7 verticals. Use `.with_industry()` instead of writing custom prompts:

```python
# Use built-in industry templates (10 prompts each)
beacon = Beacon("Nike").with_industry("ecommerce")

# Available industries: ecommerce, saas, finance, healthcare, travel, food, tech
beacon = Beacon("Salesforce").with_industry("saas")
beacon = Beacon("Mayo Clinic").with_industry("healthcare")
```

You can still write fully custom prompts for industries not covered:

```python
# Custom prompts for niche industries
legal_prompts = [
    "What are the best {category} law firms?",
    "Which {category} legal service do you recommend?",
    "What {category} lawyer should I consult?",
]

beacon = Beacon("LegalZoom").with_prompts(legal_prompts)
```

### Multilingual Prompts

```python
# Spanish prompts
spanish_prompts = [
    "¿Cuáles son las mejores marcas de {category}?",
    "¿Qué marca de {category} recomiendas?",
    "¿Cuál es la marca más popular de {category}?",
]

beacon_es = (
    Beacon("Nike")
    .with_prompts(spanish_prompts)
    .with_categories("zapatos deportivos")
)

# French prompts
french_prompts = [
    "Quelles sont les meilleures marques de {category}?",
    "Quelle marque de {category} recommandez-vous?",
]

beacon_fr = (
    Beacon("Nike")
    .with_prompts(french_prompts)
    .with_categories("chaussures de course")
)
```

---

## Async Operations

### Concurrent Brand Scanning

```python
import asyncio
from promptbeacon import Beacon, Provider

async def scan_brands_concurrently(brands: list[str]):
    """Scan multiple brands concurrently."""
    async def scan_brand(brand: str):
        beacon = (
            Beacon(brand)
            .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
            .with_prompt_count(10)
        )
        return await beacon.scan_async()

    # Run all scans concurrently
    reports = await asyncio.gather(*[scan_brand(b) for b in brands])

    return {
        brand: report.visibility_score
        for brand, report in zip(brands, reports)
    }

# Usage
brands = ["Nike", "Adidas", "Puma", "New Balance", "Under Armour"]
scores = asyncio.run(scan_brands_concurrently(brands))

for brand, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
    print(f"{brand}: {score:.1f}")
```

### Async with Progress Tracking

```python
import asyncio
from promptbeacon import Beacon
from rich.progress import Progress, SpinnerColumn, TextColumn

async def scan_with_progress(brands: list[str]):
    """Scan brands with progress indicator."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:

        task = progress.add_task("Scanning brands...", total=len(brands))

        async def scan_and_update(brand: str):
            beacon = Beacon(brand)
            report = await beacon.scan_async()
            progress.update(task, advance=1, description=f"Scanned {brand}")
            return brand, report

        results = await asyncio.gather(*[scan_and_update(b) for b in brands])

    return dict(results)

# Usage
results = asyncio.run(scan_with_progress(["Nike", "Adidas", "Puma"]))
```

### Async Rate Limiting

```python
import asyncio
from promptbeacon import Beacon

async def scan_with_rate_limit(brands: list[str], max_concurrent: int = 3):
    """Scan brands with rate limiting."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def scan_brand(brand: str):
        async with semaphore:
            beacon = Beacon(brand)
            return await beacon.scan_async()

    reports = await asyncio.gather(*[scan_brand(b) for b in brands])
    return reports

# Limit to 3 concurrent scans
reports = asyncio.run(scan_with_rate_limit(["Nike", "Adidas", "Puma"], max_concurrent=3))
```

---

## Batch Processing

### Scheduled Batch Scans

```python
import asyncio
from datetime import datetime
from pathlib import Path
from promptbeacon import Beacon, to_json

async def batch_scan(brands: list[str], output_dir: str = "./scans"):
    """Run batch scans and save results."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    async def scan_and_save(brand: str):
        beacon = Beacon(brand).with_storage(f"{output_dir}/data.db")
        report = await beacon.scan_async()

        # Save individual report
        filename = f"{brand}_{timestamp}.json"
        with open(output_path / filename, "w") as f:
            f.write(to_json(report))

        return brand, report

    results = await asyncio.gather(*[scan_and_save(b) for b in brands])

    return dict(results)

# Usage
brands = ["Nike", "Adidas", "Puma", "New Balance"]
results = asyncio.run(batch_scan(brands))

print(f"Scanned {len(results)} brands")
```

### Competitive Matrix

```python
import asyncio
from promptbeacon import Beacon
import pandas as pd

async def competitive_matrix(brands: list[str], categories: list[str]):
    """Generate competitive matrix across brands and categories."""
    async def scan_brand_category(brand: str, category: str):
        beacon = (
            Beacon(brand)
            .with_categories(category)
            .with_prompt_count(10)
        )
        report = await beacon.scan_async()
        return (brand, category, report.visibility_score)

    tasks = [
        scan_brand_category(brand, category)
        for brand in brands
        for category in categories
    ]

    results = await asyncio.gather(*tasks)

    data = {
        "Brand": [r[0] for r in results],
        "Category": [r[1] for r in results],
        "Score": [r[2] for r in results],
    }

    df = pd.DataFrame(data)
    matrix = df.pivot(index="Brand", columns="Category", values="Score")

    return matrix

# Usage
brands = ["Nike", "Adidas", "Puma"]
categories = ["running shoes", "athletic wear", "sports brand"]

matrix = asyncio.run(competitive_matrix(brands, categories))
print(matrix)
```

---

## Custom Analysis

### Provider Comparison

```python
from promptbeacon import Beacon, Provider
from collections import defaultdict

def provider_comparison(brand: str):
    """Compare brand visibility across providers."""
    beacon = (
        Beacon(brand)
        .with_providers(Provider.OPENAI, Provider.ANTHROPIC, Provider.GOOGLE)
        .with_prompt_count(15)
    )

    report = beacon.scan()

    provider_stats = defaultdict(lambda: {"mentions": 0, "positive": 0, "total": 0})

    for result in report.provider_results:
        provider = result.provider
        for mention in result.mentions:
            if mention.brand_name.lower() == brand.lower():
                provider_stats[provider]["mentions"] += 1
                provider_stats[provider]["total"] += 1
                if mention.sentiment == "positive":
                    provider_stats[provider]["positive"] += 1

    print(f"\n{brand} by Provider:")
    for provider, stats in provider_stats.items():
        if stats["total"] > 0:
            positive_rate = stats["positive"] / stats["total"]
            print(f"\n{provider}:")
            print(f"  Mentions: {stats['mentions']}")
            print(f"  Positive rate: {positive_rate:.0%}")

    # Also compare SoV per provider
    for provider_name, provider_sov in report.share_of_voice.by_provider.items():
        print(f"\n{provider_name} SoV: {provider_sov.target_share:.0%}")

provider_comparison("Nike")
```

---

## Error Handling

### Comprehensive Error Handling

```python
from promptbeacon import Beacon, Provider
from promptbeacon.core.exceptions import (
    ConfigurationError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderAPIError,
    ScanError,
)
import time

def robust_scan(brand: str, max_retries: int = 3):
    """Scan with comprehensive error handling, demo fallback."""
    for attempt in range(max_retries):
        try:
            beacon = Beacon(brand).with_providers(Provider.OPENAI)
            report = beacon.scan()
            return report

        except ConfigurationError as e:
            print(f"Configuration error: {e}")
            print("Falling back to demo mode")
            return Beacon(brand).demo().scan()

        except ProviderAuthenticationError as e:
            print(f"Authentication failed: {e}")
            return None

        except ProviderRateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Rate limit hit. Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print("Rate limit exceeded after retries")
                return None

        except ScanError as e:
            print(f"Scan failed: {e}")
            return None

    return None

report = robust_scan("Nike")
if report:
    print(f"Score: {report.visibility_score:.1f}")
```

---

## Performance Optimization

### Caching Results

PromptBeacon has built-in response caching. Enable it with `.with_cache()`:

```python
from promptbeacon import Beacon

# Enable caching with default 24-hour TTL
beacon = Beacon("Nike").with_cache()

# First scan - queries LLM providers
report1 = beacon.scan()

# Second scan - uses cached responses (instant, free)
report2 = beacon.scan()
```

The cache is keyed by `(prompt, provider, model)`, so changing providers or prompts will trigger fresh queries. Note that stability scans intentionally bypass the cache — each run must be a fresh query.

### Optimized Configuration

```python
from promptbeacon import Beacon, Provider

# Fast, cost-effective configuration
fast_beacon = (
    Beacon("Nike")
    .with_providers(Provider.GOOGLE)  # Fast provider
    .with_prompt_count(5)             # Fewer prompts
    .with_temperature(0.5)            # Lower temperature
    .with_max_tokens(512)             # Fewer tokens
    .with_timeout(15.0)               # Shorter timeout
)

# Comprehensive, higher cost configuration
comprehensive_beacon = (
    Beacon("Nike")
    .with_providers(Provider.OPENAI, Provider.ANTHROPIC, Provider.GOOGLE)
    .with_prompt_count(25)
    .with_temperature(0.7)
    .with_max_tokens(1024)
    .with_timeout(60.0)
)
```

---

## Integration Patterns

### Slack Integration

```python
from promptbeacon import Beacon, to_markdown
import requests

def send_to_slack(webhook_url: str, brand: str):
    """Send scan results to Slack."""
    beacon = Beacon(brand).with_competitors("Competitor A", "Competitor B")
    report = beacon.scan()

    sov = report.share_of_voice
    message = f"""
    *Visibility Report: {brand}*

    Score: *{report.visibility_score:.1f}/100*
    Share of Voice: *{sov.target_share:.0%}* (rank #{sov.target_rank})
    Mentions: {report.mention_count}
    Sentiment: {report.sentiment_breakdown.positive:.0%} positive

    Competitors:
    """

    for name, score in report.competitor_comparison.items():
        diff = report.visibility_score - score.visibility_score
        message += f"\n• {name}: {score.visibility_score:.1f} ({diff:+.1f})"

    payload = {"text": message}
    response = requests.post(webhook_url, json=payload)

    return response.status_code == 200

send_to_slack("https://hooks.slack.com/services/YOUR/WEBHOOK/URL", "Nike")
```

### API Endpoint

```python
from fastapi import FastAPI
from promptbeacon import Beacon
from pydantic import BaseModel

app = FastAPI()

class ScanRequest(BaseModel):
    brand: str
    competitors: list[str] = []
    prompt_count: int = 10
    demo: bool = False

class ScanResponse(BaseModel):
    brand: str
    visibility_score: float
    share_of_voice: float
    mention_count: int
    sentiment_positive: float

@app.post("/scan", response_model=ScanResponse)
async def scan_brand(request: ScanRequest):
    """API endpoint for brand scanning."""
    beacon = Beacon(request.brand)

    if request.demo:
        beacon = beacon.demo()

    if request.competitors:
        beacon = beacon.with_competitors(*request.competitors)

    beacon = beacon.with_prompt_count(request.prompt_count)
    report = await beacon.scan_async()

    return ScanResponse(
        brand=report.brand,
        visibility_score=report.visibility_score,
        share_of_voice=report.share_of_voice.target_share,
        mention_count=report.mention_count,
        sentiment_positive=report.sentiment_breakdown.positive,
    )
```

---

## Custom Scoring

### Configurable Scoring Weights

PromptBeacon's visibility score is composed of 4 factors. You can customize their weights with `.with_scoring_weights()`:

```python
from promptbeacon import Beacon

# Default weights: mention_frequency=0.3, sentiment=0.25, position=0.25, recommendation=0.2
beacon = Beacon("Nike")

# Custom weights (must sum to 1.0)
beacon = Beacon("Nike").with_scoring_weights(
    mention_frequency=0.2,
    sentiment=0.4,     # Weight sentiment more heavily
    position=0.2,
    recommendation=0.2,
)

report = beacon.scan()

# See the breakdown of each factor (0-100 before weighting)
bd = report.metrics.score_breakdown
print(f"Mention Frequency: {bd.mention_frequency:.0f}/100")
print(f"Sentiment: {bd.sentiment:.0f}/100")
print(f"Position: {bd.position:.0f}/100")
print(f"Recommendation: {bd.recommendation:.0f}/100")
print(f"Weighted total: {report.visibility_score:.1f}/100")
```

---

## Stability & Confidence

Stability scanning answers the question: "Does AI mention my brand consistently, or does it flip-flop?" It runs the full scan N times and computes a `StabilityReport`.

### Running a Stability Scan

```python
from promptbeacon import Beacon

report = (
    Beacon("Nike")
    .with_competitors("Adidas", "Puma")
    .with_stability(5)         # Run 5 times
    .with_temperature(0.7)     # Non-zero temperature required
    .scan_stability()
)

s = report.stability
print(f"Stability score: {s.stability_score:.1f}/100")
print(f"Rating: {s.volatility.stability_rating}")  # stable / moderate / volatile
print(f"95% CI: [{s.score_confidence_interval[0]:.1f}, {s.score_confidence_interval[1]:.1f}]")
print(f"Per-run scores: {[f'{x:.1f}' for x in s.score_per_run]}")
print(f"Presence consistency: {s.overall_presence_consistency:.0%}")
print(f"Flip-flops: {s.flip_flop_count}")
```

CLI equivalent:

```bash
promptbeacon scan "Nike" --stability 5
# short form:
promptbeacon scan "Nike" -r 5
```

### Important Warnings

- **Cost**: Multiplies API calls (and cost) by N. A 10-prompt scan with `--stability 5` makes 50 API calls.
- **Cache**: Stability scans bypass the response cache intentionally. Each run must query providers fresh.
- **Temperature**: Use a non-zero temperature (e.g., `0.7`). At `temperature=0`, all runs will produce identical results and the stability score will be artificially inflated.

### Async Stability Scan

```python
import asyncio
from promptbeacon import Beacon

async def main():
    report = await (
        Beacon("Nike")
        .with_stability(5)
        .scan_stability_async()
    )
    print(f"Stability: {report.stability.stability_score:.1f}/100")

asyncio.run(main())
```

### Interpreting Stability

| Stability Score | Rating | Meaning |
|----------------|--------|---------|
| 80-100 | stable | AI consistently mentions your brand |
| 50-79 | moderate | Presence varies run to run |
| 0-49 | volatile | AI rarely or inconsistently mentions your brand |

A high `flip_flop_count` means the brand appears in some runs but not others for the same prompt — often a sign of marginal awareness that is sensitive to LLM temperature and prompt phrasing.

### Distribution-grade metrics

Answer-engine output is stochastic, so a single confidence interval can mislead. A stability scan also reports:

- **`score_bootstrap_interval`** — a percentile-bootstrap 95% CI (distribution-free), alongside the normal-approximation `score_confidence_interval`.
- **`source_stability`** — per-domain citation consistency: which sources the engines cite on every run vs. flip-flop.

```python
report = Beacon("Nike").with_competitors("Adidas").with_stability(5).scan_stability()
s = report.stability
print("bootstrap 95% CI:", s.score_bootstrap_interval)
for src in s.source_stability[:5]:
    state = "flip-flop" if src.flip_flopped else "stable"
    print(f"{src.domain}: {src.presence_rate:.0%} of runs ({state})")
```

### Buyer-intent prompt sets

The recommended GEO protocol measures across 50–200 buyer-intent prompts. Generate a stable set instead of hand-writing them:

```python
from promptbeacon.prompts.templates import generate_buyer_intent_prompts

prompts = generate_buyer_intent_prompts("running shoes", n=50)
report = Beacon("Nike").with_prompts(prompts).scan()
```

### Reproducible protocols

"Don't measure once" also means *measure the same way every time*. Pin the whole scan in a JSON file so trends stay comparable:

```python
from promptbeacon.protocol import build_beacon, load_protocol

beacon = build_beacon(load_protocol("nike-protocol.json"))
report = beacon.scan()  # or .scan_stability() when the protocol sets "runs"
```

CLI equivalent: `promptbeacon scan --protocol nike-protocol.json`.

---

## Smart Mode (LLM Extraction & Recommendations)

Smart mode replaces regex-based extraction and rule-based recommendations with LLM calls that use structured output. It is opt-in and adds one extra API call per smart operation.

### Smart Extraction

Use an LLM to extract mentions and sentiment rather than regex:

```python
from promptbeacon import Beacon

report = (
    Beacon("Nike")
    .with_smart_extraction()   # LLM extraction
    .scan()
)

# Mentions are extracted with higher accuracy on complex responses
for result in report.provider_results:
    for mention in result.mentions:
        print(f"{mention.brand_name}: {mention.sentiment} (confidence: {mention.confidence:.2f})")
```

### Smart Recommendations

Generate evidence-linked, prioritized recommendations via LLM:

```python
from promptbeacon import Beacon

report = (
    Beacon("Nike")
    .with_smart_recommendations()
    .scan()
)

for rec in report.recommendations:
    print(f"[{rec.priority.upper()}] {rec.action}")
    print(f"  Rationale: {rec.rationale}")
    print(f"  Expected impact: {rec.expected_impact}")
```

### Enable Both

```python
report = (
    Beacon("Nike")
    .with_smart_extraction()
    .with_smart_recommendations()
    .scan()
)
```

CLI equivalent (enables both):

```bash
promptbeacon scan "Nike" --smart
```

### Notes

- Smart mode is **not** used in demo mode (`.demo()`)
- Falls back gracefully to regex/rule-based on error (no exception raised)
- Requires at least one provider API key
- Adds approximately one extra LLM call per feature enabled

---

## Source Attribution & Measurement Tiers

### Which sites the engines cite

Web-grounded AI answers cite their sources. Every scan aggregates those
citations by **domain** so you can see which sites the engines trust for your
category — and which of them cite *you*. This is the actionable GEO lever: to
get recommended, get cited on the sources the engines already trust.

```python
from promptbeacon import Beacon

report = Beacon("Nike").with_competitors("Adidas").demo().scan()

sa = report.source_attribution
print(f"{sa.total_citations} citations across {len(sa.entries)} domains")
for entry in sa.entries[:10]:
    flag = "cites you" if entry.cites_target else ""
    print(f"{entry.domain:<28} {entry.source_type:<10} "
          f"{entry.citations:>3} ({entry.share:.0%}) {flag}")

# Citation mix by source type (reddit / wikipedia / news / review / ...)
print(sa.by_type)
# Domains that cited your brand specifically
print(sa.target_cited_domains)
```

CLI:

```bash
promptbeacon sources "Nike" --competitor "Adidas" --demo
```

### Measurement tiers (honesty label)

Not every scan measures the same thing. `report.measurement_tier` makes it
explicit so you never mistake one for another:

| Tier | What it measures |
|------|------------------|
| `demo` | Canned offline data — for exploration, not a real measurement |
| `base_model` | A plain LLM completion with **no web search** — the model's *training memory*, not live AI search |
| `api_grounded` | The provider's web-search/grounding tool — approximates, but does **not** equal, the consumer product (ChatGPT.com etc.) |

The CLI prints this as a one-line banner on every text report, and it is
included in JSON output.

### Web-grounded scanning

By default a scan queries plain LLM completions (the model's training memory).
`with_grounding()` enables a provider's **native web-search tool** so the scan
reflects what AI *search* returns, capturing the real sources it cited:

```python
from promptbeacon import Beacon

# Requires: pip install 'promptbeacon[grounded]' and ANTHROPIC_API_KEY
report = Beacon("Nike").with_competitors("Adidas").with_grounding().scan()

assert report.measurement_tier == "api_grounded"
for entry in report.source_attribution.entries[:5]:
    state = "cited" if any(
        not c.retrieved_but_uncited
        for r in report.provider_results for c in r.citations
        if c.source_name == entry.domain
    ) else "retrieved-only"
    print(entry.domain, entry.source_type, state)
```

CLI: `promptbeacon scan "Nike" --grounded` or `promptbeacon sources "Nike" --grounded`.

Covered: OpenAI (Responses `web_search`), Anthropic (Brave-backed web search),
Gemini (Google Search grounding), and Perplexity (sonar); Mistral and Cohere
fall back to base completion, and the scan stays honestly labelled `base_model`.
The provider API approximates, but does **not** equal, the consumer product.

---

## CI/CD: Gate Deploys on AI Visibility

PromptBeacon provides three layers of CI integration: a Python assertion API, a pytest plugin, and a GitHub Action composite workflow.

### 1. Assertion API

Call `report.assert_visibility(...)` to fail fast when brand health drops below thresholds. It raises `VisibilityAssertionError` (an `AssertionError` subclass) listing all unmet thresholds:

```python
from promptbeacon import Beacon
from promptbeacon.core.exceptions import VisibilityAssertionError
import sys

report = Beacon("Nike").with_competitors("Adidas", "Puma").scan()

try:
    report.assert_visibility(
        min_score=40,
        min_share_of_voice=0.15,
        min_presence_rate=0.5,
        max_rank=3,
    )
    print("Visibility check passed")
except VisibilityAssertionError as e:
    print("Visibility check failed:")
    for failure in e.failures:
        print(f"  - {failure}")
    sys.exit(1)
```

CLI flags on `scan` command:

```bash
promptbeacon scan "Nike" \
  --assert-min-score 40 \
  --assert-min-sov 0.15 \
  --assert-min-stability 70   # requires --stability N
```

Exit code is `1` on assertion failure, `0` on success.

### 2. Pytest Plugin

The pytest plugin auto-registers via the `promptbeacon` entry point — no import needed. Use the `@pytest.mark.visibility` mark to run a scan and assert thresholds:

```python
# test_brand_visibility.py
import pytest

@pytest.mark.visibility(
    brand="Nike",
    competitors=["Adidas", "Puma"],
    min_score=40,
    min_share_of_voice=0.15,
    demo=True,   # Use demo mode (no keys needed in CI)
)
def test_nike_visibility():
    pass  # Assertion is performed by the plugin; test body is optional

@pytest.mark.visibility(brand="Nike", min_score=50)
def test_nike_score_threshold():
    pass
```

A `beacon` fixture factory is also available for custom assertions:

```python
def test_custom_visibility_check(beacon):
    report = beacon("Nike", competitors=["Adidas"]).scan()
    assert report.visibility_score >= 30
    assert report.share_of_voice.target_rank <= 2
```

**Demo mode in CI**: Tests skip cleanly when no API keys are present and `demo=True` is not set. Set the environment variable `PROMPTBEACON_DEMO=1` to force demo mode for all visibility tests in CI without API keys:

```bash
PROMPTBEACON_DEMO=1 pytest tests/
```

Run the tests:

```bash
pip install 'promptbeacon[test]'
pytest tests/test_brand_visibility.py -v
```

### 3. GitHub Action

A composite GitHub Action lives at the repository root `action.yml`. Use it to gate any workflow on AI visibility:

```yaml
# .github/workflows/brand-check.yml
name: AI Visibility Gate

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 9 * * 1'   # Weekly on Monday morning

jobs:
  visibility:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Check AI visibility
        uses: yotambraun/promptbeacon@v1
        with:
          brand: "Nike"
          competitors: "Adidas,Puma,New Balance"
          providers: "openai,anthropic"
          min-score: "40"
          min-share-of-voice: "0.15"
          stability: "3"
          min-stability: "60"
          demo: "false"   # set to "true" to use demo mode (no keys)
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

**Action inputs:**

| Input | Required | Description |
|-------|----------|-------------|
| `brand` | yes | Brand to check |
| `competitors` | no | Comma-separated competitor list |
| `providers` | no | Comma-separated provider list |
| `min-score` | no | Minimum visibility score (0-100) |
| `min-share-of-voice` | no | Minimum SoV (0-1) |
| `stability` | no | Number of stability runs |
| `min-stability` | no | Minimum stability score (0-100) |
| `demo` | no | Use demo mode (`"true"`/`"false"`) |

The action exits with code `1` if any threshold is not met, failing the workflow.

---

## Glass-Box Agentic Funnel

Modern AI search is agentic: it fans a query into 8–12 sub-queries, retrieves for each, reranks, reflects, then cites. Citation trackers see only the *survivors*. The funnel runs a **local, observable model** of that pipeline so you can see *where* your brand drops out.

```python
import asyncio
from promptbeacon.funnel import MockSearchBackend, run_funnel  # TavilyBackend for live

report = asyncio.run(
    run_funnel(
        "Nike",
        "What are the best running shoes?",
        backend=MockSearchBackend("Nike", competitors=["Adidas"]),  # keyless
        competitors=["Adidas"],
        n_sub_queries=8,
    )
)

print(report.sub_query_coverage)           # brand retrieved for X% of sub-queries
print(report.rerank_survival_rate)         # of those, X% survive reranking
print(report.retrieval_to_citation_ratio)  # of those, X% survive to citation
print(report.stage_failure)                # retrieval | rerank | citation | none
```

For live web search, set `TAVILY_API_KEY` and use `TavilyBackend(api_key)` (called over httpx — no extra SDK). CLI: `promptbeacon funnel "Nike" --category "running shoes" --demo`.

It is a **model** of agentic search (tier `funnel_model`), not a clone of any consumer product. The default planner (deterministic fan-out) and reranker (lexical) keep it dependency-free; an LLM planner/reranker can be layered on for higher fidelity.

---

## Real-Time Brand Safety

### BeaconGuard Basics

BeaconGuard analyzes LLM outputs for brand safety concerns. It is synchronous, uses no API calls, and processes everything locally:

```python
from promptbeacon import BeaconGuard

guard = BeaconGuard(
    "Nike",
    competitors=["Adidas", "Puma"],
    aliases=["Nike Inc"],
    flag_competitor_mention=True,
    flag_negative_sentiment=True,
    flag_no_brand_mention=True,
    flag_anti_recommendation=True,
)

result = guard.analyze("I'd suggest Adidas — Nike has had quality issues.")
print(f"Risk: {result.risk_level}")           # "high"
print(f"Flags: {result.flags}")               # multiple flags
print(f"Competitor: {result.competitor_names}")# ["Adidas"]
print(f"Anti-rec: {result.is_anti_recommendation}")
```

### LangChain Integration

Use BeaconGuard as a LangChain callback handler to monitor every LLM response:

```python
from promptbeacon import BeaconGuard
from promptbeacon.integrations.langchain import BeaconGuardCallbackHandler

guard = BeaconGuard("Acme", competitors=["CompetitorX"])

def on_brand_risk(result):
    print(f"Brand safety alert: {result.flags}")

handler = BeaconGuardCallbackHandler(guard, on_high_risk=on_brand_risk)

# Pass handler to your LangChain chain's callbacks:
# chain.invoke({"input": "..."}, config={"callbacks": [handler]})
```

Or use as an output parser to get `GuardResult` directly in your chain:

```python
from promptbeacon.integrations.langchain import BeaconGuardOutputParser

parser = BeaconGuardOutputParser(guard=guard)
# chain | parser  -> returns GuardResult
```

Install the optional dependency: `pip install 'promptbeacon[langchain]'`

### Custom Risk Rules with Middleware

Use `BeaconGuardMiddleware` to add brand safety to any pipeline:

```python
from promptbeacon import BeaconGuard
from promptbeacon.integrations.middleware import BeaconGuardMiddleware

guard = BeaconGuard("Acme", competitors=["CompetitorX"])

def handle_risk(result):
    if result.is_anti_recommendation:
        raise ValueError(f"Blocked: anti-recommendation detected")

middleware = BeaconGuardMiddleware(guard, on_high_risk=handle_risk)

llm_output = get_llm_response(prompt)
result = middleware(llm_output)
# result.risk_level tells you if the output is safe
```

---

## See Also

- [API Reference](api-reference.md) - Complete API documentation
- [Examples](examples.md) - Real-world usage examples
- [Storage Guide](storage.md) - Advanced data management
- [Provider Configuration](providers.md) - Provider optimization
