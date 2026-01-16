# Provider Configuration Guide

PromptBeacon supports multiple LLM providers through LiteLLM. This guide covers setup, configuration, and best practices for each provider.

## Supported Providers

| Provider | Models | API Key Required | Rate Limits |
|----------|--------|------------------|-------------|
| OpenAI | GPT-4, GPT-3.5 | Yes | 10,000 RPM (free tier) |
| Anthropic | Claude 3 family | Yes | 50 RPM (free tier) |
| Google | Gemini 1.5 | Yes | 60 RPM (free tier) |

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
```

### Verify Configuration

```python
from promptbeacon.core.config import has_api_key, Provider

print(f"OpenAI: {has_api_key(Provider.OPENAI)}")
print(f"Anthropic: {has_api_key(Provider.ANTHROPIC)}")
print(f"Google: {has_api_key(Provider.GOOGLE)}")
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
# Default: claude-3-haiku-20240307
Provider.ANTHROPIC  # Uses Claude 3 Haiku
```

### Available Models

- `claude-3-opus-20240229` - Most capable, highest cost
- `claude-3-sonnet-20240229` - Balanced performance
- `claude-3-haiku-20240307` - Default, fast and economical
- `claude-3-5-sonnet-20241022` - Latest, high performance

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
| Claude 3 Haiku | $0.25 | $1.25 | $0.02-0.04 |
| Claude 3 Sonnet | $3.00 | $15.00 | $0.20-0.40 |
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
# Default: gemini-1.5-flash
Provider.GOOGLE  # Uses Gemini 1.5 Flash
```

### Available Models

- `gemini-1.5-flash` - Default, fast and efficient
- `gemini-1.5-pro` - More capable, higher cost
- `gemini-pro` - Legacy, balanced performance

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
| Gemini 1.5 Flash | $0.075 | $0.30 | $0.005-0.015 |
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

## Multi-Provider Strategy

### Using All Providers

```python
from promptbeacon import Beacon, Provider

beacon = (
    Beacon("Nike")
    .with_providers(
        Provider.OPENAI,
        Provider.ANTHROPIC,
        Provider.GOOGLE
    )
)

report = beacon.scan()
print(f"Providers used: {', '.join(report.providers_used)}")
```

### Provider Selection Strategy

**For Maximum Coverage:**
```python
# Use all available providers
beacon = Beacon("Nike").with_providers(*Provider.all())
```

**For Cost Optimization:**
```python
# Use only free tier providers
beacon = Beacon("Nike").with_providers(
    Provider.OPENAI,  # gpt-4o-mini
    Provider.GOOGLE   # gemini-1.5-flash
)
```

**For Quality:**
```python
# Use higher-tier models (requires custom configuration)
# Note: Default PromptBeacon uses optimized defaults
beacon = Beacon("Nike").with_providers(
    Provider.OPENAI,   # Will use gpt-4o-mini
    Provider.ANTHROPIC # Will use claude-3-haiku
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

1. **Start with free tiers**: Use gpt-4o-mini, claude-3-haiku, gemini-1.5-flash
2. **Reduce prompt count**: Lower from default 10 to 5-7 per category
3. **Use fewer categories**: Focus on most important topics
4. **Limit providers**: Use 1-2 providers instead of all 3
5. **Reduce temperature**: Lower temperature = fewer tokens

**Example: Cost-Optimized Configuration**

```python
beacon = (
    Beacon("Nike")
    .with_providers(Provider.GOOGLE)  # Free tier
    .with_categories("running shoes")  # Single category
    .with_prompt_count(5)             # Reduced prompts
    .with_temperature(0.5)            # Lower temperature
    .with_max_tokens(512)             # Reduced max tokens
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

### Custom Retry Configuration

```python
from promptbeacon.core.config import BeaconConfig

# Currently not directly configurable via fluent API
# Uses sensible defaults: 3 retries, 30s timeout
```

### Rate Limit Best Practices

1. **Concurrent requests**: Default is 5, increase cautiously
2. **Prompt count**: Reduce if hitting limits frequently
3. **Multiple providers**: Distribute load across providers
4. **Timing**: Schedule scans during off-peak hours

**Example: Rate-Limit Friendly Configuration**

```python
beacon = (
    Beacon("Nike")
    .with_providers(Provider.OPENAI, Provider.ANTHROPIC)  # Split load
    .with_prompt_count(8)                                 # Slightly reduced
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

---

## Testing Provider Setup

### Quick Test Script

```python
from promptbeacon import Beacon, Provider
from promptbeacon.core.config import has_api_key

def test_providers():
    """Test all configured providers."""
    providers = [
        Provider.OPENAI,
        Provider.ANTHROPIC,
        Provider.GOOGLE
    ]

    for provider in providers:
        if not has_api_key(provider):
            print(f"{provider.value}: Not configured")
            continue

        print(f"Testing {provider.value}...")
        try:
            beacon = Beacon("Test Brand").with_providers(provider)
            beacon = beacon.with_prompt_count(1)  # Single prompt test
            report = beacon.scan()

            print(f"  ✓ Success")
            print(f"  Mentions: {report.mention_count}")
            if report.total_cost_usd:
                print(f"  Cost: ${report.total_cost_usd:.4f}")
        except Exception as e:
            print(f"  ✗ Failed: {e}")

if __name__ == "__main__":
    test_providers()
```

### CLI Test

```bash
# Test each provider
promptbeacon scan "Test" --provider openai --prompts 1
promptbeacon scan "Test" --provider anthropic --prompts 1
promptbeacon scan "Test" --provider google --prompts 1
```

---

## Security Best Practices

### API Key Management

**DO:**
- ✓ Use environment variables
- ✓ Use secrets management (AWS Secrets Manager, HashiCorp Vault)
- ✓ Rotate keys regularly
- ✓ Use separate keys for dev/staging/prod
- ✓ Restrict key permissions (if provider supports)

**DON'T:**
- ✗ Commit keys to git
- ✗ Share keys in plain text
- ✗ Use production keys in development
- ✗ Log API keys
- ✗ Store in unencrypted configuration files

### .gitignore

Ensure these are in `.gitignore`:

```gitignore
.env
.env.local
.env.*.local
*.key
secrets/
```

### Secure Loading

```python
import os
from pathlib import Path

def load_secure_config():
    """Load config from secure location."""
    config_path = Path.home() / ".config" / "promptbeacon" / "config.env"

    if config_path.exists():
        with open(config_path) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

load_secure_config()
```

---

## Migration Guide

### From OpenAI Only to Multi-Provider

```python
# Before
beacon = Beacon("Nike")  # Uses OpenAI by default

# After
from promptbeacon import Provider

beacon = (
    Beacon("Nike")
    .with_providers(
        Provider.OPENAI,
        Provider.ANTHROPIC,
        Provider.GOOGLE
    )
)
```

### Changing Default Provider

```python
# Use Anthropic as primary
beacon = Beacon("Nike").with_providers(Provider.ANTHROPIC)

# Use multiple with preference order
# (all are queried, order doesn't matter for results)
beacon = Beacon("Nike").with_providers(
    Provider.ANTHROPIC,  # Query all
    Provider.OPENAI,
    Provider.GOOGLE
)
```

---

## See Also

- [API Reference](api-reference.md) - Complete API documentation
- [Quickstart Guide](quickstart.md) - Getting started
- [Storage Guide](storage.md) - Historical tracking
- [Advanced Usage](advanced.md) - Custom configurations
