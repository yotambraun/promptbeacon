# Provider Configuration Guide

PromptBeacon supports 6 LLM providers through LiteLLM. This guide covers setup, configuration, and best practices for each provider.

## Supported Providers

| Provider | Default Model | API Key Required | Env Variable |
|----------|---------------|------------------|--------------|
| OpenAI | gpt-4o-mini | Yes | `OPENAI_API_KEY` |
| Anthropic | claude-3-5-haiku-20241022 | Yes | `ANTHROPIC_API_KEY` |
| Google | gemini-2.0-flash | Yes | `GOOGLE_API_KEY` |
| Mistral | mistral-small-latest | Yes | `MISTRAL_API_KEY` |
| Cohere | command-r | Yes | `COHERE_API_KEY` |
| Perplexity | sonar | Yes | `PERPLEXITY_API_KEY` |

## Quick Setup

### Check Provider Status

```bash
promptbeacon providers
```

This shows which providers are configured and which need setup.

### Set API Keys

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Google
export GOOGLE_API_KEY="..."

# Mistral
export MISTRAL_API_KEY="..."

# Cohere
export COHERE_API_KEY="..."

# Perplexity
export PERPLEXITY_API_KEY="pplx-..."
```

### Verify Configuration

```python
from promptbeacon.core.config import has_api_key, Provider

for provider in Provider:
    status = "configured" if has_api_key(provider) else "not configured"
    print(f"{provider.value}: {status}")
```

---

## OpenAI

### Setup

1. **Get API Key**: Visit [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. **Create new secret key**
3. **Set environment variable**:

```bash
export OPENAI_API_KEY="sk-proj-..."
```

For persistence, add to `~/.bashrc` or `~/.zshrc`:

```bash
echo 'export OPENAI_API_KEY="sk-proj-..."' >> ~/.bashrc
source ~/.bashrc
```

### Default Model

```python
# Default: gpt-4o-mini
Provider.OPENAI  # Uses gpt-4o-mini
```

### Available Models

- `gpt-4o` - Most capable, higher cost
- `gpt-4o-mini` - Default, balanced performance/cost
- `gpt-4-turbo` - Fast, capable
- `gpt-3.5-turbo` - Fastest, lowest cost

### Usage

```python
from promptbeacon import Beacon, Provider

beacon = Beacon("Nike").with_providers(Provider.OPENAI)
report = beacon.scan()
```

### Rate Limits

**Free Tier:**
- 3 RPM (requests per minute)
- 200 RPD (requests per day)

**Tier 1 ($5+ spent):**
- 500 RPM
- 10,000 RPD

**Tier 2 ($50+ spent):**
- 5,000 RPM
- 1,500,000 RPD

### Cost Estimates

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Typical scan cost |
|-------|----------------------|------------------------|-------------------|
| gpt-4o-mini | $0.15 | $0.60 | $0.01-0.03 |
| gpt-4o | $2.50 | $10.00 | $0.15-0.30 |
| gpt-3.5-turbo | $0.50 | $1.50 | $0.03-0.05 |

### Troubleshooting

**401 Unauthorized**
```bash
# Invalid API key
export OPENAI_API_KEY="sk-proj-..."  # Double-check key
```

**429 Rate Limit**
```python
# Reduce concurrent requests
beacon = Beacon("Nike").with_prompt_count(5)
```

**Billing Issues**
- Ensure you have credits: [platform.openai.com/settings/organization/billing](https://platform.openai.com/settings/organization/billing)
- Add payment method if needed

---

## Anthropic (Claude)

### Setup

1. **Get API Key**: Visit [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
2. **Create key**
3. **Set environment variable**:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

For persistence:

```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.bashrc
source ~/.bashrc
```

### Default Model

```python
# Default: claude-3-5-haiku-20241022
Provider.ANTHROPIC  # Uses Claude 3.5 Haiku
```

### Available Models

- `claude-3-5-haiku-20241022` - Default, fast and economical
- `claude-3-5-sonnet-20241022` - High performance, balanced
- `claude-3-opus-20240229` - Most capable, highest cost

### Usage

```python
from promptbeacon import Beacon, Provider

