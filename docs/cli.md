# CLI Reference

Every command and option. Run `promptbeacon COMMAND --help` for the same information in
your terminal.

```bash
promptbeacon --help
```

## Conventions

- **Category.** Scanning commands accept `--category` / `-t`: the topic the prompts ask
  about, phrased the way a buyer would ("running shoes", "crm software", "python http
  client"). It is what makes a result meaningful. Without it, PromptBeacon asks
  "alternatives to *competitor*" questions when you gave competitors, otherwise it
  falls back to generic prompts and prints how to fix it.
- **Demo.** `--demo` runs the full pipeline on canned answers generated from your
  inputs: no keys, no cost, and output labelled `measurement: demo`.
- **Output streams.** Reports and machine formats (`--format json|csv|markdown|html`) go
  to **stdout**, unwrapped. Progress spinners, notices and errors go to **stderr**, so
  `promptbeacon scan ... -f json > report.json` always produces valid JSON.
- **Lists.** Repeat an option for several values: `-c "Adidas" -c "New Balance"`.

## Commands

| Command | What it does |
| --- | --- |
| [`demo`](#demo) | Keyless demo scan |
| [`scan`](#scan) | Full scan of a brand or project (the main command) |
| [`quick`](#quick) | Fast 3-prompt scan |
| [`compare`](#compare) | Scan with competitors and show the comparison table |
| [`sources`](#sources) | Which domains AI answers cite, and which cite you |
| [`funnel`](#funnel) | Where a brand drops out of a model of agentic search |
| [`dashboard`](#dashboard) | Single-file HTML report |
| [`history`](#history) | Saved scans and trend |
| [`badge`](#badge) | README badge (SVG and shields.io endpoint JSON) |
| [`card`](#card) | 1200x630 share card (SVG, optional PNG) |
| [`ci`](#ci) | Outputs, job summary, PR-comment body and gates from a saved report |
| [`mcp`](#mcp) | MCP server over stdio |
| [`providers`](#providers) | Which provider keys are configured |

---

## `demo`

Keyless demo scan with realistic canned answers.

```bash
promptbeacon demo [BRAND] [OPTIONS]
```

| Option | Short | Description |
| --- | --- | --- |
| `BRAND` | | Brand to analyze (default `Nike`) |
| `--category` | `-t` | Category the prompts ask about (repeatable) |
| `--competitor` | `-c` | Competitors (repeatable). Without it, the demo uses two placeholders, "Competitor A" and "Competitor B" |
| `--format` | `-f` | `text` (default), `json`, `markdown`, `csv`, `html` |

```bash
promptbeacon demo "Nike" -t "running shoes" -c "Adidas" -c "New Balance"
promptbeacon demo "Acme" -t "crm software" -f json > demo.json
```

---

## `scan`

Measure a brand or an open-source project across one or more providers.

```bash
promptbeacon scan [BRAND] [OPTIONS]
```

**What to scan**

| Option | Description |
| --- | --- |
| `BRAND` | Brand to analyze. Optional with `--protocol` or a project option |
| `--repo OWNER/NAME` | A GitHub repository (also accepts a github.com URL) |
| `--pypi PACKAGE` | A PyPI package |
| `--npm PACKAGE` | An npm package (scoped names such as `@scope/pkg` work) |
| `--project KIND:REF` | Any registered source, e.g. `pypi:httpx`, `github:owner/name` |

Project options read public metadata to choose the brand, a category and competitor
candidates, print what they guessed and why, and can be overridden with `--category`
and `--competitor`. See [Open-source projects](projects.md).

**Prompts**

| Option | Short | Description |
| --- | --- | --- |
| `--category` | `-t` | Category the prompts ask about (repeatable) |
| `--infer-category` | | No category? Ask one model to name it (and suggest competitors if none were given). One extra LLM call, logged; ignored in demo mode |
| `--competitor` | `-c` | Competitors to compare (repeatable) |
| `--prompts` | `-n` | Prompts per category (default 10). Larger counts are extended deterministically with more templates and phrasing variants; a count that cannot be met is an error, never a silent cap |
| `--protocol PATH` | | Pinned JSON protocol for reproducible runs (see below) |

**Providers and mode**

| Option | Short | Description |
| --- | --- | --- |
| `--provider` | `-p` | `openai` (default), `anthropic`, `google`, `mistral`, `cohere`, `perplexity` (repeatable). Providers are queried in parallel |
| `--demo` | | Keyless demo mode |
| `--grounded` | | Use each provider's web search and capture real citations (OpenAI, Anthropic, Gemini, Perplexity; needs `promptbeacon[grounded]`) |
| `--smart` | | LLM-based extraction and recommendations (more calls) |
| `--stability N` | `-r` | Repeat the whole scan N times and report stability (multiplies cost) |

**History**

| Option | Short | Description |
| --- | --- | --- |
| `--save` / `--no-save` | | Real scans are saved to the history file by default so `history` can show trends. Demo scans are only saved with an explicit `--storage`. `--no-save` wins over `--storage`; a default-history write failure only warns |
| `--storage PATH` | `-s` | History file (default `~/.promptbeacon/data.db`, or `$PROMPTBEACON_HOME/data.db`) |

**Gates and output**

| Option | Description |
| --- | --- |
| `--assert-min-score X` | Exit 1 if the visibility score is below X |
| `--assert-min-sov X` | Exit 1 if share of voice (0-1) is below X |
| `--assert-min-stability X` | Exit 1 if the stability score is below X (needs `--stability`) |
| `--format`, `-f` | `text` (default), `json`, `markdown`, `csv`, `html` |

### Examples

```bash
# Real scan, two providers
promptbeacon scan "Nike" -t "running shoes" -c "Adidas" -c "New Balance" -p openai -p anthropic

# Same, keyless
promptbeacon scan "Nike" -t "running shoes" -c "Adidas" --demo

# Web-grounded, with the real cited sources
promptbeacon scan "Nike" -t "running shoes" -c "Adidas" --grounded -p openai

# An open-source project
promptbeacon scan --pypi httpx
promptbeacon scan --repo fastapi/fastapi -t "python web framework"

# Stability and a CI gate
promptbeacon scan "Nike" -t "running shoes" --stability 5 --assert-min-stability 60
promptbeacon scan "Nike" -t "running shoes" -c "Adidas" --assert-min-score 40 --assert-min-sov 0.2

# Machine-readable, without touching history
promptbeacon scan "Nike" -t "running shoes" -f json --no-save > report.json
```

When a scan used generic prompts (no category, no competitors) the CLI says so on
stderr, and `report.prompt_strategy` is `"generic"`.

### Reproducible protocol

Pin everything in a JSON file so each run asks exactly the same questions:

```json
{
  "brand": "Nike",
  "competitors": ["Adidas", "Puma"],
  "providers": ["openai", "anthropic"],
  "prompts": [
    "What are the best running shoes?",
    "Which running shoe brand is most recommended?"
  ],
  "runs": 5,
  "grounded": true
}
```

```bash
promptbeacon scan --protocol nike-protocol.json
```

Pinned prompts are always used in full. `categories` and `prompt_count` are also
accepted instead of `prompts`.

---

## `quick`

A 3-prompt scan for a fast check.

```bash
promptbeacon quick "Nike" --category "running shoes" [--demo] [-f json]
```

| Option | Short | Description |
| --- | --- | --- |
| `--category` | `-t` | Category |
| `--demo` | | Keyless demo mode |
| `--format` | `-f` | Output format |

---

## `compare`

A scan with competitors that ends with the comparison table.

```bash
promptbeacon compare "Nike" -t "running shoes" --against "Adidas" -a "Puma"
```

| Option | Short | Description |
| --- | --- | --- |
| `--against` | `-a` | Competitors (repeatable, required) |
| `--category` | `-t` | Category |
| `--provider` | `-p` | Providers |
| `--demo` | | Keyless demo mode |
| `--format` | `-f` | Output format |

---

## `sources`

Rank the domains AI answers cite for your category and show which ones cite you.
Real citations need `--grounded`; `--demo` previews the output.

```bash
promptbeacon sources "Nike" -t "running shoes" -c "Adidas" --grounded -p openai
promptbeacon sources "Nike" -t "running shoes" --demo -f json
```

| Option | Short | Description |
| --- | --- | --- |
| `--category` | `-t` | Category |
| `--competitor` | `-c` | Competitors |
| `--provider` | `-p` | Providers |
| `--prompts` | `-n` | Prompts per category |
| `--grounded` | | Web-grounded measurement with real citations |
| `--demo` | | Keyless demo mode |
| `--format` | `-f` | `text` or `json` |

Example (demo):

```text
measurement: demo — Demo data — canned responses, not a real measurement.
prompts: 10 · category: running shoes

Top Source Domains (8 citations across 5 sources)
 Domain             Type        Citations   Share   Cites Nike?
 en.wikipedia.org   wikipedia   2           25%     yes
 medium.com         social      2           25%     yes
 www.quora.com      social      2           25%     yes
 www.reddit.com     reddit      1           12%     yes
 www.youtube.com    video       1           12%     yes
```

---

## `funnel`

A local, observable model of agentic search: the prompt is fanned out into
sub-queries, results are retrieved, reranked and cited, and the report shows where the
brand drops out. It is a model (`measurement: funnel_model`), not the consumer product.

```bash
promptbeacon funnel "Nike" -t "running shoes" -c "Adidas" --demo
promptbeacon funnel "Nike" --prompt "What are the best running shoes?"   # needs TAVILY_API_KEY
```

| Option | Short | Description |
| --- | --- | --- |
| `--prompt` | `-q` | Buyer-intent prompt to fan out |
| `--category` | `-t` | Builds the prompt when `--prompt` is omitted |
| `--competitor` | `-c` | Competitors |
| `--sub-queries` | | Fan-out width (default 8) |
| `--smart` | | LLM planner and LLM-judge reranker (needs an LLM key) |
| `--demo` | | Mock search backend |
| `--format` | `-f` | `text` or `json` |

Live search uses Tavily: set `TAVILY_API_KEY` (free key at
[tavily.com](https://tavily.com)).

---

## `dashboard`

Write a single, self-contained HTML report.

```bash
promptbeacon dashboard "Nike" -t "running shoes" -c "Adidas" --demo -o report.html
promptbeacon dashboard "Nike" -t "running shoes" -c "Adidas" --no-open
```

| Option | Short | Description |
| --- | --- | --- |
| `--category` | `-t` | Category |
| `--competitor` | `-c` | Competitors |
| `--provider` | `-p` | Providers |
| `--output` | `-o` | Output file (default `promptbeacon-report.html`) |
| `--open` / `--no-open` | | Open in a browser (default: open) |
| `--demo` | | Keyless demo mode |

---

## `history`

Show saved scans for a brand and the trend.

```bash
promptbeacon history "Nike" --days 30
promptbeacon history "Nike" -f json
```

| Option | Short | Description |
| --- | --- | --- |
| `--days` | `-d` | Days of history (default 30) |
| `--storage` | `-s` | History file (default `~/.promptbeacon/data.db` or `$PROMPTBEACON_HOME/data.db`) |
| `--format` | `-f` | `text` or `json` |

Real `scan` runs are saved automatically. If there is no history yet, the command says
how to create it instead of creating an empty database.

---

## `badge`

Write a README badge from a scan, or from a saved report.

```bash
promptbeacon badge "Nike" -t "running shoes" -c "Adidas" --demo
promptbeacon badge --report report.json -o .promptbeacon/badge.svg \
  --endpoint .promptbeacon/badge.json
promptbeacon badge --pypi httpx --metric sov
```

| Option | Description |
| --- | --- |
| `BRAND` or `--repo/--pypi/--npm/--project` | What to scan (omit with `--report`) |
| `--report PATH` | Render from a saved `scan -f json` report instead of scanning |
| `--category`, `--competitor`, `--provider`, `--prompts`, `--demo`, `--grounded` | As for `scan` |
| `--output`, `-o` | SVG file (default `promptbeacon-badge.svg`) |
| `--endpoint PATH` | Also write a shields.io endpoint JSON |
| `--label TEXT` | Left-hand text (default `AI visibility`) |
| `--metric` | `both` (default, e.g. `62/100 · SoV 34%`), `score`, or `sov` |

The command prints a ready-to-paste Markdown snippet. Badges made from demo data say
`demo` and are grey. See [Badges & share cards](share.md).

---

## `card`

Write a 1200x630 share card showing how often each brand appears in the answers.

```bash
promptbeacon card "Nike" -t "running shoes" -c "Adidas" -c "Hoka" --demo
promptbeacon card --report report.json --theme both --png card.png
```

| Option | Description |
| --- | --- |
| `BRAND` or `--repo/--pypi/--npm/--project` | What to scan (omit with `--report`) |
| `--report PATH` | Render from a saved report |
| `--category`, `--competitor`, `--provider`, `--prompts`, `--demo`, `--grounded` | As for `scan` |
| `--output`, `-o` | SVG file (default `promptbeacon-card.svg`) |
| `--png PATH` | Also write a PNG (needs `pip install 'promptbeacon[share]'`) |
| `--theme` | `light` (default), `dark`, or `both` (adds a `-dark` file next to each output) |

---

## `ci`

Turn a saved report into CI artifacts and apply thresholds. Everything is written
before the command exits, so a failing check still reports its numbers.

```bash
promptbeacon scan "Nike" -t "running shoes" -c "Adidas" -f json --no-save > report.json
promptbeacon ci --report report.json --min-score 50 --min-sov 0.2 --comment-file comment.md
```

| Option | Description |
| --- | --- |
| `--report PATH` | Report from `scan -f json` (required) |
| `--min-score`, `--min-sov`, `--min-presence`, `--min-stability`, `--max-rank` | Thresholds; exit 1 if any is missed |
| `--comment-file PATH` | Write a Markdown PR-comment body that starts with a hidden marker, for a sticky comment |

On GitHub Actions it appends step outputs to `$GITHUB_OUTPUT` (`score`,
`share-of-voice`, `rank`, `presence`, `stability`, `tier`, `category`, `cost-usd`,
`passed`) and a Markdown summary to `$GITHUB_STEP_SUMMARY`. Elsewhere it prints the
summary to stdout. See [CI & examples](examples.md).

---

## `mcp`

Run the MCP server over stdio, for Claude Code, Cursor and other MCP clients. Needs
`pip install 'promptbeacon[mcp]'`.

```bash
promptbeacon mcp
```

See [Claude Code & MCP](mcp.md).

---

## `providers`

List providers and the Tavily search backend, and whether each key is configured. Key
values are never printed.

```bash
promptbeacon providers
```

---

## Environment variables

| Variable | Used for |
| --- | --- |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `MISTRAL_API_KEY`, `COHERE_API_KEY`, `PERPLEXITY_API_KEY` | Provider keys for real scans. Empty values count as not set |
| `TAVILY_API_KEY` | Live web search for `funnel` |
| `GITHUB_TOKEN` or `GH_TOKEN` | Higher GitHub API limit for `--repo` (60 requests/hour without a token) |
| `PROMPTBEACON_HOME` | Data directory (history and caches); default `~/.promptbeacon` |
| `PROMPTBEACON_DEMO` | `1` makes `@pytest.mark.visibility` tests run in demo mode (pytest plugin only) |

Keys can also live in a `.env` file in the working directory; values already set in
the environment win.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Error (configuration, scan failure, missing project, or a missed threshold) |
| 2 | Invalid command-line usage |

## Scripting

```bash
# Score and share of voice with jq
promptbeacon scan "Nike" -t "running shoes" -c "Adidas" -f json --no-save > report.json
jq '.visibility_score' report.json
jq '.share_of_voice.aggregate | map_values(.share_of_voice)' report.json

# Several brands, one history file
for brand in Nike Adidas Puma; do
  promptbeacon scan "$brand" -t "running shoes" --storage ~/.promptbeacon/shoes.db
done
promptbeacon history "Nike" --storage ~/.promptbeacon/shoes.db
```

## See also

- [Quickstart](quickstart.md)
- [Open-source projects](projects.md)
- [Badges & share cards](share.md)
- [CI & examples](examples.md)
- [API reference](api-reference.md)
