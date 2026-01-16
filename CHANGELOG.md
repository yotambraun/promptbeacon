# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