beacon = Beacon("Nike").with_providers(Provider.ANTHROPIC)
report = beacon.scan()
```

### Rate Limits

**Free Tier:**
- 5 RPM
- 1,000 RPD

**Tier 1:**
- 50 RPM
- 10,000 RPD

**Tier 2:**
- 1,000 RPM
- 100,000 RPD

### Cost Estimates

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Typical scan cost |
|-------|----------------------|------------------------|-------------------|
| Claude 3.5 Haiku | $1.00 | $5.00 | $0.03-0.06 |
| Claude 3.5 Sonnet | $3.00 | $15.00 | $0.20-0.40 |
| Claude 3 Opus | $15.00 | $75.00 | $1.00-2.00 |

### Troubleshooting

**401 Authentication Error**
```bash
# Verify API key format (should start with sk-ant-)
echo $ANTHROPIC_API_KEY
```

**429 Rate Limit**
```python
# Reduce request rate
beacon = (
    Beacon("Nike")
    .with_providers(Provider.ANTHROPIC)
    .with_prompt_count(3)  # Reduce from default 10
)
```

**Billing Required**
- Some accounts require billing setup even for free tier
- Visit [console.anthropic.com/settings/billing](https://console.anthropic.com/settings/billing)

---

## Google (Gemini)

### Setup

1. **Get API Key**: Visit [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. **Create API key**
3. **Set environment variable**:

```bash
export GOOGLE_API_KEY="..."
```

For persistence:

```bash
echo 'export GOOGLE_API_KEY="..."' >> ~/.bashrc
source ~/.bashrc
```

### Default Model

```python
# Default: gemini-2.0-flash
Provider.GOOGLE  # Uses Gemini 2.0 Flash
```

### Available Models

- `gemini-2.0-flash` - Default, fast and efficient
- `gemini-1.5-pro` - More capable, higher cost

### Usage

```python
from promptbeacon import Beacon, Provider

beacon = Beacon("Nike").with_providers(Provider.GOOGLE)
report = beacon.scan()
```

### Rate Limits

**Free Tier:**
- 15 RPM
- 1,500 RPD

**Paid:**
- 2,000 RPM
- Much higher daily limits

### Cost Estimates

**Free Tier (First 1,500 requests/day):**
- No cost up to limits

**Paid Tier:**

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Typical scan cost |
|-------|----------------------|------------------------|-------------------|
| Gemini 2.0 Flash | $0.075 | $0.30 | $0.005-0.015 |
| Gemini 1.5 Pro | $1.25 | $5.00 | $0.08-0.15 |

### Troubleshooting

**400 Bad Request**
```python
# Some requests may fail due to content policy
# This is normal; PromptBeacon handles gracefully
```

**429 Quota Exceeded**
```bash
# Free tier daily quota reached
# Wait 24 hours or upgrade to paid tier
```

**API Key Issues**
```bash
# Ensure no extra spaces
export GOOGLE_API_KEY="AIza..."
```

---

## Mistral

### Setup

1. **Get API Key**: Visit [console.mistral.ai/api-keys](https://console.mistral.ai/api-keys)
2. **Create key**
3. **Set environment variable**:

```bash
export MISTRAL_API_KEY="..."
```

### Default Model

```python
# Default: mistral-small-latest
Provider.MISTRAL  # Uses Mistral Small
```

### Available Models

- `mistral-small-latest` - Default, fast and affordable
- `mistral-medium-latest` - Balanced performance
- `mistral-large-latest` - Most capable

### Usage

```python
from promptbeacon import Beacon, Provider

beacon = Beacon("Nike").with_providers(Provider.MISTRAL)
report = beacon.scan()
```

### Cost Estimates

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Typical scan cost |
|-------|----------------------|------------------------|-------------------|
| Mistral Small | $0.20 | $0.60 | $0.01-0.03 |
| Mistral Large | $2.00 | $6.00 | $0.10-0.20 |

---

## Cohere

### Setup

1. **Get API Key**: Visit [dashboard.cohere.com/api-keys](https://dashboard.cohere.com/api-keys)
2. **Create key**
3. **Set environment variable**:

```bash
export COHERE_API_KEY="..."
```

### Default Model

```python
# Default: command-r
Provider.COHERE  # Uses Command R
```

### Available Models

- `command-r` - Default, good general purpose
- `command-r-plus` - More capable, higher cost

### Usage

```python
from promptbeacon import Beacon, Provider

beacon = Beacon("Nike").with_providers(Provider.COHERE)
report = beacon.scan()
```

### Cost Estimates

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Typical scan cost |
|-------|----------------------|------------------------|-------------------|
| Command R | $0.15 | $0.60 | $0.01-0.03 |
| Command R+ | $2.50 | $10.00 | $0.15-0.30 |

---

## Perplexity

### Setup

1. **Get API Key**: Visit [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api)
2. **Create key**
3. **Set environment variable**:

```bash
export PERPLEXITY_API_KEY="pplx-..."
```

### Default Model

```python
# Default: sonar
Provider.PERPLEXITY  # Uses Sonar
```

### Available Models

- `sonar` - Default, fast with web-grounded responses
- `sonar-pro` - More capable, higher cost

### Usage

```python
from promptbeacon import Beacon, Provider

