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

- [`demo`](#demo) - Keyless demo scan (no API keys required)
- [`quick`](#quick) - Fast 3-prompt scan with cheapest provider
- [`scan`](#scan) - Run a full brand visibility scan
- [`compare`](#compare) - Compare brand against competitors
- [`sources`](#sources) - Show which source domains AI engines cite for your brand
- [`history`](#history) - View historical visibility data
- [`dashboard`](#dashboard) - Generate HTML dashboard
- [`providers`](#providers) - List available providers and status

---

## `demo`

Run a full demo scan using realistic canned data. No API keys required. This is the recommended first step to explore PromptBeacon's output format.

### Usage

```bash
promptbeacon demo BRAND [OPTIONS]
```

### Arguments

- `BRAND` (required): The brand name to simulate

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--format` | `-f` | TEXT | text | Output format: text, json, markdown |
| `--output` | `-o` | PATH | None | Write output to file instead of stdout |

### Examples

```bash
# Demo scan
promptbeacon demo "Nike"

# Demo with JSON output
promptbeacon demo "Nike" --format json

# Save demo report to file
promptbeacon demo "Nike" --format json -o demo_report.json
```

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
| `--demo` | | FLAG | false | Use demo mode (no API keys required) |

### Examples

```bash
# Quick check
promptbeacon quick "Nike"

# Quick check in demo mode
promptbeacon quick "Nike" --demo

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
| `--competitor` | `-c` | TEXT | None | Competitor brand (repeatable) |
| `--provider` | `-p` | TEXT | None | Provider: openai, anthropic, google, mistral, cohere, perplexity (repeatable) |
| `--category` | `-t` | TEXT | None | Category/topic to analyze (repeatable) |
| `--prompts` | `-n` | INT | 10 | Number of prompts per category |
| `--storage` | `-s` | PATH | None | Path to DuckDB storage file |
| `--format` | `-f` | TEXT | text | Output format: text, json, markdown |
| `--demo` | | FLAG | false | Use demo mode (no API keys required) |
| `--smart` | | FLAG | false | Enable LLM-powered extraction and recommendations |
| `--grounded` | | FLAG | false | Measure web-grounded answers (provider web search) instead of base-model memory — costs more, uses your keys |
| `--stability` | `-r` | INT | None | Number of stability runs (multiplies API cost) |
| `--assert-min-score` | | FLOAT | None | Fail (exit 1) if score below threshold |
| `--assert-min-sov` | | FLOAT | None | Fail (exit 1) if Share of Voice below threshold |
| `--assert-min-stability` | | FLOAT | None | Fail (exit 1) if stability score below threshold (requires `--stability`) |
| `--protocol` | | PATH | None | Pinned scan protocol JSON for reproducible runs (overrides the config flags; `BRAND` optional) |

### Examples

#### Basic Scan

```bash
promptbeacon scan "Nike"
```

Output:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Visibility Score: Nike
Generated: 2026-06-14 10:30:00
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         73.5 / 100

           Metrics
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Metric             ┃ Value       ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Total Mentions     │ 42          │
│ Share of Voice     │ 38%         │
│ SoV Rank           │ #1          │
│ Presence Rate      │ 85%         │
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
  • Brand is mentioned prominently across all queries.

Recommendations:
  [HIGH] Increase presence in "athletic wear" queries.

Sources Cited:
  • nike.com [Nike]
  • runnersworld.com [Nike]
```

#### Demo Mode

```bash
promptbeacon scan "Nike" --demo
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

#### Smart Mode (LLM Extraction + Recommendations)

```bash
promptbeacon scan "Nike" --smart
```

#### Stability Scan

Run the scan N times and compute stability metrics:

```bash
# 5 stability runs
promptbeacon scan "Nike" --stability 5

# Short form
promptbeacon scan "Nike" -r 5

# Stability in demo mode (free exploration)
promptbeacon scan "Nike" --stability 3 --demo
```

#### CI Assertions (Exit Code 1 on Failure)

```bash
# Fail if score < 40
promptbeacon scan "Nike" --assert-min-score 40

# Fail if Share of Voice < 15%
promptbeacon scan "Nike" --assert-min-sov 0.15

# Combined thresholds
promptbeacon scan "Nike" \
  --competitor "Adidas" \
  --assert-min-score 40 \
  --assert-min-sov 0.15

# Stability + stability assertion
promptbeacon scan "Nike" \
  --stability 5 \
  --assert-min-stability 70
```

#### Reproducible Protocol (pinned, for CI trends)

Pin the brand, prompts, providers, and run count in a JSON file so every run is
identical and trends stay comparable ("don't measure once"):

```json
// nike-protocol.json
{
  "brand": "Nike",
  "competitors": ["Adidas", "Puma"],
  "providers": ["openai", "anthropic"],
  "prompts": ["What are the best running shoes?", "Which running shoe brand is most recommended?"],
  "runs": 5,
  "grounded": true
}
```

```bash
promptbeacon scan --protocol nike-protocol.json
```

#### Custom Categories

```bash
promptbeacon scan "Nike" \
  --category "running shoes" \
  --category "athletic wear" \
  --category "sports brand"
```

#### With Storage

```bash
promptbeacon scan "Nike" \
  --storage ~/.promptbeacon/nike.db
```

#### JSON / Markdown Output

```bash
promptbeacon scan "Nike" --format json > report.json
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
  --smart \
  --assert-min-score 40 \
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
| `--against` | `-a` | TEXT | required | Competitor brand (repeatable, at least one required) |
| `--provider` | `-p` | TEXT | None | LLM provider (repeatable) |
| `--format` | `-f` | TEXT | text | Output format: text, json, markdown |
| `--demo` | | FLAG | false | Use demo mode |

### Examples

```bash
# Basic comparison
promptbeacon compare "Nike" --against "Adidas"

# Multiple competitors
promptbeacon compare "Nike" \
  --against "Adidas" \
  --against "Puma" \
  --against "New Balance"

# JSON export
promptbeacon compare "Nike" \
  --against "Adidas" \
  --format json > comparison.json

# Demo mode
promptbeacon compare "Nike" --against "Adidas" --demo
```

Output includes a competitor comparison table with scores, Share of Voice, and sentiment.

---

## `sources`

Show which **source domains** AI answers cite for your brand and category — and which of them cite *you*. Web-grounded answers cite their sources; this ranks those domains so you can act on them ("get cited on these sites"). Works keyless in demo mode.

### Usage

```bash
promptbeacon sources BRAND [OPTIONS]
```

### Arguments

- `BRAND` (required): The brand name to analyze

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--competitor` | `-c` | TEXT | None | Competitor brand (repeatable) |
| `--provider` | `-p` | TEXT | None | LLM provider (repeatable) |
| `--category` | `-t` | TEXT | None | Category/topic to analyze (repeatable) |
| `--prompts` | `-n` | INT | 10 | Number of prompts per category |
| `--demo` | | FLAG | false | Use demo mode (no API keys required) |
| `--grounded` | | FLAG | false | Web-grounded measurement with real provider citations (uses your keys) |
| `--format` | `-f` | TEXT | text | Output format: text, json |

### Examples

```bash
# Preview source attribution, keyless
promptbeacon sources "Nike" --demo --competitor "Adidas"

# Real, web-grounded citations (needs the [grounded] extra + a provider key)
promptbeacon sources "Nike" --grounded --competitor "Adidas" --provider openai

# Machine-readable for pipelines
promptbeacon sources "Nike" --demo --format json
```

### Output

```
measurement: demo — Demo data — canned responses, not a real measurement.

Top Source Domains (5 citations across 3 sources)
 Domain                    Type     Citations  Share  Cites Nike?
 www.consumerreports.org   review   3          60%    yes
 www.cnbc.com              news     1          20%    yes
 www.reddit.com            reddit   1          20%    yes

Domains that cite Nike: www.consumerreports.org, www.cnbc.com, www.reddit.com
```

> `--grounded` measures web-grounded answers with the **real provider citations**. Covered: OpenAI, Anthropic, Gemini, and Perplexity (Mistral/Cohere fall back to base completion). Install with `pip install 'promptbeacon[grounded]'`.

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

```bash
promptbeacon history "Nike"
promptbeacon history "Nike" --days 90
promptbeacon history "Nike" --format json > history.json
```

---

## `dashboard`

Generate a self-contained HTML dashboard with interactive charts: Share of Voice bar, score breakdown, sentiment donut, stability band (if stability data present), and optional history sparkline.

### Usage

```bash
promptbeacon dashboard BRAND [OPTIONS]
```

### Arguments

- `BRAND` (required): The brand name

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--competitor` | `-c` | TEXT | None | Competitor brand (repeatable) |
| `--provider` | `-p` | TEXT | None | LLM provider (repeatable) |
| `--storage` | `-s` | PATH | None | DuckDB path (enables history sparkline) |
| `--output` | `-o` | PATH | report.html | Output HTML file path |
| `--demo` | | FLAG | false | Use demo mode |
| `--no-open` | | FLAG | false | Do not auto-open in browser |
| `--format` | `-f` | TEXT | html | Output format (currently only html) |

### Examples

```bash
# Demo dashboard (no keys, auto-opens browser)
promptbeacon dashboard "Nike" --demo -o report.html

# Real scan with competitors
promptbeacon dashboard "Nike" \
  --competitor "Adidas" \
  --provider openai \
  --storage ~/.promptbeacon/nike.db \
  -o nike_dashboard.html

# Generate only, do not open browser
promptbeacon dashboard "Nike" --demo -o report.html --no-open
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

Note: No API keys are required to use demo mode. The `demo` command and the `--demo` flag work without any configured providers.

---

## Output Formats

### Text Format (Default)

Rich formatted output with tables, colors, score breakdown, Share of Voice, and visual hierarchy. Best for terminal display.

```bash
promptbeacon scan "Nike"
```

### JSON Format

Machine-readable JSON for parsing and integration.

```bash
promptbeacon scan "Nike" --format json
```

Example output (abbreviated):
```json
{
  "brand": "Nike",
  "visibility_score": 73.5,
  "mention_count": 42,
  "share_of_voice": {
    "target_share": 0.38,
    "target_presence_rate": 0.85,
    "target_rank": 1,
    "aggregate": {
      "Nike": {"share_of_voice": 0.38, "appearances": 34, "total_prompts": 40},
      "Adidas": {"share_of_voice": 0.29, "appearances": 26, "total_prompts": 40}
    }
  },
  "sentiment_breakdown": {
    "positive": 0.67,
    "neutral": 0.28,
    "negative": 0.05
  },
  "timestamp": "2026-06-14T10:30:00Z",
  "scan_duration_seconds": 12.3
}
```

### Markdown Format

Formatted Markdown for documentation and reports.

```bash
promptbeacon scan "Nike" --format markdown
```

---

## Environment Variables

### Provider API Keys

Required for live scans; not needed for demo mode:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
export MISTRAL_API_KEY="..."
export COHERE_API_KEY="..."
export PERPLEXITY_API_KEY="pplx-..."
```

### Demo Mode Override

Force demo mode for all commands (useful in CI without API keys):

```bash
export PROMPTBEACON_DEMO=1
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (configuration, scan failure, assertion failure, etc.) |

CI assertion flags (`--assert-min-score`, `--assert-min-sov`, `--assert-min-stability`) return exit code `1` when thresholds are not met.

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

promptbeacon scan "$BRAND" \
  --storage ~/.promptbeacon/nike.db \
  --competitor "Adidas" \
  --competitor "Puma" \
  --provider openai \
  --provider anthropic \
  --prompts 25 \
  --assert-min-score 40 \
  --format json > "$OUTPUT_DIR/nike_$DATE.json"

echo "Scan completed: $OUTPUT_DIR/nike_$DATE.json"
```

### Weekly Dashboard Generation

```bash
#!/bin/bash
# weekly_dashboard.sh

promptbeacon dashboard "Nike" \
  --competitor "Adidas" \
  --competitor "Puma" \
  --provider openai \
  --storage ~/.promptbeacon/nike.db \
  -o "reports/nike_dashboard_$(date +%Y%m%d).html" \
  --no-open

echo "Dashboard saved"
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

## Integration Examples

### With jq

Process JSON output with jq:

```bash
# Extract visibility score
promptbeacon scan "Nike" --format json | jq '.visibility_score'

# Get Share of Voice
promptbeacon scan "Nike" --format json | jq '.share_of_voice.target_share'

# Get competitor SoV breakdown
promptbeacon scan "Nike" --format json | \
  jq '.share_of_voice.aggregate | to_entries[] | "\(.key): \(.value.share_of_voice)"'

# Filter high-priority recommendations
promptbeacon scan "Nike" --format json | \
  jq '.recommendations[] | select(.priority == "high") | .action'

# List cited sources
promptbeacon scan "Nike" --format json | \
  jq '.citation_summary.citations[] | .source_name'
```

---

## Troubleshooting

### Command Not Found

**Problem:** `promptbeacon: command not found`

**Solution:**
```bash
pip install promptbeacon

# Or with uv
uv add promptbeacon

# Check installation
python -m promptbeacon --help
```

### No API Keys (Live Scan Fails)

**Problem:** `Error: No API keys found for configured providers`

**Solution:** Use demo mode, or set at least one key:

```bash
# Demo mode (no keys needed)
promptbeacon demo "Nike"
promptbeacon scan "Nike" --demo

# Or set a provider key
export OPENAI_API_KEY="sk-..."
promptbeacon providers  # verify configuration
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
- [Advanced Usage](advanced.md) - CI/CD, stability, smart mode
