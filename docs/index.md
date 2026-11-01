# PromptBeacon

**Does AI recommend your library or dev product?** PromptBeacon is an open-source Python
library, CLI, pytest plugin, GitHub Action and MCP server. It asks ChatGPT, Claude, Gemini
or a local model the questions your users ask, measures how often you are mentioned and
recommended next to your competitors, and turns that into a number you can gate in CI and
show as a README badge.

!!! info "Which tool?"
    **PromptBeacon** is for developers and open-source maintainers: does AI recommend
    your library or dev product — a number in CI and a README badge.

    **[Saylent](https://github.com/yotambraun/saylent)** (npm `saylent`) is for brand and
    website teams: an audit of what AI assistants say about your site, with the answers
    and cited pages as receipts, plus fixes for your site.

## Try it in ten seconds

```bash
pip install promptbeacon
promptbeacon demo httpx --category "python http client" -c requests -c aiohttp
```

The demo runs the full pipeline on canned answers built from your inputs, so you see what
a real scan reports without spending anything. Output is labelled `measurement: demo`.
For a real measurement, set an API key and run `promptbeacon scan` with the same
arguments.

```python
from promptbeacon import Beacon

report = (
    Beacon("httpx")
    .demo()
    .with_category("python http client")
    .with_competitors("requests", "aiohttp")
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
| Check a library or product | `promptbeacon scan "Acme" --category "crm software"` |
| Check an open-source project | `promptbeacon scan --repo owner/name` ([Open-source projects](projects.md)) |
| Show the result | `promptbeacon badge` and `promptbeacon card` ([Badges & share cards](share.md)) |
| Gate CI or track weekly | GitHub Action, pytest plugin, `promptbeacon ci` ([CI & examples](examples.md)) |
| Choose models, run locally | `--model anthropic=claude-sonnet-5-5`, `--model litellm=ollama/llama3.2` ([Models & local LLMs](models.md)) |
| Ask from your editor or agent | `promptbeacon mcp` and the Claude Code plugin ([Claude Code & MCP](mcp.md)) |
| Build on it | The Python API ([API reference](api-reference.md)) |

## Providers and models

OpenAI, Anthropic, Google, Mistral, Cohere and Perplexity, queried in parallel with
your own keys (environment variables or a `.env` file), plus a `litellm` slot for any
model LiteLLM supports, such as a local Ollama model. Each provider has a low-cost
default model; choose another with `--model provider=model_id`. Web-grounded scans use
each provider's native web search for OpenAI, Anthropic, Gemini and Perplexity. See
[Models & local LLMs](models.md) and [Providers](providers.md).

## Local-first

Results stay on your machine. Real CLI scans are saved to a local DuckDB file
(`~/.promptbeacon/data.db`) so `promptbeacon history` can show trends; see
[Storage & history](storage.md). There is no hosted service and no account.

## Next steps

- [Quickstart](quickstart.md) — demo, first real scan, first project scan
- [Models & local LLMs](models.md) — default models, `--model`, Ollama
- [CLI reference](cli.md) — every command and option
- [Badges & share cards](share.md) — put the result in a README or a post
- [CI & examples](examples.md) — GitHub Action, job summary, PR comments, pytest
- [Advanced](advanced.md) — stability, smart mode, protocols, async

PromptBeacon is released under the Apache License 2.0.
