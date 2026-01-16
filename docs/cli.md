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

- [`scan`](#scan) - Run a brand visibility scan
- [`compare`](#compare) - Compare brand against competitors
- [`history`](#history) - View historical visibility data
- [`providers`](#providers) - List available providers and status

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
| `--provider` | `-p` | TEXT | None | LLM provider: openai, anthropic, google (can be used multiple times) |
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
Generated: 2026-01-16 10:30:00
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
  --provider google
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

Output:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Historical Visibility Data
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           Nike

Average Score: 72.3
Trend: ↑ up
Volatility: 3.45

    Historical Data Points
┏━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Date       ┃ Score ┃ Mentions ┃ Sentiment  ┃
┡━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━┩
│ 2026-01-10 │ 68.5  │ 38      │ +65% / -5% │
│ 2026-01-11 │ 70.2  │ 40      │ +66% / -4% │
│ 2026-01-12 │ 71.8  │ 41      │ +67% / -5% │
│ 2026-01-13 │ 73.1  │ 42      │ +68% / -4% │
│ 2026-01-14 │ 74.5  │ 44      │ +69% / -3% │
│ 2026-01-15 │ 73.9  │ 43      │ +68% / -4% │
│ 2026-01-16 │ 73.5  │ 42      │ +67% / -5% │
└────────────┴───────┴─────────┴────────────┘
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
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Provider ┃ Status         ┃ Environment Variable ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ openai   │ ✓ Configured   │ OPENAI_API_KEY       │
│ anthropic│ ✗ Not configured│ ANTHROPIC_API_KEY    │
│ google   │ ✓ Configured   │ GOOGLE_API_KEY       │
└──────────┴────────────────┴──────────────────────┘
```

---

## Output Formats

### Text Format (Default)

Rich formatted output with tables, colors, and visual hierarchy. Best for terminal display.

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
  "competitor_comparison": {},
  "timestamp": "2026-01-16T10:30:00Z",
  "scan_duration_seconds": 12.3
}
```

### Markdown Format

Formatted Markdown for documentation and reports.

```bash
promptbeacon scan "Nike" --format markdown
```

Example output:
```markdown
# Visibility Report: Nike

**Generated:** 2026-01-16 10:30:00

## Summary

- **Visibility Score:** 73.5 / 100
- **Total Mentions:** 42
- **Positive Sentiment:** 67.0%
- **Scan Duration:** 12.3s

## Metrics

| Metric | Value |
|--------|-------|
| Total Mentions | 42 |
| Positive Sentiment | 67.0% |
...
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

### Competitive Intelligence

```bash
#!/bin/bash
# competitive_intel.sh

promptbeacon compare "Nike" \
  --against "Adidas" \
  --against "Puma" \
  --against "New Balance" \
  --against "Under Armour" \
  --provider openai \
  --provider anthropic \
  --format markdown > reports/competitive_analysis.md

promptbeacon history "Nike" --days 90 --format json > reports/nike_history.json
```

---

## Environment Variables

### Provider API Keys

Required for provider access:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
```

### Default Storage Path

Override default storage location:

```bash
export PROMPTBEACON_STORAGE="~/.promptbeacon/data.db"
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (configuration, scan failure, etc.) |

### Handling Errors

```bash
#!/bin/bash

if promptbeacon scan "Nike" --format json > report.json; then
    echo "Scan successful"
else
    echo "Scan failed with exit code $?"
    exit 1
fi
```

---

## Shell Completion

### Bash

```bash
eval "$(_PROMPTBEACON_COMPLETE=bash_source promptbeacon)"
```

Add to `~/.bashrc` for persistence.

### Zsh

```bash
eval "$(_PROMPTBEACON_COMPLETE=zsh_source promptbeacon)"
```

Add to `~/.zshrc` for persistence.

### Fish

```bash
_PROMPTBEACON_COMPLETE=fish_source promptbeacon | source
```

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
```

### With CSV Tools

```bash
# Convert to CSV and analyze with csvkit
promptbeacon scan "Nike" --format json | \
  python -c "import sys, json, csv; data = json.load(sys.stdin); ..." > report.csv

csvstat report.csv
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

## Scheduled Execution

### Using cron

```cron
# Daily scan at 2 AM
0 2 * * * /usr/local/bin/promptbeacon scan "Nike" --storage ~/.promptbeacon/nike.db

# Weekly competitive analysis (Mondays at 3 AM)
0 3 * * 1 /usr/local/bin/promptbeacon compare "Nike" --against "Adidas" --format json > /data/reports/weekly_$(date +\%Y\%m\%d).json
```

### Using systemd timer

Create `~/.config/systemd/user/promptbeacon.service`:

```ini
[Unit]
Description=PromptBeacon Daily Scan

[Service]
Type=oneshot
ExecStart=/usr/local/bin/promptbeacon scan "Nike" --storage %h/.promptbeacon/nike.db
```

Create `~/.config/systemd/user/promptbeacon.timer`:

```ini
[Unit]
Description=Run PromptBeacon Daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:
```bash
systemctl --user enable promptbeacon.timer
systemctl --user start promptbeacon.timer
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
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Permission Denied on Storage

**Problem:** `StorageError: Permission denied: /path/to/data.db`

**Solution:**
```bash
# Ensure directory exists and is writable
mkdir -p ~/.promptbeacon
chmod 755 ~/.promptbeacon

# Use explicit path
promptbeacon scan "Nike" --storage ~/.promptbeacon/data.db
```

### Timeout Errors

**Problem:** Scan times out with many prompts

**Solution:**
```bash
# Reduce prompt count
promptbeacon scan "Nike" --prompts 5

# Or increase timeout in Python API
# (CLI doesn't expose timeout option currently)
```

---

## Advanced Usage

### Piping and Redirection

```bash
# Chain commands
promptbeacon scan "Nike" --format json | jq '.visibility_score' | mail -s "Nike Score" team@company.com

# Append to log file
promptbeacon scan "Nike" >> ~/logs/promptbeacon.log 2>&1

# Split output
promptbeacon scan "Nike" --format json | tee report.json | jq '.visibility_score'
```

### Conditional Execution

```bash
# Only run comparison if scan succeeds
promptbeacon scan "Nike" && promptbeacon compare "Nike" --against "Adidas"

# Run with fallback
promptbeacon scan "Nike" --provider openai || promptbeacon scan "Nike" --provider anthropic
```

### Loop Processing

```bash
# Process multiple brands
for brand in Nike Adidas Puma; do
    promptbeacon scan "$brand" --format json > "${brand,,}_report.json"
done

# Process with timestamps
while true; do
    promptbeacon scan "Nike" --storage ~/.promptbeacon/nike.db
    sleep 86400  # 24 hours
done
```

---

## See Also

- [API Reference](api-reference.md) - Python API documentation
- [Examples](examples.md) - Real-world usage patterns
- [Storage Guide](storage.md) - Historical tracking details
- [Provider Configuration](providers.md) - API key setup
