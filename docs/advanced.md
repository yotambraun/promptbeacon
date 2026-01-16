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

```python
# B2B SaaS
saas_prompts = [
    "What are the best {category} software solutions?",
    "Which {category} tool should our team use?",
    "What's the leading {category} platform for enterprises?",
    "Can you recommend a {category} service for our company?",
    "What {category} vendors do you suggest?",
]

# E-commerce
ecommerce_prompts = [
    "Where should I buy {category}?",
    "What {category} store has the best selection?",
    "Which online retailer is best for {category}?",
    "Can you recommend a {category} website?",
]

# Healthcare
healthcare_prompts = [
    "What {category} providers are highly rated?",
    "Which {category} service should I consider?",
    "What are the best {category} options in my area?",
]
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

### Targeted Prompts

```python
# Price-focused
price_prompts = [
    "What's the most affordable {category} brand?",
    "Which {category} offers the best value?",
    "What are budget-friendly {category} options?",
]

# Quality-focused
quality_prompts = [
    "What's the highest quality {category} brand?",
    "Which {category} is known for durability?",
    "What {category} brand do professionals use?",
]

# Innovation-focused
innovation_prompts = [
    "What's the most innovative {category} brand?",
    "Which {category} company is leading in technology?",
    "What {category} brand has the best features?",
]
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

### Multi-Category Batch Analysis

```python
from promptbeacon import Beacon
from itertools import product

def batch_category_analysis(brand: str, categories: list[str]):
    """Analyze brand across multiple categories."""
    results = {}

    for category in categories:
        beacon = (
            Beacon(brand)
            .with_categories(category)
            .with_prompt_count(15)
        )

        report = beacon.scan()
        results[category] = {
            "score": report.visibility_score,
            "mentions": report.mention_count,
            "sentiment": report.sentiment_breakdown.positive,
        }

    return results

# Usage
categories = [
    "running shoes",
    "athletic wear",
    "sports equipment",
    "fitness apparel",
    "training gear",
]

results = batch_category_analysis("Nike", categories)

for category, metrics in results.items():
    print(f"\n{category}:")
    print(f"  Score: {metrics['score']:.1f}")
    print(f"  Mentions: {metrics['mentions']}")
    print(f"  Positive: {metrics['sentiment']:.0%}")
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

    # Generate all combinations
    tasks = [
        scan_brand_category(brand, category)
        for brand in brands
        for category in categories
    ]

    results = await asyncio.gather(*tasks)

    # Create DataFrame
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

### Sentiment Deep Dive

```python
from promptbeacon import Beacon
from collections import Counter

def sentiment_analysis(brand: str):
    """Detailed sentiment analysis."""
    beacon = (
        Beacon(brand)
        .with_prompt_count(25)
        .with_categories("product quality", "customer service", "value")
    )

    report = beacon.scan()

    # Analyze by category
    category_sentiment = {}

    for result in report.provider_results:
        for mention in result.mentions:
            if mention.brand_name.lower() == brand.lower():
                category = extract_category(result.prompt)
                if category not in category_sentiment:
                    category_sentiment[category] = []
                category_sentiment[category].append(mention.sentiment)

    # Calculate sentiment by category
    for category, sentiments in category_sentiment.items():
        sentiment_counts = Counter(sentiments)
        total = len(sentiments)

        print(f"\n{category}:")
        print(f"  Positive: {sentiment_counts['positive']/total:.0%}")
        print(f"  Neutral: {sentiment_counts['neutral']/total:.0%}")
        print(f"  Negative: {sentiment_counts['negative']/total:.0%}")

def extract_category(prompt: str) -> str:
    """Extract category from prompt."""
    # Simple extraction - customize based on your prompts
    for word in ["quality", "service", "value", "price"]:
        if word in prompt.lower():
            return word
    return "general"

sentiment_analysis("Nike")
```

### Position Analysis

```python
from promptbeacon import Beacon
import statistics

def position_analysis(brand: str):
    """Analyze brand mention positions."""
    beacon = Beacon(brand).with_prompt_count(20)
    report = beacon.scan()

    positions = []
    for result in report.provider_results:
        for mention in result.mentions:
            if mention.brand_name.lower() == brand.lower():
                positions.append(mention.position)

    if positions:
        print(f"\n{brand} Position Analysis:")
        print(f"  Average position: {statistics.mean(positions):.1f}")
        print(f"  Median position: {statistics.median(positions):.1f}")
        print(f"  Best position: {min(positions)}")
        print(f"  Worst position: {max(positions)}")
        print(f"  First mentions: {sum(1 for p in positions if p == 0)}")

