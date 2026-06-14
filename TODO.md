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

---

## High Priority (next)

### Continuous monitoring (the big remaining gap)
- [ ] Scheduled / repeatable scans (cron-like)
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
- [ ] Provider-specific rate limiting
- [ ] Automatic retry with exponential backoff
- [ ] Cost tracking and budgeting

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
- [ ] Local models (Ollama)
- [ ] Custom provider plugins

---

## Technical Debt

- [ ] Increase test coverage to 90%+
- [ ] Add integration tests with mock LLM responses
- [ ] Performance benchmarking
- [ ] Memory optimization for large scans
- [ ] Better error messages and debugging

## Documentation

- [ ] API documentation site
- [ ] Tutorial videos
- [ ] Industry-specific guides (e.g., "PromptBeacon for E-commerce")
- [ ] Best practices guide
- [ ] Architecture diagrams

---

## Contributing

Want to help? Pick an item from this list and submit a PR! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

For questions or suggestions, open an issue on GitHub.
