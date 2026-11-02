# PromptBeacon Roadmap

## Completed in v0.1.0

### Core Functionality
- [x] Beacon class with fluent API
- [x] Multi-provider support (OpenAI, Anthropic, Google) via LiteLLM
- [x] Brand mention extraction with sentiment analysis
- [x] Visibility scoring algorithm (0-100 scale)
- [x] Competitor comparison and benchmarking

### Statistical Analysis
- [x] Confidence intervals for visibility scores
- [x] Volatility scoring for trend stability
- [x] Significance testing for score changes
- [x] Trend detection (up/down/stable)

### Storage & History
- [x] DuckDB-based local storage
- [x] Historical data tracking
- [x] Scan comparison functionality
- [x] SQL queries for trend analysis

### Reporting
- [x] Multiple export formats (JSON, CSV, Markdown, HTML)
- [x] pandas DataFrame export
- [x] Explainable insights with evidence quotes
- [x] Actionable recommendations with priorities

### CLI
- [x] `scan` command for visibility analysis
- [x] `compare` command for competitor benchmarking
- [x] `history` command for trend viewing
- [x] `providers` command for status check
- [x] Multiple output formats

---

## Completed in v0.3.0

### BeaconGuard
- [x] Real-time brand safety analysis (`BeaconGuard` class)
- [x] `GuardResult` pydantic model with risk levels
- [x] `is_brand_anti_recommended()` utility
- [x] LangChain integration (callback handler + output parser)
- [x] Generic middleware with `on_high_risk` callback
- [x] Optional `[langchain]` dependency group

## Completed in v1.0.0

### Measurement & rigor
- [x] Share of Voice (presence-based, per-provider + aggregate + rank)
- [x] Stability scanning (repeat-N trust score, confidence interval, flip-flop detection)
- [x] LLM-based smart extraction (opt-in `with_smart_extraction()`)
- [x] LLM-generated, evidence-linked recommendations (opt-in `with_smart_recommendations()`)

### Adoption & DX
- [x] Keyless demo mode (`MockLLMClient` + fixtures, `Beacon.demo()`, `promptbeacon demo`)
- [x] HTML dashboard (`to_dashboard_html`, `promptbeacon dashboard`)
- [x] Modern logo + README screenshots

### CI-native
- [x] `Report.assert_visibility()` + `VisibilityAssertionError`
- [x] pytest plugin (`@pytest.mark.visibility`)
- [x] GitHub Action (`action.yml`)
- [x] CLI assertion flags (`--assert-min-score/-sov/-stability`)

### Polish
- [x] Refresh default models (claude-haiku-4-5); Production/Stable status
- [x] Hosted docs site (mkdocs-material)

## Completed in v1.3.0

- [x] Category-aware prompts (`with_category`, opt-in inference, competitor fallback)
- [x] Clean machine-readable CLI output; csv/html formats
- [x] CLI history saved by default
- [x] Prompt counts above 10; pinned prompt sets never truncated
- [x] Grounded cost estimates with `cost_status`
- [x] Concurrent providers
- [x] README badge (SVG + shields endpoint) and share cards (SVG/PNG, light/dark)
- [x] GitHub Action outputs, job summary, sticky PR comment; `promptbeacon ci`
- [x] Open-source project scans (`--repo`, `--pypi`, `--npm`)
- [x] MCP server and Claude Code plugin

## Completed in v1.4.0

- [x] Model choice per provider (`with_models`, `--model`, `PROMPTBEACON_<PROVIDER>_MODEL`,
      Action `models` input, MCP `models` argument, protocol `models`)
- [x] Local and other LiteLLM models (Ollama, OpenRouter, ...) through the `litellm` slot
- [x] Current default models from a single `DEFAULT_MODELS` table
- [x] `GEMINI_API_KEY` support
- [x] Fast import (LiteLLM loaded only for live requests)
- [x] Python 3.14; warnings-as-errors test suite
- [x] `promptbeacon init` (repository setup: workflow, badge snippet, secrets)
- [x] Cost cap (`--max-cost`, `with_max_cost`, Action and MCP `max_cost`) and estimates
- [x] Rank badge, score trend on share cards, crates.io and Hugging Face sources
- [x] MCP tools for estimate, compare, recommendations, history, funnel; setup for seven
      AI assistants; `ai-visibility-review` skill
- [x] Whole-name brand matching; ranks only from list items; appearance-order positions

---

## High Priority (next)

### Continuous monitoring
- [x] Scheduled scans (weekly GitHub workflow template that refreshes the badge)
- [ ] Webhook + Slack notifications on visibility / Share of Voice drop
- [ ] Email alerts for significant changes

### Enhanced Extraction
- [ ] Entity disambiguation (Nike vs Nike, Inc.)
- [ ] Multi-language extraction

### Prompt Library
- [x] Industry-specific prompt templates
- [x] Custom prompt template support
- [ ] Prompt effectiveness scoring
- [ ] A/B testing for prompts

### Provider Improvements
- [ ] Perplexity: move grounded scans to the Agent API (Sonar chat completions are
      served through it since September 2026)
- [ ] Provider-specific rate limiting
- [x] Retries (LiteLLM `num_retries`)
- [x] Cost tracking (grounded and base scans)
- [x] Cost budgeting (`--max-cost`, `with_max_cost`; 1.4.0)

---

## Medium Priority

### Visualization
- [x] HTML dashboard generation
- [ ] Terminal-based charts (sparklines, bar charts)
- [ ] Interactive (JS) dashboard charts

### Advanced Analytics
- [x] Share of Voice calculation
- [ ] Competitive gap analysis
- [ ] Sentiment trend correlation
- [ ] Brand mention co-occurrence

### Cloud Storage Options
- [ ] PostgreSQL backend
- [ ] SQLite backend option
- [ ] S3 export for reports
- [ ] Redis caching for API responses

---

## Lower Priority

### Enterprise Features
- [ ] Team/organization support
- [ ] API server mode
- [ ] Role-based access control
- [ ] Audit logging

### Integrations
- [ ] Langfuse tracing integration
- [ ] OpenTelemetry support
- [ ] Google Analytics export
- [ ] Notion/Airtable sync

### Additional Providers
- [x] Cohere support
- [x] Mistral support
- [x] Local models (Ollama) and any LiteLLM model (1.4.0)
- [ ] Custom provider plugins

---

## Technical Debt

- [ ] Increase test coverage to 90%+
- [x] Integration tests with mock LLM responses (`tests/integration`)
- [ ] Performance benchmarking
- [ ] Memory optimization for large scans
- [ ] Better error messages and debugging

## Documentation

- [x] API documentation site
- [ ] Plan the docs move off MkDocs Material (end of life announced for May 2027)
- [ ] Tutorial videos
- [ ] Industry-specific guides (e.g., "PromptBeacon for E-commerce")
- [ ] Best practices guide
- [ ] Architecture diagrams

---

## Contributing

Want to help? Pick an item from this list and open a PR. See [CONTRIBUTING.md](CONTRIBUTING.md) to get set up.

For questions or suggestions, open an issue on GitHub.