position_analysis("Nike")
```

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

    # Aggregate by provider
    provider_stats = defaultdict(lambda: {"mentions": 0, "positive": 0, "total": 0})

    for result in report.provider_results:
        provider = result.provider
        for mention in result.mentions:
            if mention.brand_name.lower() == brand.lower():
                provider_stats[provider]["mentions"] += 1
                provider_stats[provider]["total"] += 1
                if mention.sentiment == "positive":
                    provider_stats[provider]["positive"] += 1

    # Display results
    print(f"\n{brand} by Provider:")
    for provider, stats in provider_stats.items():
        if stats["total"] > 0:
            positive_rate = stats["positive"] / stats["total"]
            print(f"\n{provider}:")
            print(f"  Mentions: {stats['mentions']}")
            print(f"  Positive rate: {positive_rate:.0%}")

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
    """Scan with comprehensive error handling."""
    for attempt in range(max_retries):
        try:
            beacon = Beacon(brand).with_providers(Provider.OPENAI)
            report = beacon.scan()
            return report

        except ConfigurationError as e:
            print(f"Configuration error: {e}")
            print("Please set OPENAI_API_KEY")
            return None

        except ProviderAuthenticationError as e:
            print(f"Authentication failed: {e}")
            print("Check your API key")
            return None

        except ProviderRateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Rate limit hit. Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print("Rate limit exceeded after retries")
                return None

        except ProviderAPIError as e:
            if attempt < max_retries - 1:
                print(f"API error: {e}. Retrying...")
                time.sleep(2)
            else:
                print("API error after retries")
                return None

        except ScanError as e:
            print(f"Scan failed: {e}")
            return None

        except Exception as e:
            print(f"Unexpected error: {e}")
            return None

    return None

# Usage
report = robust_scan("Nike")
if report:
    print(f"Score: {report.visibility_score:.1f}")
```

### Fallback Providers

```python
from promptbeacon import Beacon, Provider
from promptbeacon.core.exceptions import ProviderError

def scan_with_fallback(brand: str):
    """Try multiple providers with fallback."""
    providers = [Provider.OPENAI, Provider.ANTHROPIC, Provider.GOOGLE]

    for provider in providers:
        try:
            beacon = Beacon(brand).with_providers(provider)
            report = beacon.scan()
            print(f"Successfully scanned with {provider.value}")
            return report

        except ProviderError as e:
            print(f"{provider.value} failed: {e}")
            continue

    print("All providers failed")
    return None

report = scan_with_fallback("Nike")
```

---

## Performance Optimization

### Caching Results

```python
from functools import lru_cache
from promptbeacon import Beacon
import hashlib
import json

class CachedBeacon:
    """Beacon with result caching."""

    def __init__(self, cache_ttl: int = 3600):
        self.cache_ttl = cache_ttl
        self._cache = {}

    def scan(self, brand: str, **kwargs) -> dict:
        """Scan with caching."""
        cache_key = self._make_key(brand, **kwargs)

        if cache_key in self._cache:
            cached_time, result = self._cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                print(f"Cache hit for {brand}")
                return result

        # Cache miss - perform scan
        beacon = Beacon(brand)
        for key, value in kwargs.items():
            if hasattr(beacon, f"with_{key}"):
                method = getattr(beacon, f"with_{key}")
                beacon = method(value)

        report = beacon.scan()
        self._cache[cache_key] = (time.time(), report)

        return report

    def _make_key(self, brand: str, **kwargs) -> str:
        """Generate cache key."""
        data = {"brand": brand, **kwargs}
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(json_str.encode()).hexdigest()

# Usage
cached_beacon = CachedBeacon(cache_ttl=3600)  # 1 hour cache

# First call - cache miss
report1 = cached_beacon.scan("Nike")

# Second call - cache hit (if within 1 hour)
report2 = cached_beacon.scan("Nike")
```

### Parallel Processing with multiprocessing

