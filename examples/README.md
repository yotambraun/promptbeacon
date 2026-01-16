# PromptBeacon Examples

This directory contains example scripts demonstrating how to use PromptBeacon for brand visibility monitoring.

## Prerequisites

1. Install PromptBeacon:
   ```bash
   pip install promptbeacon
   # or with uv
   uv add promptbeacon
   ```

2. Set your API key:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```
   Or create a `.env` file in the project root:
   ```
   OPENAI_API_KEY=sk-...
   ```

## Examples

| Example | Description |
|---------|-------------|
| [`basic_scan.py`](basic_scan.py) | Simple brand visibility analysis |
| [`competitor_analysis.py`](competitor_analysis.py) | Compare against competitors |
| [`export_formats.py`](export_formats.py) | Export reports in various formats |

### 1. Basic Scan

Run a simple visibility scan for a brand:

```bash
python examples/basic_scan.py
```

**Sample Output:** [`output/sample_output.txt`](output/sample_output.txt)

```
============================================================
PromptBeacon - Basic Brand Visibility Scan
============================================================

📊 Visibility Score: 73.5/100
📝 Total Mentions: 12
⏱️  Scan Duration: 8.2s
💰 Estimated Cost: $0.0018

📈 Sentiment Breakdown:
   ✅ Positive: 66.7%
   ➖ Neutral:  25.0%
   ❌ Negative: 8.3%

💡 Key Insights:
   🟢 [visibility] Nike has strong visibility in LLM responses
   🟢 [sentiment] Nike is mentioned predominantly in positive contexts

🎯 Recommendations:
   🟡 [MEDIUM] Build recommendation-worthy content

📄 Sample LLM Responses:

   --- Response 1 (openai/gpt-4o-mini) ---
   Prompt: What are the best running shoes brands?...
   Response: When it comes to running shoes, several brands stand out
             for their quality and innovation. Nike is widely considered
             one of the top choices...
```

### 2. Competitor Analysis

Compare your brand against competitors:

```bash
python examples/competitor_analysis.py
```

**Sample Output:** [`output/competitor_analysis_output.txt`](output/competitor_analysis_output.txt)

```
============================================================
PromptBeacon - Competitor Analysis
============================================================

Brand: Nike
Competitors: Adidas, Puma

📊 Competitor Scores:
----------------------------------------
Brand                Score      Mentions
----------------------------------------
Nike                 73.5       12
Adidas               68.2       10
Puma                 45.3       6
----------------------------------------

🥇 Market Leader: Nike (73.5)
✅ Nike is the visibility leader!
```

### 3. Export Formats

Export reports to JSON, CSV, Markdown, HTML:

```bash
python examples/export_formats.py
```

Creates files in `examples/output/`:
- `report.json` - JSON export
- `report.csv` - CSV metrics
- `report.md` - Markdown report

## Customization

Modify the examples to analyze your own brand:

```python
from promptbeacon import Beacon, Provider

beacon = (
    Beacon("YourBrand")
    .with_competitors("Competitor1", "Competitor2")
    .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
    .with_categories("your industry", "your products")
    .with_prompt_count(20)
)

report = beacon.scan()
print(f"Visibility: {report.visibility_score}/100")
```

## Output Directory

The `output/` directory contains sample outputs demonstrating what PromptBeacon produces:

```
output/
├── sample_output.txt              # Basic scan output
├── competitor_analysis_output.txt # Competitor analysis output
├── report.json                    # JSON export example
├── report.csv                     # CSV export example
└── report.md                      # Markdown export example
```
