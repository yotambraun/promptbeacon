# CLI Reference

Complete command-line interface reference for PromptBeacon. The CLI provides full access to all functionality for automation, scripting, and quick analysis.

## Installation Verification

After installing PromptBeacon, verify CLI access:

```bash
promptbeacon --help
```

## Global Options

All commands support these options:

- `--help`: Show help message and exit
- `--version`: Show version and exit

## Commands

- [`quick`](#quick) - Fast 3-prompt scan with cheapest provider
- [`scan`](#scan) - Run a full brand visibility scan
- [`compare`](#compare) - Compare brand against competitors
- [`history`](#history) - View historical visibility data
- [`providers`](#providers) - List available providers and status

---

## `quick`

Run a fast 3-prompt scan with the cheapest available provider. Great for a quick check before running a full scan.

### Usage

```bash
promptbeacon quick BRAND [OPTIONS]
```

### Arguments

- `BRAND` (required): The brand name to analyze

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--format` | `-f` | TEXT | text | Output format: text, json, markdown |

### Examples

```bash
# Quick check
promptbeacon quick "Nike"

# Quick check with JSON output
promptbeacon quick "Nike" --format json
```

---

## `scan`

Run a visibility scan for a brand.

### Usage

```bash
promptbeacon scan BRAND [OPTIONS]
```

### Arguments

- `BRAND` (required): The brand name to analyze

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--competitor` | `-c` | TEXT | None | Competitor brand (can be used multiple times) |
| `--provider` | `-p` | TEXT | None | LLM provider: openai, anthropic, google, mistral, cohere, perplexity (can be used multiple times) |
| `--category` | `-t` | TEXT | None | Category/topic to analyze (can be used multiple times) |
| `--prompts` | `-n` | INT | 10 | Number of prompts per category |
| `--storage` | `-s` | PATH | None | Path to DuckDB storage file |
| `--format` | `-f` | TEXT | text | Output format: text, json, markdown |

### Examples

#### Basic Scan

```bash
promptbeacon scan "Nike"
```

Output:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Visibility Score: Nike
Generated: 2026-02-06 10:30:00
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         73.5 / 100

           Metrics
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Metric             ┃ Value       ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Total Mentions     │ 42          │
│ Positive Sentiment │ 67.0%       │
│ Neutral Sentiment  │ 28.0%       │
│ Negative Sentiment │ 5.0%        │
│ Providers Used     │ openai      │
│ Scan Duration      │ 12.3s       │
│ Estimated Cost     │ $0.0145     │
└────────────────────┴─────────────┘

  Score Breakdown (0-100 per factor, before weighting)
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Factor                ┃ Score  ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ Mention Frequency     │ 80.0   │
│ Sentiment             │ 75.5   │
│ Position / Prominence │ 68.2   │
│ Recommendation Rate   │ 65.0   │
└───────────────────────┴────────┘

Key Insights:
  ● Brand is mentioned prominently across all queries.

Recommendations:
  [HIGH] Increase presence in "athletic wear" queries.

Sources Cited:
  • nike.com [Nike]
  • runnersworld.com [Nike]
```

#### With Competitors

```bash
promptbeacon scan "Nike" \
  --competitor "Adidas" \
  --competitor "Puma" \
  --competitor "New Balance"
```

#### Multiple Providers

```bash
promptbeacon scan "Nike" \
  --provider openai \
  --provider anthropic \
  --provider google \
  --provider mistral
```

#### Custom Categories

```bash
promptbeacon scan "Nike" \
  --category "running shoes" \
  --category "athletic wear" \
  --category "sports brand"
```

#### Increased Prompt Count

```bash
promptbeacon scan "Nike" --prompts 25
```

#### With Storage

```bash
promptbeacon scan "Nike" \
  --storage ~/.promptbeacon/nike.db
```

#### JSON Output

```bash
promptbeacon scan "Nike" --format json > report.json
```

#### Markdown Output

```bash
promptbeacon scan "Nike" --format markdown > report.md
```

#### Complete Example

```bash
promptbeacon scan "Nike" \
  --competitor "Adidas" \
  --competitor "Puma" \
  --provider openai \
  --provider anthropic \
  --provider mistral \
  --category "running shoes" \
  --category "athletic wear" \
  --prompts 20 \
  --storage ~/.promptbeacon/nike.db \
  --format text
```

---

## `compare`

Compare a brand against competitors with side-by-side results.

### Usage

```bash
promptbeacon compare BRAND --against COMPETITOR [OPTIONS]
```

### Arguments

- `BRAND` (required): The brand name to analyze

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--against` | `-a` | TEXT | required | Competitor brand (can be used multiple times, at least one required) |
| `--provider` | `-p` | TEXT | None | LLM provider (can be used multiple times) |
| `--format` | `-f` | TEXT | text | Output format: text, json, markdown |

### Examples

#### Basic Comparison

```bash
promptbeacon compare "Nike" --against "Adidas"
```

Output includes competitor comparison table:
```
        Competitor Comparison
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┓
┃ Brand       ┃ Visibility Score ┃ Mentions ┃ Positive % ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━┩
│ Nike        │ 73.5            │ 42      │ 67%       │
│ Adidas      │ 68.2            │ 38      │ 64%       │
└─────────────┴─────────────────┴─────────┴───────────┘
```

#### Multiple Competitors

```bash
promptbeacon compare "Nike" \
  --against "Adidas" \
  --against "Puma" \
  --against "New Balance" \
  --against "Under Armour"
```

#### With Specific Providers

```bash
promptbeacon compare "Nike" \
  --against "Adidas" \
  --provider openai \
  --provider anthropic
```

#### JSON Export

```bash
promptbeacon compare "Nike" \
  --against "Adidas" \
  --against "Puma" \
  --format json > comparison.json
```

---

## `history`

View historical visibility data and trends.

### Usage

```bash
promptbeacon history BRAND [OPTIONS]
```

### Arguments

- `BRAND` (required): The brand name

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--days` | `-d` | INT | 30 | Number of days of history |
| `--storage` | `-s` | PATH | ~/.promptbeacon/data.db | Path to DuckDB storage file |
| `--format` | `-f` | TEXT | text | Output format: text, json |

### Examples

#### View 30-Day History

```bash
promptbeacon history "Nike"
```

#### Custom Time Range

```bash
promptbeacon history "Nike" --days 90
```

#### Custom Storage Location

```bash
promptbeacon history "Nike" \
  --storage /data/promptbeacon/nike.db \
  --days 60
```

#### JSON Export

```bash
promptbeacon history "Nike" --format json > history.json
```

---

## `providers`

List available LLM providers and their configuration status.

### Usage

```bash
promptbeacon providers
```

### Examples

```bash
promptbeacon providers
```

Output:
```
         Available Providers
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Provider   ┃ Status           ┃ Environment Variable   ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ openai     │ ✓ Configured     │ OPENAI_API_KEY         │
│ anthropic  │ ✓ Configured     │ ANTHROPIC_API_KEY      │
│ google     │ ✓ Configured     │ GOOGLE_API_KEY         │
│ mistral    │ ✗ Not configured │ MISTRAL_API_KEY        │
│ cohere     │ ✗ Not configured │ COHERE_API_KEY         │
│ perplexity │ ✗ Not configured │ PERPLEXITY_API_KEY     │
└────────────┴──────────────────┴────────────────────────┘
```

---

## Output Formats

### Text Format (Default)

Rich formatted output with tables, colors, score breakdown, and visual hierarchy. Best for terminal display.

```bash
promptbeacon scan "Nike"
```

### JSON Format

Machine-readable JSON for parsing and integration.

```bash
promptbeacon scan "Nike" --format json
```

Example output:
```json
{
  "brand": "Nike",
  "visibility_score": 73.5,
  "mention_count": 42,
  "sentiment_breakdown": {
    "positive": 0.67,
    "neutral": 0.28,
    "negative": 0.05
  },
  "citation_summary": {
    "total_citations": 5,
    "unique_domains": ["nike.com", "runnersworld.com"],
    "citations": [...]
  },
  "timestamp": "2026-02-06T10:30:00Z",
  "scan_duration_seconds": 12.3
}
```

### Markdown Format

Formatted Markdown for documentation and reports.

```bash
promptbeacon scan "Nike" --format markdown
```

---

## Automation Examples

### Daily Monitoring Script

```bash
#!/bin/bash
# daily_scan.sh

BRAND="Nike"
DATE=$(date +%Y-%m-%d)
OUTPUT_DIR="./reports"

mkdir -p "$OUTPUT_DIR"

# Run scan with storage
promptbeacon scan "$BRAND" \
  --storage ~/.promptbeacon/nike.db \
  --competitor "Adidas" \
  --competitor "Puma" \
  --provider openai \
  --provider anthropic \
  --prompts 25 \
  --format json > "$OUTPUT_DIR/nike_$DATE.json"

echo "Scan completed: $OUTPUT_DIR/nike_$DATE.json"
```

### Multi-Brand Monitoring

```bash
#!/bin/bash
# multi_brand.sh

BRANDS=("Nike" "Adidas" "Puma" "New Balance")

for brand in "${BRANDS[@]}"; do
    echo "Scanning $brand..."
    promptbeacon scan "$brand" \
      --storage ~/.promptbeacon/data.db \
      --format json > "reports/${brand}_$(date +%Y%m%d).json"
done

echo "All scans completed"
```

### Quick Check Before Full Scan

```bash
#!/bin/bash
# quick_then_full.sh

BRAND="Nike"

echo "Running quick scan..."
promptbeacon quick "$BRAND"

read -p "Run full scan? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Running full scan..."
    promptbeacon scan "$BRAND" \
      --competitor "Adidas" \
      --competitor "Puma" \
      --provider openai \
      --provider anthropic \
      --storage ~/.promptbeacon/nike.db
fi
```

---

## Environment Variables

### Provider API Keys

Required for provider access:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
export MISTRAL_API_KEY="..."
export COHERE_API_KEY="..."
export PERPLEXITY_API_KEY="pplx-..."
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (configuration, scan failure, etc.) |

---

## Integration Examples

### With jq

Process JSON output with jq:

```bash
# Extract visibility score
promptbeacon scan "Nike" --format json | jq '.visibility_score'

# Get competitor scores
promptbeacon compare "Nike" --against "Adidas" --format json | \
  jq '.competitor_comparison | to_entries[] | "\(.key): \(.value.visibility_score)"'

# Filter high-priority recommendations
promptbeacon scan "Nike" --format json | \
  jq '.recommendations[] | select(.priority == "high") | .action'

# List cited sources
promptbeacon scan "Nike" --format json | \
  jq '.citation_summary.citations[] | .source_name'
```

### With curl for API Integration

```bash
# Post results to webhook
REPORT=$(promptbeacon scan "Nike" --format json)

curl -X POST https://api.example.com/reports \
  -H "Content-Type: application/json" \
  -d "$REPORT"
```

---

## Troubleshooting

### Command Not Found

**Problem:** `promptbeacon: command not found`

**Solution:**
```bash
# Ensure package is installed
pip install promptbeacon

# Or with uv
uv add promptbeacon

# Check installation
python -m promptbeacon --help
```

### Provider Not Configured

**Problem:** `Error: No API keys found for configured providers`

**Solution:**
```bash
# Check provider status
promptbeacon providers

# Set missing API keys
export OPENAI_API_KEY="sk-..."
```

### Timeout Errors

**Problem:** Scan times out with many prompts

**Solution:**
```bash
# Use quick scan for a fast check
promptbeacon quick "Nike"

# Or reduce prompt count
promptbeacon scan "Nike" --prompts 5
```

---

## See Also

- [API Reference](api-reference.md) - Python API documentation
- [Examples](examples.md) - Real-world usage patterns
- [Storage Guide](storage.md) - Historical tracking details
- [Provider Configuration](providers.md) - API key setup
