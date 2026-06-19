# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2026-06-20

### Added
- **Funnel LLM mode**: the glass-box funnel can now use an **LLM planner + LLM-judge
  reranker** — `run_funnel(..., complete=...)` or `promptbeacon funnel --smart` — for
  higher-fidelity fan-out and ranking, with graceful fallback to the deterministic
  planner / lexical reranker (the keyless demo is unchanged). New
  `funnel.llm_generate_sub_queries` and `funnel.llm_rerank`.
- **First-class Tavily key handling**: `get_tavily_api_key()` / `has_tavily_api_key()`,
  shown in `promptbeacon providers`, with an actionable error linking to tavily.com.

### Fixed
- **`.env` files now load.** `python-dotenv` was a dependency but `load_dotenv()` was
  never called, so a `.env` file silently did nothing. PromptBeacon now auto-loads
  `.env` on import (new `core.config.load_env()`), so `OPENAI_API_KEY`,
  `TAVILY_API_KEY`, etc. work from a `.env` for both the library and the CLI — without
  overriding values already set in the real environment.

## [1.1.0] - 2026-06-19

The web-grounded, glass-box release — PromptBeacon now measures **real AI-search
visibility** (not just model memory), with distribution-grade rigor and a
funnel view no citation tracker offers.

### Added

- **Glass-box agentic funnel** (`promptbeacon funnel` / `funnel.run_funnel`): models
  the agentic-search funnel locally and instruments every stage — fan a prompt into
  sub-queries, run an observable retrieve → rerank → cite pipeline, and report
  **where the brand drops out** (`sub_query_coverage`, `rerank_survival_rate`,
  `retrieval_to_citation_ratio`, `stage_failure`). Unlike citation trackers, it sees
  the funnel, not just the survivors. Keyless `--demo`; live web search via Tavily
  (`TAVILY_API_KEY`, called over httpx — no extra SDK). New `promptbeacon.funnel`
  package (`FunnelReport`, `run_funnel`, `SearchBackend`).
- **Web-grounded scanning** (`Beacon.with_grounding()` / `promptbeacon scan --grounded`
  / `sources --grounded`): query a provider's **native web-search tool** through its
  official SDK so results reflect what AI *search* returns — with the **real sources
  it cited** and a `retrieved_but_uncited` flag for sources the engine pulled but
  didn't use. Covers **Anthropic** (Brave-backed `web_search`), **OpenAI** (Responses
  `web_search`), **Gemini** (Google Search grounding), and **Perplexity** (sonar) via
  the new `[grounded]` extra (`pip install 'promptbeacon[grounded]'`); Mistral/Cohere
  fall back to base completion. `ProviderResult.grounded` records which results were
  grounded, and `measurement_tier` is `api_grounded` only when grounding actually ran
  (honest: it approximates, but does not equal, the consumer product).
- **Source attribution**: every scan now ranks the source **domains** that AI
  answers cite (`report.source_attribution`), classifies each
  (reddit / wikipedia / news / review / academic / social / video / code / web),
  shows its share of all citations, and flags which domains cite your brand —
  the actionable GEO lever ("get cited on these sites"). New
  `promptbeacon sources "<brand>"` command and a **Top Source Domains** table in
  text reports. New `SourceAttributionReport` / `SourceAttributionEntry` schemas
  and `analysis.sources.aggregate_source_attribution()`.