```python
from multiprocessing import Pool
from promptbeacon import Beacon

def scan_brand(brand: str) -> tuple[str, float]:
    """Scan a single brand."""
    beacon = Beacon(brand)
    report = beacon.scan()
    return brand, report.visibility_score

def parallel_scan(brands: list[str], num_workers: int = 4):
    """Scan brands in parallel using multiprocessing."""
    with Pool(processes=num_workers) as pool:
        results = pool.map(scan_brand, brands)

    return dict(results)

# Usage
brands = ["Nike", "Adidas", "Puma", "New Balance", "Under Armour"]
scores = parallel_scan(brands, num_workers=4)

for brand, score in scores.items():
    print(f"{brand}: {score:.1f}")
```

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

    # Format message
    message = f"""
    *Visibility Report: {brand}*

    Score: *{report.visibility_score:.1f}/100*
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

# Usage
send_to_slack("https://hooks.slack.com/services/YOUR/WEBHOOK/URL", "Nike")
```

### API Endpoint

```python
from fastapi import FastAPI, BackgroundTasks
from promptbeacon import Beacon
from pydantic import BaseModel

app = FastAPI()

class ScanRequest(BaseModel):
    brand: str
    competitors: list[str] = []
    prompt_count: int = 10

class ScanResponse(BaseModel):
    brand: str
    visibility_score: float
    mention_count: int
    sentiment_positive: float

@app.post("/scan", response_model=ScanResponse)
async def scan_brand(request: ScanRequest):
    """API endpoint for brand scanning."""
    beacon = Beacon(request.brand)

    if request.competitors:
        beacon = beacon.with_competitors(*request.competitors)

    beacon = beacon.with_prompt_count(request.prompt_count)

    report = await beacon.scan_async()

    return ScanResponse(
        brand=report.brand,
        visibility_score=report.visibility_score,
        mention_count=report.mention_count,
        sentiment_positive=report.sentiment_breakdown.positive,
    )

# Run with: uvicorn script:app --reload
```

### Dashboard Integration

```python
from promptbeacon import Beacon
import streamlit as st
import plotly.graph_objects as go

def create_dashboard(brand: str):
    """Create interactive dashboard with Streamlit."""
    st.title(f"{brand} Visibility Dashboard")

    # Sidebar configuration
    competitors = st.sidebar.text_input("Competitors (comma-separated)").split(",")
    prompt_count = st.sidebar.slider("Prompts per category", 5, 50, 10)

    if st.sidebar.button("Run Scan"):
        with st.spinner("Scanning..."):
            beacon = Beacon(brand).with_storage("~/.promptbeacon/data.db")

            if competitors and competitors[0]:
                beacon = beacon.with_competitors(*competitors)

            beacon = beacon.with_prompt_count(prompt_count)
            report = beacon.scan()

            # Display score
            st.metric("Visibility Score", f"{report.visibility_score:.1f}")

            # Sentiment chart
            fig = go.Figure(data=[
                go.Bar(
                    x=["Positive", "Neutral", "Negative"],
                    y=[
                        report.sentiment_breakdown.positive,
                        report.sentiment_breakdown.neutral,
                        report.sentiment_breakdown.negative,
                    ]
                )
            ])
            st.plotly_chart(fig)

            # Historical trend
            history = beacon.get_history(days=30)
            if history.data_points:
                dates = [dp.timestamp for dp in history.data_points]
                scores = [dp.visibility_score for dp in history.data_points]

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=dates, y=scores, mode="lines+markers"))
                st.plotly_chart(fig)

# Run with: streamlit run script.py
create_dashboard("Nike")
```

---

## Custom Scoring

### Weighted Scoring

```python
from promptbeacon import Beacon

def custom_weighted_score(report) -> float:
    """Calculate custom weighted visibility score."""
    weights = {
        "visibility": 0.4,
        "sentiment": 0.3,
        "position": 0.2,
        "recommendations": 0.1,
    }

    # Base visibility
    visibility_component = report.visibility_score * weights["visibility"]

    # Sentiment component
    sentiment_score = (
        report.sentiment_breakdown.positive * 100
        - report.sentiment_breakdown.negative * 50
    )
    sentiment_component = sentiment_score * weights["sentiment"]

    # Position component (lower is better)
    avg_position = report.metrics.average_position or 5.0
    position_score = max(0, 100 - (avg_position * 10))
    position_component = position_score * weights["position"]

    # Recommendations component
    rec_rate = report.metrics.recommendation_rate * 100
    rec_component = rec_rate * weights["recommendations"]

    total = (
        visibility_component +
        sentiment_component +
        position_component +
        rec_component
    )

    return round(total, 1)

# Usage
beacon = Beacon("Nike")
report = beacon.scan()

standard_score = report.visibility_score
custom_score = custom_weighted_score(report)

print(f"Standard score: {standard_score:.1f}")
print(f"Custom score: {custom_score:.1f}")
```

### Category-Specific Scoring

```python
def category_specific_analysis(brand: str, categories: list[str]):
    """Analyze brand with category-specific scoring."""
    scores = {}

    for category in categories:
        beacon = (
            Beacon(brand)
            .with_categories(category)
            .with_prompt_count(15)
        )

        report = beacon.scan()

        # Custom scoring per category
        if "price" in category.lower() or "value" in category.lower():
            # For price categories, weight sentiment higher
            score = (
                report.visibility_score * 0.3 +
                report.sentiment_breakdown.positive * 70
            )
        elif "quality" in category.lower():
            # For quality, weight recommendations higher
            score = (
                report.visibility_score * 0.4 +
                report.metrics.recommendation_rate * 60
            )
        else:
            score = report.visibility_score

        scores[category] = round(score, 1)

    return scores

# Usage
categories = ["product quality", "pricing value", "customer service"]
scores = category_specific_analysis("Nike", categories)

for category, score in scores.items():
    print(f"{category}: {score:.1f}")
```

---

## See Also

- [API Reference](api-reference.md) - Complete API documentation
- [Examples](examples.md) - Real-world usage examples
- [Storage Guide](storage.md) - Advanced data management
- [Provider Configuration](providers.md) - Provider optimization
