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

## High Priority

### Enhanced Extraction
- [ ] LLM-based mention extraction (using Instructor)
- [ ] More sophisticated sentiment analysis
- [ ] Entity disambiguation (Nike vs Nike, Inc.)
- [ ] Context-aware recommendation detection

### Prompt Library
- [ ] Industry-specific prompt templates
- [ ] Custom prompt template support
- [ ] Prompt effectiveness scoring
- [ ] A/B testing for prompts

### Provider Improvements
- [ ] Provider-specific rate limiting
- [ ] Automatic retry with exponential backoff
- [ ] Cost tracking and budgeting
- [ ] Model selection per provider

---

## Medium Priority

### Visualization
- [ ] Terminal-based charts (sparklines, bar charts)
- [ ] HTML report with interactive charts
- [ ] Dashboard generation
- [ ] Trend visualization

### Scheduling & Automation
- [ ] Scheduled scans (cron-like)
- [ ] Webhook notifications
- [ ] Email alerts for significant changes
- [ ] Slack/Discord integration

### Advanced Analytics
- [ ] Share of Voice calculation
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
- [ ] Cohere support
- [ ] Mistral support
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