- **Measurement-tier honesty label**: `report.measurement_tier`
  (`demo` | `base_model` | `api_grounded`) makes explicit how a scan was
  measured — shown as a one-line banner in the CLI and included in JSON — so
  base-model results (the model's training memory) are never mistaken for live
  AI-search results.
- **Richer citations**: `Citation` now carries `source_rank`, `source_type`,
  `query` (the prompt that surfaced it), and `retrieved_but_uncited` (all
  additive and back-compatible).
- **Distribution-grade stability** ("don't measure once"): stability scans now
  add a **percentile-bootstrap** confidence interval
  (`StabilityReport.score_bootstrap_interval`, distribution-free, alongside the
  normal-approximation CI) and **per-source stability**
  (`StabilityReport.source_stability` / new `SourceStability`) — which domains
  the engines cite on every run vs. flip-flop. `bootstrap_ci()` added to
  `analysis.statistics`.
- **Buyer-intent prompt sets**: `generate_buyer_intent_prompts(category, n=50)`
  produces a stable set of buyer-intent prompts for the recommended 50–200
  prompt measurement protocol.
- **Reproducible protocols**: pin a scan in a JSON file and re-run it
  identically with `promptbeacon scan --protocol protocol.json` (new
  `promptbeacon.protocol` module: `ScanProtocol`, `load_protocol`,
  `build_beacon`), so CI trends stay comparable over time.

### Changed

- Demo fixtures now cite realistic, varied domains (Reddit, Wikipedia, Consumer
  Reports, major news) so `promptbeacon demo` / `--demo` showcases source
  attribution with no API keys.

## [1.0.0] - 2026-06-14

The first stable release — PromptBeacon is now **the open-source GEO engine to
measure, track, and CI-test how AI recommends your brand**. Repositioned for
developers and agencies, with a keyless first run and the statistical rigor a
real monitoring pipeline needs.

### Added

- **Keyless demo mode**: `Beacon("Nike").demo().scan()` and `promptbeacon demo "Nike"`
  (plus a `--demo` flag on `scan`/`quick`/`dashboard`) run against a realistic offline
  mock — instant value with **no API keys**. New `MockLLMClient` + deterministic fixtures.
- **Share of Voice**: presence-based SoV vs competitors, computed on every scan —
  `report.share_of_voice` (`.target_share`, `.target_presence_rate`, `.target_rank`,
  `.aggregate`, `.by_provider`). New `calculate_share_of_voice()`.
- **Stability scanning**: `Beacon(...).with_stability(N).scan_stability()` (CLI `--stability/-r`)
  repeats each prompt N times and reports a 0-100 `report.stability.stability_score`, a
  confidence interval, run-to-run volatility, and per-prompt flip-flop detection — so you
  know how much to trust a single number. Bypasses the cache so runs actually vary.
- **CI-native testing**: `report.assert_visibility(min_score=, min_share_of_voice=, ...)`
  raising `VisibilityAssertionError`; a **pytest plugin** (`@pytest.mark.visibility(...)`,
  auto-registered, skips cleanly without keys); a composite **GitHub Action** (`action.yml`);
  and CLI `--assert-min-score` / `--assert-min-sov` / `--assert-min-stability` flags (exit 1 on fail).
- **HTML dashboard**: `to_dashboard_html(report)` and `promptbeacon dashboard "Nike"` produce a
  single self-contained, shareable HTML file (SoV bar, score breakdown, sentiment donut,
  stability band, optional history sparkline) — no SaaS.
- **Smart mode (LLM)**: opt-in `with_smart_extraction()` (LLM + structured output instead of
  regex) and `with_smart_recommendations()` (evidence-linked, actionable GEO guidance), enabled
  together via the CLI `--smart` flag. Falls back to regex/rule-based on any error.
- **Brand assets**: a modern "Signal Beacon" logo set, plus README screenshots.
- **Hosted docs site** (mkdocs-material) at https://yotambraun.github.io/promptbeacon/.

### Changed

- **Repositioned** as a developer/CI-native GEO measurement engine; README, docs, and PyPI
  metadata rewritten around the new narrative. BeaconGuard is now a documented secondary feature.
- Default Anthropic model updated to **`claude-haiku-4-5`** (the previous default,
  `claude-3-5-haiku-20241022`, was retired and would 404 on real scans).
- Package status promoted to **Production/Stable**; added a `[docs]` extra and a `pytest11`
  entry point.

## [0.3.0] - 2026-03-20

### Added

- **BeaconGuard**: Real-time brand safety analysis for LLM outputs — pure local processing, no API calls
  - `BeaconGuard` class with configurable flags for competitor mentions, negative sentiment, brand absence, and anti-recommendations
  - `GuardResult` pydantic model with risk level, flags, sentiment details, citations, and recommendation detection
  - `is_brand_anti_recommended()` utility for detecting negative recommendation patterns
- **LangChain Integration**: `BeaconGuardCallbackHandler` and `BeaconGuardOutputParser` for LangChain pipelines
  - Lazy import — `langchain-core` is NOT a hard dependency
  - Optional `[langchain]` dependency group: `pip install 'promptbeacon[langchain]'`
- **Generic Middleware**: `BeaconGuardMiddleware` callable with optional `on_high_risk` callback for any LLM pipeline
- **New examples**: `guard_example.py` (BeaconGuard basics), `langchain_guard.py` (middleware usage)

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
