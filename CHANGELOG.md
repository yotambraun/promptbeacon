# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-02-06

### Added

- **Citation Tracking**: New `extract_citations()` module detects URLs and attribution phrases ("According to X", "Source: X") in LLM responses, associating each citation with the nearest brand mention
- **`Citation` and `CitationSummary` schema types** on `ProviderResult` and `Report`
- **Brand Aliases**: `Beacon.with_aliases("Nike Inc", "Nike Corporation")` — alternative names are matched and credited to the primary brand
- **Industry Prompt Templates**: `Beacon.with_industry("ecommerce")` — pre-built prompts for 7 verticals (ecommerce, saas, finance, healthcare, travel, food, tech)
- **Response Caching**: `Beacon.with_cache()` — file-based caching keyed by (prompt, provider, model) with configurable TTL (default 24h)
- **Score Breakdown**: `report.metrics.score_breakdown` shows the 0-100 sub-score for each factor (mention_frequency, sentiment, position, recommendation) before weighting
- **`promptbeacon quick` CLI command**: Fast 3-prompt scan with cheapest available provider
- **3 New Providers**: Mistral (`mistral-small-latest`), Cohere (`command-r`), Perplexity (`sonar`) — 6 providers total
- **`Beacon.with_scoring_weights()`**: Customise the four scoring weights via the fluent API
- **Integration tests**: Full scan pipeline tests with mocked LLM responses (`tests/integration/test_scan_pipeline.py`)
- **CLI smoke tests**: Verify `promptbeacon scan` and `promptbeacon providers` work end-to-end (`tests/integration/test_cli.py`)
- **Sources Cited section** in CLI text output, Markdown, and HTML exports
- **Score Breakdown table** in CLI text output
- **Prerequisites section** in README with API key setup instructions

### Fixed

- **Anti-recommendation detection**: `is_brand_recommended()` now returns `False` for phrases like "recommend against Nike", "avoid Nike", "don't recommend Nike"
- **Honest confidence scores**: Mentions use signal-quality-based confidence (0.5-0.8) instead of a hardcoded 0.7
- **Evidence-based recommendations**: Recommendations now reference actual scan data — missed prompt categories, negative context snippets, provider mention rates, and competitor score gaps
- **Stale model names** in `docs/api-reference.md` (Anthropic and Google models updated)

### Changed

- `ScoringWeights` class now has a detailed docstring explaining the rationale for each default weight
- Neutral sentiment scoring documented: counts as 50% positive because being mentioned neutrally is still better than not being mentioned

## [0.1.1] - 2025-01-20

### Fixed

- Removed `instructor` dependency — no longer required at runtime
- Fixed license field in `pyproject.toml` to use SPDX identifier (`Apache-2.0`)
- Updated default model names: Anthropic to `claude-3-5-haiku-20241022`, Google to `gemini-2.0-flash`
- Added structured logging throughout the package

### Improved

- Sentiment analysis now detects negation (e.g., "not great" correctly classifies as negative)
- Added GEO-specific keywords for more relevant prompt generation

## [0.1.0] - 2024-01-16

### Added

- **Core Beacon Class**: Fluent API for brand visibility monitoring
  - `with_competitors()` - Add competitor brands to track
  - `with_providers()` - Select LLM providers (OpenAI, Anthropic, Google)
  - `with_categories()` - Set analysis topics
  - `with_storage()` - Enable DuckDB persistence
  - `scan()` / `scan_async()` - Run visibility analysis

- **Multi-Provider Support**: Query multiple LLMs via LiteLLM
  - OpenAI (GPT-4o-mini)
  - Anthropic (Claude 3 Haiku)
  - Google (Gemini 1.5 Flash)

- **Brand Extraction**: Automatic mention detection
  - Case-insensitive brand matching
  - Context extraction around mentions
  - Position tracking in responses

- **Sentiment Analysis**: Understand brand perception
  - Positive/neutral/negative classification
  - Weighted sentiment scoring
  - Evidence quotes for each classification

- **Visibility Scoring**: Comprehensive 0-100 scoring
  - Mention frequency weighting
  - Sentiment impact
  - Position prominence
  - Recommendation rate

- **Statistical Analysis**:
  - Confidence intervals (95%)
  - Volatility scoring
  - Significance testing
  - Trend detection (up/down/stable)

- **Local Storage**: DuckDB-powered persistence
  - Historical data tracking
  - Scan comparison
  - Trend queries

- **Export Formats**:
  - JSON
  - CSV
  - Markdown
  - HTML
  - pandas DataFrame

- **CLI Interface**:
  - `promptbeacon scan` - Run visibility analysis
  - `promptbeacon compare` - Compare against competitors
  - `promptbeacon history` - View historical trends
  - `promptbeacon providers` - Check provider status

- **Explainable Insights**: Not just scores, but why
  - Evidence quotes from LLM responses
  - Category-based explanations
  - Impact levels (high/medium/low)

- **Actionable Recommendations**:
  - Prioritized action items
  - Rationale for each recommendation
  - Expected impact descriptions

### Technical

- Python 3.10+ support
- Async-first architecture
- Pydantic v2 data validation
- Type hints throughout
- Comprehensive test suite
- GitHub Actions CI/CD
- Multi-OS testing (Linux, Windows, macOS)
