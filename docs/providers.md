# Providers

PromptBeacon queries six hosted providers through [LiteLLM](https://docs.litellm.ai/),
plus a `litellm` slot for any other model LiteLLM supports (a local Ollama model,
OpenRouter, Azure, a vLLM server). This page covers keys and setup; model choice is on
[Models & local LLMs](models.md).

> **No API keys needed to try PromptBeacon.** `promptbeacon demo httpx -t "python http client"`
> (or `.demo().scan()` in Python) runs every feature on canned data.

## Supported providers

| Provider (`-p`) | Default model | API key variable | Get a key |
|-----------------|---------------|------------------|-----------|
| `openai` | `gpt-6-luna` | `OPENAI_API_KEY` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `anthropic` | `claude-haiku-5-5` | `ANTHROPIC_API_KEY` | [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) |
| `google` | `gemini-3.5-flash-lite` | `GOOGLE_API_KEY` or `GEMINI_API_KEY` | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) |
| `mistral` | `mistral-small-latest` | `MISTRAL_API_KEY` | [console.mistral.ai/api-keys](https://console.mistral.ai/api-keys) |
| `cohere` | `command-r7b-12-2024` | `COHERE_API_KEY` | [dashboard.cohere.com/api-keys](https://dashboard.cohere.com/api-keys) |
| `perplexity` | `sonar` | `PERPLEXITY_API_KEY` | [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api) |
| `litellm` | none, set with `--model litellm=...` | read by LiteLLM | see [Models & local LLMs](models.md#local-models-with-ollama) |

Override any default with `--model provider=model_id`, `Beacon.with_models()` or
`PROMPTBEACON_<PROVIDER>_MODEL`. Check what is configured, and which model each provider
will use:

```bash
promptbeacon providers
```

## Setting keys

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GEMINI_API_KEY="..."        # or GOOGLE_API_KEY; GOOGLE_API_KEY wins if both are set
export MISTRAL_API_KEY="..."
export COHERE_API_KEY="..."
export PERPLEXITY_API_KEY="pplx-..."
```

Keys can also live in a `.env` file in the working directory or a parent; it is loaded on
import, and values already set in the environment win. An empty or whitespace-only value
(for example `OPENAI_API_KEY=` in CI, or an unset `${VAR:-}` mapping in an MCP
configuration) counts as **not configured**.

```python
from promptbeacon import Provider
from promptbeacon.core.config import has_api_key, resolve_model

for provider in Provider:
    print(provider.value, has_api_key(provider), resolve_model(provider))
```

## Choosing providers

By default a scan queries OpenAI. Choose providers with `-p` (repeatable) or
`with_providers()`; they are queried in parallel, each with its own concurrency limit
(`concurrent_requests`, default 5). Providers without a key are skipped; if none of the
chosen providers has a key, the scan stops with a clear error.

```python
from promptbeacon import Beacon, Provider

report = (
    Beacon("httpx")
    .with_category("python http client")
    .with_providers(Provider.OPENAI, Provider.ANTHROPIC, Provider.GOOGLE)
    .scan()
)
print(report.providers_used)
```

If you name models with `--model` / `with_models()` and do not pass providers, the
providers you named models for are the ones queried.

## Web-grounded scans

`--grounded` (or `.with_grounding()`) uses each provider's own web search through its
official SDK and records the pages it cites (`pip install 'promptbeacon[grounded]'`):

| Provider | Web search used |
|----------|-----------------|
| OpenAI | Responses API `web_search` tool |
| Anthropic | `web_search_20250305` server tool |
| Google | Google Search grounding |
| Perplexity | Sonar (always web-grounded) |
| Mistral, Cohere, `litellm` | none: falls back to a plain completion, labelled `base_model` |

Grounded calls use the same model you chose for the provider. Perplexity now serves Sonar
requests through its Agent API; PromptBeacon calls the OpenAI-compatible endpoint, which
Perplexity documents as continuing to work during its migration.

## Funnel search backend (Tavily)

`promptbeacon funnel` runs its own live web retrieval, separate from the LLM providers,
using [Tavily](https://tavily.com):

```bash
export TAVILY_API_KEY="tvly-..."
promptbeacon funnel httpx --category "python http client"          # live
promptbeacon funnel httpx --category "python http client" --demo   # keyless mock backend
```

Add `--smart` for an LLM planner and LLM-judge reranker (uses one of your provider keys).
`promptbeacon providers` also shows whether Tavily is configured.

## In CI and containers

The GitHub Action takes keys as environment variables and models as an input:

```yaml
- uses: yotambraun/promptbeacon@v1
  with:
    brand: "httpx"
    category: "python http client"
    providers: "openai anthropic"
    min-score: "40"
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

Any other CI runs the CLI directly:

```bash
pip install promptbeacon
promptbeacon scan httpx --category "python http client" \
  --format json --no-save --assert-min-score 40 > report.json
```

In a container, pass keys at run time rather than baking them into the image:

```dockerfile
FROM python:3.12-slim
RUN pip install promptbeacon
CMD ["promptbeacon", "scan", "httpx", "--category", "python http client", "--no-save"]
```

```bash
docker run --rm -e OPENAI_API_KEY my-promptbeacon-image
```

See [CI & examples](examples.md) for the full Action reference.

## Costs

Each report carries `total_cost_usd`, an estimate from the token usage the provider
returns and LiteLLM's price map, and `cost_status`, which says how complete that estimate
is:

| `cost_status` | Meaning |
| --- | --- |
| `complete` | Every API call was priced |
| `partial` | Some calls, or some web-search fees, could not be priced: the real bill is higher |
| `unknown` | No price data for these calls (shown as "unknown", never as $0) |
| `none` | No paid calls (demo mode, or every answer came from the cache) |

Web-grounded scans include per-search fees where the price is known (Anthropic's listed
rate, or the search fee in the price map); otherwise the status is `partial`.
`ProviderResult.search_count` and `search_fees_included` show the detail per answer.
Prices change, so PromptBeacon does not publish its own price tables: check the
provider's pricing page, or the estimate on a one-prompt scan.

```python
from promptbeacon import Beacon

report = Beacon("httpx").with_category("python http client").with_prompt_count(1).scan()
print(report.total_cost_usd, report.cost_status)
```

### Estimating and capping cost

`--estimate` prices a scan before you run it: per model, from LiteLLM's bundled price
map, assuming about 500 output tokens per answer, with an upper bound at `max_tokens`.
Nothing is sent.

```bash
promptbeacon scan httpx -t "python http client" -p openai -p anthropic --estimate
```

`--max-cost USD` (Python: `.with_max_cost(0.05)`, Action: `max-cost`, MCP: `max_cost`)
caps a scan:

1. **Before the scan**, the estimate is compared with the cap. Above it, the scan does
   not start, and the error shows the estimate and how to lower it (fewer prompts,
   providers or stability runs, or a cheaper model).
2. **During the scan**, no new request starts once the money spent plus the requests in
   flight reaches the cap. Requests already running finish, so the overshoot is at most
   one batch of concurrent requests.
3. **The result** is built from the answers collected. `report.partial` is `True`,
   `report.budget` records the cap, the estimate, the spend and how many answers were
   skipped, and every output (text, JSON, Markdown, the CI summary, the badge and the
   card) says it is partial.

Models with no price in LiteLLM's map, such as a local Ollama model, count as $0 and
are listed by name. Perplexity Sonar's per-request fee and grounded search fees are
included where the price map knows them. Demo mode is always $0.

```python
from promptbeacon import Beacon

beacon = Beacon("httpx").with_category("python http client").with_max_cost(0.05)
print(
    beacon.estimate_cost().summary()
)  # about $0.0025 (at most $0.0051) for 10 answers
report = beacon.scan()
if report.partial:
    print(report.budget.completed_answers, "of", report.budget.planned_answers)
```

Ways to keep costs down:

1. Explore in demo mode first; it never calls a provider.
2. Keep the default low-cost models, or pick one with `--model`.
3. Enable `.with_cache()` to skip identical queries.
4. Lower the prompt count (`--prompts 5`) and the number of providers.
5. Use `--stability N` deliberately: it multiplies the number of calls by N.
6. For development, use a local model: `--model litellm=ollama/llama3.2`.

## Errors and rate limits

LiteLLM retries failed requests (`max_retries`, default 3). A provider error is recorded
on that answer as `ExceptionType: message` and the rest of the scan continues; if every
query fails, the scan raises `ScanError` naming the first error, for example an
authentication error from a wrong key or a `NotFoundError` from a mistyped model ID.

If you hit rate limits, lower `concurrent_requests` or the prompt count, enable the cache,
or spread the scan across providers.

Test each provider with a one-prompt scan:

```bash
for p in openai anthropic google mistral cohere perplexity; do
  promptbeacon scan httpx -t "python http client" -p "$p" --prompts 1 --no-save
done
```

## Key hygiene

- Keep keys in environment variables, a secrets manager or CI secrets; never commit them.
- Keep `.env` in `.gitignore`.
- Use separate keys for development and CI, and rotate them.
- PromptBeacon never prints key values; `promptbeacon providers` and the MCP `providers`
  tool report only whether a key is set.

## See also

- [Models & local LLMs](models.md): default models, `--model`, Ollama
- [CI & examples](examples.md): the GitHub Action and pytest plugin
- [Storage & history](storage.md): tracking results over time
- [API reference](api-reference.md)
