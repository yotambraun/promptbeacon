# Models & local LLMs

Every provider has a low-cost default model, so a 10-prompt scan stays cheap. You can
choose a different model per provider, or point PromptBeacon at any model LiteLLM can
reach, including a local Ollama model.

## Default models

| Provider (`-p`) | Default model | API key variable |
|-----------------|---------------|------------------|
| `openai` | `gpt-6-luna` | `OPENAI_API_KEY` |
| `anthropic` | `claude-haiku-5-5` | `ANTHROPIC_API_KEY` |
| `google` | `gemini-3.5-flash-lite` | `GOOGLE_API_KEY` or `GEMINI_API_KEY` |
| `mistral` | `mistral-small-latest` | `MISTRAL_API_KEY` |
| `cohere` | `command-r7b-12-2024` | `COHERE_API_KEY` |
| `perplexity` | `sonar` | `PERPLEXITY_API_KEY` |
| `litellm` | none, you set one | read by LiteLLM for the backend you route to |

The defaults live in one place, `promptbeacon.core.config.DEFAULT_MODELS`, and
`promptbeacon providers` prints the model each provider will use right now. Defaults
change between releases as providers retire models, so pin the model when you track a
trend: a different model gives a different score.

## Choosing a model

The model for a provider is resolved in this order:

1. an explicit choice: `--model provider=model_id`, `Beacon.with_models()`, the Action's
   `models` input, a protocol's `models`, or the MCP tools' `models` argument;
2. the environment variable `PROMPTBEACON_<PROVIDER>_MODEL`, for example
   `PROMPTBEACON_OPENAI_MODEL=gpt-6-sol`;
3. the default above.

=== "CLI"

    ```bash
    promptbeacon scan httpx -t "python http client" \
      --model anthropic=claude-sonnet-5-5 --model openai=gpt-6-sol
    ```

    `--model` (short `-m`) is repeatable and works on `scan`, `compare`, `sources`,
    `dashboard`, `badge` and `card`.

=== "Python"

    ```python
    from promptbeacon import Beacon

    report = (
        Beacon("httpx")
        .with_category("python http client")
        .with_models({"anthropic": "claude-sonnet-5-5"}, openai="gpt-6-sol")
        .demo()  # remove for a real scan
        .scan()
    )
    print(sorted({(r.provider, r.model) for r in report.provider_results}))
    ```

=== "Environment"

    ```bash
    export PROMPTBEACON_ANTHROPIC_MODEL=claude-sonnet-5-5
    promptbeacon scan httpx -t "python http client" -p anthropic
    ```

=== "GitHub Action"

    ```yaml
    - uses: yotambraun/promptbeacon@v1
      with:
        brand: "httpx"
        category: "python http client"
        models: |
          anthropic=claude-sonnet-5-5
          openai=gpt-6-luna
      env:
        ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    ```

**Which providers are queried.** If you pass providers explicitly (`-p`,
`with_providers()`, the Action's `providers` input), exactly those are queried, and a
model set for any other provider is ignored with a warning. If you don't, the providers
you named a model for are queried. With neither, PromptBeacon queries OpenAI.

## Local models with Ollama

The `litellm` provider passes the model string straight to
[LiteLLM](https://docs.litellm.ai/docs/providers), so anything LiteLLM supports works,
with no OpenAI-style API key:

```bash
ollama pull llama3.2          # once; Ollama must be running (ollama serve)
promptbeacon scan httpx -t "python http client" -c requests -c aiohttp \
  --model litellm=ollama/llama3.2
```

```python
from promptbeacon import Beacon

report = (
    Beacon("httpx")
    .with_category("python http client")
    .with_models(litellm="ollama/llama3.2")
    .scan()
)
```

LiteLLM talks to Ollama at `http://localhost:11434`; set `OLLAMA_API_BASE` for another
host. Results are labelled with the provider `litellm` and the model you gave
(`ollama/llama3.2`). A local model's answers say how *that* model ranks you, which is
useful for development and for open-weight models, but is not what ChatGPT or Claude
users see.

Other backends use the same slot, with the credentials LiteLLM expects:

| Backend | `--model` value | Credentials |
|---------|-----------------|-------------|
| OpenRouter | `litellm=openrouter/<vendor>/<model>` | `OPENROUTER_API_KEY` |
| Azure OpenAI | `litellm=azure/<deployment>` | `AZURE_API_KEY`, `AZURE_API_BASE`, `AZURE_API_VERSION` |
| vLLM / any OpenAI-compatible server | `litellm=hosted_vllm/<model>` | `HOSTED_VLLM_API_BASE` |

The `litellm` slot answers from model memory only; `--grounded` web search is available
for OpenAI, Anthropic, Google and Perplexity.

## Notes per provider

- **Anthropic**: PromptBeacon never sends `temperature` to Claude models (current models
  reject non-default values), including Claude models reached through the `litellm` slot.
  `with_temperature()` therefore has no effect on Claude.
- **Google**: either `GOOGLE_API_KEY` or `GEMINI_API_KEY` works; if both are set,
  `GOOGLE_API_KEY` is used. Model IDs may be given with or without the `gemini/` prefix.
- **Perplexity**: Perplexity now serves Sonar requests through its Agent API.
  PromptBeacon still calls the OpenAI-compatible endpoint with `sonar`, which Perplexity
  documents as working during its migration; grounded scans read the cited URLs from
  either `citations` or `search_results`.
- **Web-grounded scans** (`--grounded`) use the provider's own SDK with the same model
  you chose for that provider.

## Costs

Cost estimates come from the price map bundled with the installed LiteLLM, so they work
offline and do not change during a run. Set `LITELLM_LOCAL_MODEL_COST_MAP=False` to have
LiteLLM fetch its latest prices instead. A model missing from the map gets no estimate
(`cost_status: "unknown"` or `"partial"`), never a misleading `$0`. Local models cost
nothing to call and are reported without a price.