beacon = Beacon("Nike").with_providers(Provider.PERPLEXITY)
report = beacon.scan()
```

### Why Perplexity?

Perplexity is unique because its models are grounded in real-time web search. This makes it especially valuable for citation tracking — Perplexity responses frequently include URLs and source attributions.

---

## Multi-Provider Strategy

### Using All Providers

```python
from promptbeacon import Beacon, Provider

beacon = (
    Beacon("Nike")
    .with_providers(
        Provider.OPENAI,
        Provider.ANTHROPIC,
        Provider.GOOGLE,
        Provider.MISTRAL,
        Provider.COHERE,
        Provider.PERPLEXITY,
    )
)

report = beacon.scan()
print(f"Providers used: {', '.join(report.providers_used)}")
```

### Provider Selection Strategy

**For Maximum Coverage:**
```python
# Use all available providers
beacon = Beacon("Nike")  # Automatically detects configured providers
```

**For Cost Optimization:**
```python
# Use only free/cheap tier providers
beacon = Beacon("Nike").with_providers(
    Provider.GOOGLE,   # Generous free tier
    Provider.OPENAI,   # gpt-4o-mini is very cheap
    Provider.MISTRAL,  # Affordable
)
```

**For Citation Tracking:**
```python
# Include Perplexity for web-grounded citations
beacon = Beacon("Nike").with_providers(
    Provider.OPENAI,
    Provider.PERPLEXITY,  # Best for citations
)
```

### Automatic Provider Selection

PromptBeacon automatically uses only configured providers:

```python
# If only OPENAI_API_KEY is set, only OpenAI will be used
beacon = Beacon("Nike")  # Automatically detects available providers
report = beacon.scan()
```

---

## Environment Setup

### Development Environment

Create `.env` file in project root:

```bash
# .env
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
MISTRAL_API_KEY=...
COHERE_API_KEY=...
PERPLEXITY_API_KEY=pplx-...
```

Load with python-dotenv:

```python
from dotenv import load_dotenv
load_dotenv()

from promptbeacon import Beacon

beacon = Beacon("Nike")
report = beacon.scan()
```

### Production Environment

**Docker:**

```dockerfile
FROM python:3.11-slim

ENV OPENAI_API_KEY=${OPENAI_API_KEY}
ENV ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
ENV GOOGLE_API_KEY=${GOOGLE_API_KEY}

RUN pip install promptbeacon

CMD ["promptbeacon", "scan", "Nike"]
```

**Kubernetes:**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: promptbeacon-secrets
type: Opaque
stringData:
  openai-key: sk-proj-...
  anthropic-key: sk-ant-...
  google-key: ...
---
apiVersion: v1
kind: Pod
metadata:
  name: promptbeacon
spec:
  containers:
  - name: scanner
    image: promptbeacon:latest
    env:
    - name: OPENAI_API_KEY
      valueFrom:
        secretKeyRef:
          name: promptbeacon-secrets
          key: openai-key
    - name: ANTHROPIC_API_KEY
      valueFrom:
        secretKeyRef:
          name: promptbeacon-secrets
          key: anthropic-key
    - name: GOOGLE_API_KEY
      valueFrom:
        secretKeyRef:
          name: promptbeacon-secrets
          key: google-key
```

### CI/CD Environment

**GitHub Actions:**

```yaml
name: Brand Scan

on:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install PromptBeacon
        run: pip install promptbeacon
      - name: Run Scan
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
        run: promptbeacon scan "Nike" --format json > report.json
      - name: Upload Report
        uses: actions/upload-artifact@v3
        with:
          name: scan-report
          path: report.json
```

---

## Cost Management

### Estimating Costs

```python
from promptbeacon import Beacon

beacon = Beacon("Nike").with_prompt_count(10)
report = beacon.scan()

if report.total_cost_usd:
    print(f"Scan cost: ${report.total_cost_usd:.4f}")
    print(f"Monthly (daily scans): ${report.total_cost_usd * 30:.2f}")
```

### Cost Optimization Tips

1. **Start with free tiers**: Use gpt-4o-mini, gemini-2.0-flash, mistral-small
2. **Enable caching**: `.with_cache()` skips duplicate queries automatically
3. **Reduce prompt count**: Lower from default 10 to 5-7 per category
4. **Use industry templates**: `.with_industry("ecommerce")` generates relevant prompts
5. **Use fewer categories**: Focus on most important topics
6. **Limit providers**: Use 1-2 providers instead of all 6

**Example: Cost-Optimized Configuration**

```python
beacon = (
    Beacon("Nike")
    .with_providers(Provider.GOOGLE)  # Free tier
    .with_categories("running shoes")  # Single category
    .with_prompt_count(5)             # Reduced prompts
    .with_cache()                     # Cache responses
    .with_temperature(0.5)            # Lower temperature
)
```

