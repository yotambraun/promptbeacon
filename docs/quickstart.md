# Quickstart

From install to a real measurement in a few minutes. The first step needs no API keys.

## Installation

```bash
pip install promptbeacon
```

or with [uv](https://github.com/astral-sh/uv):

```bash
uv add promptbeacon
```

Python 3.10 or newer. Optional extras: `promptbeacon[grounded]` (web-grounded scans),
`promptbeacon[share]` (PNG share cards), `promptbeacon[mcp]` (MCP server),
`promptbeacon[pandas]`, `promptbeacon[langchain]`.

---

## Step 1: the keyless demo

A scan asks AI assistants buyer-style questions about a **category** ("What are the
best running shoes?") and measures how often each brand comes up. Give it your
category and your competitors:

```bash
promptbeacon demo "Nike" -t "running shoes" -c "Adidas" -c "New Balance"
```

The demo answers are canned but generated from your inputs, so the report has the
same shape as a real one. It is labelled `measurement: demo` and costs nothing. If you
leave out `-c`, the demo compares against two clearly named placeholders,
"Competitor A" and "Competitor B".

The same in Python:

```python
from promptbeacon import Beacon

report = (
    Beacon("Nike")
    .demo()
    .with_category("running shoes")
    .with_competitors("Adidas", "New Balance")
    .scan()
)

print(f"Visibility score: {report.visibility_score}/100")
sov = report.share_of_voice
print(f"Share of voice:   {sov.target_share:.0%} (rank {sov.target_rank})")
for brand, entry in sov.aggregate.items():
    print(f"  {brand}: in {entry.appearances}/{entry.total_prompts} answers")
```

`--demo` works on the other commands too (`scan`, `quick`, `compare`, `dashboard`,
`sources`, `funnel`, `badge`, `card`).

!!! tip "Always set a category"
    Without a category the prompts cannot be about anything specific. PromptBeacon then
    asks "alternatives to *competitor*" questions if you gave competitors, and otherwise
    falls back to generic prompts and warns you. `report.prompt_strategy` records which
    one was used. If you have an API key, `--infer-category` asks one model to name the
    category for you (one extra call).

---

## Step 2: add a provider key

Set at least one key, in the environment or in a `.env` file in your project
(loaded automatically):

```bash
export OPENAI_API_KEY="sk-..."          # https://platform.openai.com/api-keys
export ANTHROPIC_API_KEY="sk-ant-..."   # https://console.anthropic.com/settings/keys
promptbeacon providers                   # shows which providers are configured
```

Google, Mistral, Cohere and Perplexity are also supported; see
[Providers](providers.md). Empty values count as not configured.

---

## Step 3: your first real scan

```bash
promptbeacon scan "Nike" --category "running shoes" -c "Adidas" -c "New Balance" \
  -p openai -p anthropic
```

Providers are queried in parallel. The report shows the score, share of voice, the
score breakdown, insights and an estimated cost. Real scans are saved to your local
history (`~/.promptbeacon/data.db`) so you can follow the trend:

```bash
promptbeacon history "Nike" --days 30
```

Use `--no-save` to skip saving. In Python:

```python
from promptbeacon import Beacon, Provider

report = (
    Beacon("Nike")
    .with_category("running shoes")
    .with_competitors("Adidas", "New Balance")
    .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
    .scan()
)
print(report.visibility_score, report.cost_status, report.total_cost_usd)
```

What a base scan measures is the model's training memory. To measure what users see
in AI search, add `--grounded` (provider web search, real citations; costs more):

```bash
promptbeacon scan "Nike" -t "running shoes" -c "Adidas" --grounded -p openai
```

---

## Step 4: an open-source project

For software, let PromptBeacon read the project's public metadata:

```bash
promptbeacon scan --pypi httpx --demo
promptbeacon scan --repo encode/httpx            # real scan
promptbeacon scan --npm express --category "node.js web framework"
```

It guesses the category (here "python http client") and competitor candidates from the
README, prints what it guessed and why, and lets you override both. See
[Open-source projects](projects.md).

---

## Step 5: share or track it

```bash
promptbeacon scan "Nike" -t "running shoes" -c "Adidas" -f json --no-save > report.json
promptbeacon badge --report report.json        # README badge (SVG)
promptbeacon card --report report.json --png card.png   # 1200x630 share card
promptbeacon ci --report report.json --min-score 50     # CI gate + summary
```

See [Badges & share cards](share.md) and [CI & examples](examples.md).

---

## Reading the results

**Visibility score (0-100)** combines mention frequency, sentiment, position and
explicit recommendations. Roughly: 70+ strong, 40-69 present but not prominent,
below 40 rarely mentioned.

```python
bd = report.metrics.score_breakdown
print(bd.mention_frequency, bd.sentiment, bd.position, bd.recommendation)
```

**Share of voice** is presence-based: in how many answers each tracked brand appears,
and what fraction of all those appearances is yours.

**Measurement tier** (`report.measurement_tier`) is `demo`, `base_model` or
`api_grounded`. **Cost** is an estimate from token usage and, for grounded scans,
search fees where they are known; `report.cost_status` says whether it is
`complete`, `partial` (the real bill is higher), `unknown` or `none`.

---

## Exports

The CLI writes machine formats to stdout and everything else (progress, notices) to
stderr, so they can be piped:

```bash
promptbeacon scan "Nike" -t "running shoes" -f json > nike.json
promptbeacon scan "Nike" -t "running shoes" -f csv > nike.csv
promptbeacon scan "Nike" -t "running shoes" -f markdown > nike.md
promptbeacon scan "Nike" -t "running shoes" -f html > nike.html
promptbeacon dashboard "Nike" -t "running shoes" -c "Adidas" --demo -o report.html
```

In Python:

```python
from promptbeacon import to_csv, to_dashboard_html, to_dataframe, to_json, to_markdown

to_json(report)
to_csv(report)
to_markdown(report)
to_dashboard_html(report)  # single self-contained HTML file
to_dataframe(report)  # needs promptbeacon[pandas]
```

---

## BeaconGuard

A separate, local-only guard for chatbots you ship: it flags outputs that recommend a
competitor or speak badly of your brand. No API calls.

```python
from promptbeacon import BeaconGuard

guard = BeaconGuard("Nike", competitors=["Adidas", "Puma"])
result = guard.analyze(
    "Avoid Nike. I would recommend Adidas instead, Nike quality is poor."
)
print(result.risk_level)  # "high" (competitor + anti-recommendation)
```

See [Advanced: real-time brand safety](advanced.md#real-time-brand-safety).

---

## Troubleshooting

**"No API keys found for configured providers"** — run with `--demo`, or set a key and
check it with `promptbeacon providers`.

**"No category set … prompts are generic"** — pass `--category` (or
`.with_category(...)`).

**Rate limits** — enable caching (`.with_cache()`), lower `--prompts`, or use fewer
providers.

**Timeouts** — `.with_timeout(60.0)` (default 30 seconds).

---

## Quick reference

```python
Beacon(brand)
.demo()  # keyless demo mode
.with_category(name)  # what the prompts ask about
.with_categories(*names)
.with_category_inference()  # opt-in: one LLM call names the category
.with_competitors(*brands)
.with_aliases(*names)
.with_providers(*providers)
.with_prompt_count(n)  # any n; extended deterministically past the templates
.with_industry(name)  # ecommerce, saas, finance, healthcare, travel, food, tech, developer-tools
.with_grounding()  # web-grounded scan
.with_stability(n)  # repeat for a stability score
.with_cache() / .with_storage(path)
Beacon.from_project("pypi:httpx")  # open-source project

report = beacon.scan()
report.assert_visibility(min_score=40, min_share_of_voice=0.2)
```

```bash
promptbeacon demo "Brand" -t "category" -c "Rival"
promptbeacon scan "Brand" -t "category" -c "Rival" [-p openai] [--grounded] [--stability 5]
promptbeacon scan --repo owner/name | --pypi pkg | --npm pkg
promptbeacon badge | card | ci | history | sources | funnel | dashboard | mcp
```

Next: [CLI reference](cli.md) · [API reference](api-reference.md) ·
[Advanced](advanced.md)
