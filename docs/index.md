# PromptBeacon

**Does AI recommend your product?** PromptBeacon is an open-source Python library,
CLI and GitHub Action that measures how often ChatGPT, Claude, Gemini and other
models mention and recommend a brand or an open-source project, compares it with
competitors, and tracks the result over time and in CI.

`pip install promptbeacon` — the first run needs no API keys.

## Try it in ten seconds

```bash
pip install promptbeacon
promptbeacon demo "Nike" -t "running shoes" -c "Adidas" -c "New Balance"
```

The demo runs the full pipeline on realistic canned answers, so you see exactly what a
real scan reports without spending anything. Output is clearly labelled
`measurement: demo`.

```python
from promptbeacon import Beacon

report = (
    Beacon("Nike")
    .demo()
    .with_category("running shoes")
    .with_competitors("Adidas", "New Balance")
    .scan()
)
print(f"Visibility: {report.visibility_score}/100")
print(f"Share of voice: {report.share_of_voice.target_share:.0%}")
```

For an open-source project, point it at the package or repository:

```bash
promptbeacon scan --pypi httpx --demo        # or --repo owner/name, --npm express
```

## What it measures

- **Visibility score (0-100)** — how often, how prominently and how positively the
  answers mention you, with a breakdown of the four factors.
- **Share of voice** — of all the mentions of you and your competitors, how many are
  yours, with your rank.
- **Stability** — repeat each prompt N times to see how much a single number can be
  trusted (confidence intervals, flip-flopping prompts).
- **Sources** — with `--grounded`, the provider's own web search runs and the real
  cited pages are captured; PromptBeacon ranks the domains and shows which ones cite
  you.
- **Funnel** — a local model of agentic search (fan-out, retrieve, rerank, cite)
  that shows where a brand drops out.

Every report states how it was measured — `demo`, `base_model` (the model's training
memory) or `api_grounded` (provider web search) — and what the prompts asked about
(`report.categories`, `report.prompt_strategy`).

## Where it fits

| Use | How |
| --- | --- |
| Check a brand or product | `promptbeacon scan "Acme" --category "crm software"` |
| Check an open-source project | `promptbeacon scan --repo owner/name` ([Open-source projects](projects.md)) |
| Show the result | `promptbeacon badge` and `promptbeacon card` ([Badges & share cards](share.md)) |
| Gate CI or track weekly | GitHub Action, pytest plugin, `promptbeacon ci` ([CI & examples](examples.md)) |
| Ask from your editor or agent | `promptbeacon mcp` and the Claude Code plugin ([Claude Code & MCP](mcp.md)) |
| Build on it | The Python API ([API reference](api-reference.md)) |

## Providers

OpenAI, Anthropic, Google, Mistral, Cohere and Perplexity, queried in parallel with
your own keys (environment variables or a `.env` file). Web-grounded scans use each
provider's native web search for OpenAI, Anthropic, Gemini and Perplexity. See
[Providers](providers.md).

## Local-first

Results stay on your machine. Real CLI scans are saved to a local DuckDB file
(`~/.promptbeacon/data.db`) so `promptbeacon history` can show trends; see
[Storage & history](storage.md). There is no hosted service and no account.

## Next steps

- [Quickstart](quickstart.md) — demo, first real scan, first project scan
- [CLI reference](cli.md) — every command and option
- [Badges & share cards](share.md) — put the result in a README or a post
- [CI & examples](examples.md) — GitHub Action, job summary, PR comments, pytest
- [Advanced](advanced.md) — stability, smart mode, protocols, async

PromptBeacon is released under the Apache License 2.0.