### Budget Alerts

Track costs programmatically:

```python
MONTHLY_BUDGET = 10.00  # $10/month
daily_budget = MONTHLY_BUDGET / 30

report = beacon.scan()

if report.total_cost_usd and report.total_cost_usd > daily_budget:
    print(f"WARNING: Daily budget exceeded!")
    print(f"Cost: ${report.total_cost_usd:.4f}")
    print(f"Budget: ${daily_budget:.4f}")
```

---

## Rate Limit Handling

### Built-in Retry Logic

PromptBeacon automatically retries failed requests:

```python
# Default: 3 retries with exponential backoff
beacon = Beacon("Nike")  # Uses max_retries=3 by default
```

### Rate Limit Best Practices

1. **Concurrent requests**: Default is 5, increase cautiously
2. **Prompt count**: Reduce if hitting limits frequently
3. **Multiple providers**: Distribute load across providers
4. **Caching**: Enable `.with_cache()` to avoid duplicate queries
5. **Timing**: Schedule scans during off-peak hours

**Example: Rate-Limit Friendly Configuration**

```python
beacon = (
    Beacon("Nike")
    .with_providers(Provider.OPENAI, Provider.ANTHROPIC, Provider.MISTRAL)  # Split load
    .with_prompt_count(8)
    .with_cache()  # Don't re-query cached responses
)
```

---

## Provider-Specific Features

### OpenAI

**Strengths:**
- Most widely used and tested
- Consistent response quality
- Good for general recommendations

**Best for:**
- General brand mentions
- Broad category analysis
- High-volume scanning (with paid tier)

### Anthropic (Claude)

**Strengths:**
- Excellent reasoning capabilities
- Detailed, thoughtful responses
- Good context understanding

**Best for:**
- Nuanced sentiment analysis
- Competitive comparisons
- Complex category analysis

### Google (Gemini)

**Strengths:**
- Generous free tier
- Fast response times
- Good cost-to-quality ratio

**Best for:**
- High-frequency monitoring
- Cost-sensitive applications
- Development and testing

### Mistral

**Strengths:**
- Very affordable pricing
- Fast response times
- Good European language support

**Best for:**
- Cost-sensitive scanning
- European market analysis
- Multilingual brand tracking

### Cohere

**Strengths:**
- Strong retrieval-augmented generation
- Good for factual queries
- Competitive pricing

**Best for:**
- Factual brand queries
- Knowledge-based analysis

### Perplexity

**Strengths:**
- Web-grounded responses with real-time data
- Frequently includes URLs and source citations
- Combines search with generation

**Best for:**
- Citation tracking (strongest provider for this)
- Real-time brand monitoring
- Source attribution analysis

---

## Testing Provider Setup

### Quick Test Script

```python
from promptbeacon import Beacon, Provider
from promptbeacon.core.config import has_api_key

def test_providers():
    """Test all configured providers."""
    for provider in Provider:
        if not has_api_key(provider):
            print(f"{provider.value}: Not configured")
            continue

        print(f"Testing {provider.value}...")
        try:
            beacon = Beacon("Test Brand").with_providers(provider)
            beacon = beacon.with_prompt_count(1)  # Single prompt test
            report = beacon.scan()

            print(f"  Success")
            print(f"  Mentions: {report.mention_count}")
            if report.total_cost_usd:
                print(f"  Cost: ${report.total_cost_usd:.4f}")
        except Exception as e:
            print(f"  Failed: {e}")

if __name__ == "__main__":
    test_providers()
```

### CLI Test

```bash
# Test each provider individually
promptbeacon scan "Test" --provider openai --prompts 1
promptbeacon scan "Test" --provider anthropic --prompts 1
promptbeacon scan "Test" --provider google --prompts 1
promptbeacon scan "Test" --provider mistral --prompts 1
promptbeacon scan "Test" --provider cohere --prompts 1
promptbeacon scan "Test" --provider perplexity --prompts 1
```

---

## Security Best Practices

### API Key Management

**DO:**
- Use environment variables
- Use secrets management (AWS Secrets Manager, HashiCorp Vault)
- Rotate keys regularly
- Use separate keys for dev/staging/prod
- Restrict key permissions (if provider supports)

**DON'T:**
- Commit keys to git
- Share keys in plain text
- Use production keys in development
- Log API keys
- Store in unencrypted configuration files

### .gitignore

Ensure these are in `.gitignore`:

```gitignore
.env
.env.local
.env.*.local
*.key
secrets/
```

---

## See Also

- [API Reference](api-reference.md) - Complete API documentation
- [Quickstart Guide](quickstart.md) - Getting started
- [Storage Guide](storage.md) - Historical tracking
- [Advanced Usage](advanced.md) - Custom configurations
