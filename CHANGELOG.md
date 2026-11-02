# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - Unreleased

Set a repository up in one command, cap what a scan may spend, share a rank badge and a
score trend, scan crates and Hugging Face models; choose the model for each provider,
including local models, with current defaults, a faster start, and fixes for Python
3.12+. Use all of it from seven AI assistants through the MCP server. The AI
Recommendation Index is built but not yet run.

### Added
- **Use from your AI assistant.** A new setup page,
  [Use from AI assistants](https://yotambraun.github.io/promptbeacon/mcp/), with a
  tested snippet for Claude Code (plugin, `claude mcp add`, `.mcp.json`), Claude
  Desktop, Cursor (install link), VS Code with GitHub Copilot (install links, `code
  --add-mcp`, `.vscode/mcp.json` with a key prompt), Windsurf / Devin Desktop, Codex CLI
  (`config.toml`) and Gemini CLI (`settings.json`, and the Antigravity CLI), and how to
  pass keys and models in each. A test parses every snippet and decodes the install
  links.
- **MCP tools: `estimate`, `compare`, `recommendations`, `history`, `funnel` and
  `init_preview`,** thin wrappers over existing code: `estimate` prices a scan without
  sending anything; `compare` puts each brand side by side; `recommendations` returns
  the rule-based recommendations and explanations (or LLM-written ones with `smart:
  true`, one more request); `history` returns saved scans, the trend, the change since
  the previous scan and the existing significance check; `funnel` uses Tavily with
  `TAVILY_API_KEY` and the offline mock backend without it; `init_preview` shows what
  `promptbeacon init` would write, and the command to apply it, without writing
  anything.
- **Measure once, analyse for free:** `scan` and `project_scan` take `save_report`, and
  `compare`, `recommendations` and `share_assets` take `report_path` to read that report
  instead of scanning.
- **The answers behind a report.** `promptbeacon answers --report report.json` lists
  each answer of a saved report: prompt, provider and model, the tracked brands it
  names in order, the target's position and list rank, whether it recommends the
  target, an excerpt and the cited URLs. Filter with `--model`, `--mentions NAME` and
  `--missing NAME` (answers that leave a brand out); `-f jsonl`, `json` or `csv` export
  it with the full answer text. The new MCP `answers` tool returns the same rows from
  `report_path`, with excerpts instead of full text, paged (`offset`, `limit` up to
  100), so an assistant can check the evidence at no cost. In Python:
  `promptbeacon.reporting.answer_rows(report)`.
- **Define the measurement: your own prompts, aliases and stability runs** from the CLI
  and the MCP server. `scan` takes `--prompt` (repeatable), `--prompt-file` (one prompt
  per line, `#` comments) and `--alias`; the MCP `scan`, `project_scan` and `estimate`
  tools take `custom_prompts`, `aliases` and `stability_runs` (2-20, with a `stability`
  block in the result). Cost estimates and `max_cost` count the custom prompts and the
  runs. `configure_beacon` has the same options (`prompts`, `aliases`,
  `stability_runs`).
- **`ai-visibility-review` skill** in the plugin: a full review that checks the keys,
  prices the scan and asks before spending, scans once, then compares, reads the
  answers behind the numbers, checks sources, history and significance, and ends with
  evidence and next steps. It is a plain `SKILL.md`, usable by other agents.
- New docs page: [Python API](https://yotambraun.github.io/promptbeacon/python/), whose
  examples run offline and are tested.
- **`promptbeacon init`.** Reads `pyproject.toml`, `package.json` or `Cargo.toml`, the
  README and the git remote (no network), proposes a category with its basis (confirm or
  change it in a terminal; `--category` / `--competitor` skip the questions), and writes
  `.github/workflows/ai-visibility.yml`: weekly, using `yotambraun/promptbeacon@v1`, with
  a commented `models` example, a `max-cost` cap and badge, rank badge, card and trend
  paths. It shows new files in full and changed files as a diff and asks before writing;
  it never replaces a file without confirmation (`--yes` writes new files only, `--force`
  also replaces changed ones, and without a terminal nothing is written). Re-running it
  changes nothing. It works without API keys, prints the exact `gh secret set` command
  and the README badge snippet, can run a labelled demo scan, and ends with next steps.
  `--protocol` also writes a pinned `.promptbeacon/protocol.json`; `--dry-run` previews;
  `--format json` returns the plan.
- **Cost cap: `--max-cost USD`** on `scan`, `compare`, `sources`, `dashboard`, `badge`
  and `card` (Python `Beacon.with_max_cost()`, Action input `max-cost`, MCP argument
  `max_cost`). The scan is priced first from LiteLLM's price map and refuses to start
  above the cap, with the estimate and how to lower it; during the scan no new request
  starts once the spend plus the requests in flight reaches the cap, and the result is
  marked partial (`report.partial`, `report.budget`) in every output, the CI summary,
  the new `partial` Action output, the badge and the card. Models with no known price
  (for example local Ollama) count as $0 and are named. `scan --estimate` prints the
  estimate without sending anything; `Beacon.estimate_cost()` returns it; `ci
  --max-cost` gates on a report's cost.
- **Rank badge:** `badge --metric rank` ("AI rank: #2 of 9 · python http clients", ties
  say "tied"), with its shields.io endpoint JSON, from a scan with a category and at
  least two competitors. Demo ranks are grey and say "demo". Action input
  `rank-badge-path`; the MCP `share_assets` tool writes `rank.svg` and `rank.json` when it
  can.
- **Score trend on share cards:** with three or more real scans measured the same way,
  SVG and PNG cards show a score sparkline. The scores come from the local history or,
  in CI, from a trend file (`card --trend .promptbeacon/trend.json`, Action input
  `trend-path`). Demo data never gets a trend.
- **crates.io and Hugging Face sources:** `--crate serde` and `--hf owner/name` (also
  `datasets/owner/name` and `spaces/owner/name`) on `scan`, `badge` and `card`, `crates:`
  and `hf:` in `Beacon.from_project()` and the MCP tools. Only the public crates.io and
  Hugging Face Hub APIs are read. A model's `pipeline_tag` or a dataset's
  `task_categories` is used as the category. A keyless `--demo` run carries on offline
  with the project name.
- **GitHub Action:** `protocol` input (a pinned protocol file; `brand` is then
  optional), and `max-cost`, `rank-badge-path` and `trend-path` inputs.
- `promptbeacon.analysis.statistics.proportion_interval()`: a Wilson score interval for
  rates such as "mentioned in 12 of 90 answers".
- `promptbeacon --version`; `promptbeacon demo` ends with the next step (the matching
  `scan ... --estimate` command and `promptbeacon init`).
- `Database.connection`, the DuckDB connection the storage docs use for custom SQL.
- **AI Recommendation Index (not launched):** a generator in the repository's `index/`
  folder with 30 pinned category protocols, mention-rate ranking with confidence
  intervals, a static site with methodology and rank badges, a labelled demo build with
  placeholder names, and a monthly workflow that is disabled until the maintainer enables
  it. No rankings have been published. Docs page:
  [AI Recommendation Index](https://yotambraun.github.io/promptbeacon/recommendation-index/).
- **Model choice per provider.** `Beacon.with_models({"anthropic": "claude-sonnet-5-5"})`
  (or `with_models(openai="gpt-6-sol")`), the repeatable CLI option
  `--model provider=model_id` / `-m` (on `scan`, `compare`, `sources`, `dashboard`,
  `badge`, `card`), the environment variables `PROMPTBEACON_<PROVIDER>_MODEL`, a `models`
  input on the GitHub Action, a `models` field in scan protocols and in
  `@pytest.mark.visibility`, and a `models` argument on the MCP `scan`, `project_scan`,
  `sources` and `share_assets` tools. When no providers are given, the providers you
  name models for are the ones queried.
- **Local and other LiteLLM models.** A new `litellm` provider slot passes any LiteLLM
  model string through, so `--model litellm=ollama/llama3.2` scans a local Ollama model
  with no API key, and OpenRouter, Azure or a vLLM server work the same way.
- `promptbeacon providers` (and the MCP `providers` tool) show the model each provider
  will use.
- New docs page: [Models & local LLMs](https://yotambraun.github.io/promptbeacon/models/).
- Python 3.14 support.

### Changed
- `Beacon.with_prompts()` checks its prompts: an empty list, a blank or duplicate
  prompt, more than 1,000 prompts, or a placeholder other than `{category}` (a literal
  brace must be written `{{`) raise `ValueError` when the prompts are set, instead of a
  `KeyError` or a skewed count during the scan. Surrounding spaces are removed.
- `--stability` needs at least 2 runs (one run measures no stability); `0` still means a
  single scan.
- MCP tools describe every argument in their schema, say what they cost, and carry
  read-only and open-world hints. Real scans made by the MCP `scan` and `project_scan`
  tools are saved to the local history, as CLI scans are (`save_history: false` skips
  it).
- The docs lead with three entry points (terminal, AI assistant, CI), and the
  navigation runs from getting started through assistants, CI, the Python API, models,
  sharing and the Index to the reference. "Claude Code & MCP" is now "Use from AI
  assistants".
- **Default models updated** (verified 2026-11-01 against the providers' model lists and
  LiteLLM's price map): OpenAI `gpt-6-luna` (was `gpt-4o-mini`), Anthropic
  `claude-haiku-5-5` (was `claude-haiku-4-5`), Google `gemini-3.5-flash-lite` (was
  `gemini-2.0-flash`, which Google has shut down), Cohere `command-r7b-12-2024` (was the
  deprecated `command-r`). Mistral (`mistral-small-latest`) and Perplexity (`sonar`) are
  unchanged. Scores from the new defaults are not directly comparable with earlier
  scans; pin `--model` to keep a trend on one model.
- All defaults now come from one table, `promptbeacon.core.config.DEFAULT_MODELS`, used
  by the live, demo and web-grounded clients.
- `temperature` is never sent to Claude models, which reject non-default values.
- **Faster start.** LiteLLM is imported on the first live request instead of at import
  time, and uses its bundled price map unless `LITELLM_LOCAL_MODEL_COST_MAP` is set (no
  network fetch or warning at startup). Measured on Python 3.12 with an installed wheel:
  `import promptbeacon` went from about 2.0 s to 0.2 s, and `promptbeacon demo` from
  about 2.1 s to 0.25 s.
- A scan in which no provider query succeeded now raises `ScanError` naming the first
  error and its type (for example `AuthenticationError: ...`), instead of returning a
  zero score built from failed answers. Provider errors on individual answers are
  recorded as `ExceptionType: message`.
- Dependencies: `litellm>=1.106.0` (the first release that knows the new default
  models; this also excludes the compromised 1.82.7 and 1.82.8 releases); `rich` up to
  15.x and `duckdb` up to 2.x are allowed. The `cli` extra is empty (its packages are
  core dependencies) and kept for compatibility.
- The docs no longer publish per-model price tables; cost estimates come from LiteLLM.
- `promptbeacon --help` leads with the developer use case and groups commands into
  "Start here", "Analyse", "Share and track" and "Integrations".
- Project categories read better: "higher level HTTP client library" becomes "http
  client", and "serialization/deserialization framework" becomes "serialization
  framework".
- History files record each scan's measurement tier and categories (older files gain
  the columns automatically; their rows are left out of card trends).
- New dependency on Python 3.10 only: `tomli` (for `init`; Python 3.11+ uses `tomllib`).

### Fixed
- **Scores for short or common brand names were inflated by substring matches.** A
  brand was found anywhere in the text, so `uv` counted in every answer that named
  "uvicorn", `React` in "Preact" and `Ray` in "array". Brands now match only as whole
  names, through one shared matcher (`promptbeacon.extraction.matching`) used for
  mentions, ranks, recommendations, citation attribution (including web-grounded
  citations), the funnel and the AI Recommendation Index. Names with punctuation match
  as written (`C++`, `.NET`, `Node.js`, `scikit-learn`), non-ASCII names work, and a
  hyphenated compound is a different name (`pytest` is not found in "pytest-asyncio").
- **Numbers inside sentences were read as ranks.** "We recommend Python 3.12 with
  httpx" gave httpx rank 3, because any digit followed by a period counted as a list
  number. A rank now comes only from a numbered item at the start of a line (Markdown
  `1. **Name**`, `**1. Name**` and `### 1. Name` included), an ordered bullet or a
  recommending sentence; recommending sentences no longer stop at the dot in names such
  as `Node.js`.
- **`average_position` was not the order of appearance.** Each mention's `position`
  counted through the brand list (target first), not the text, so the target always
  looked named first; and an average of 0.0 (always named first) was reported as
  `None`. `position` is now the order in which the brand first appears among the
  tracked brands the answer names (0 = first), mentions are returned in text order, and
  `average_position` is the mean of that order over the answers that name the brand.
  Smart extraction (`--smart`) orders mentions the same way.
- A custom prompt without `{category}` was asked once per category, so a scan with two
  categories asked it twice and counted the answers twice. It is now asked once.
- The "actively recommended in N responses" insight counted mentions, so it could
  exceed the number of answers ("in 14 responses" from 10 prompts). It now counts
  answers ("in 5 of 10 answers").

  **Measured scores change** for brands whose name appears inside other words (short
  names such as `uv`, `Ray` or `React` most of all): their mention rate, share of voice
  and score drop to what the answers actually say, and so can a competitor's. Position
  scores change where an answer had version numbers or decimals at a rank's place.
  Saved history keeps the old numbers; compare scans made with 1.4.0 with each other.
  The keyless demo's numbers are unchanged (its answers name brands as whole words).
- **Scans failed under `-W error` / `filterwarnings = error` on Python 3.12+.**
  `datetime.utcnow()` raised a `DeprecationWarning` inside every provider query, which
  was swallowed and reported as "All provider queries failed. Check API keys and
  network." Timestamps now come from `datetime.now(timezone.utc)` (stored as naive UTC,
  as before).
- Errors in PromptBeacon's own code are no longer reported as provider failures; they
  propagate with their original type.
- `GEMINI_API_KEY` is accepted for Google (`GOOGLE_API_KEY` still wins when both are set).
- The `.env` file is now found from the working directory, as documented. It was
  searched for upwards from the installed package, so a project's `.env` was only found
  when the virtualenv lived inside the project.
- Perplexity grounded results also read cited URLs from `search_results` when a response
  has no `citations` list.
- Smart-extraction calls (`--smart`) are now included in a scan's cost.
- `Database("~/...")` expands the home directory instead of creating a `~` folder.
- CLI error messages no longer lose bracketed text such as `promptbeacon[mcp]` (it was
  read as Rich markup), a keyless real scan suggests `--demo` or a local model, and
  library warnings are shown once instead of twice.
- The storage docs' SQL examples run on DuckDB (they used SQLite functions).
- LiteLLM no longer prints its provider list to stdout when pricing an unknown model, so
  `-f json` output stays valid.

### Internal
- CI tests Python 3.10-3.14 with the matrix interpreter (the committed `.python-version`
  previously made every job run 3.11), runs pytest with warnings as errors, type-checks
  with mypy, and builds the docs with `--strict`. Actions and pre-commit hooks updated to
  current versions.
- Tests never see real provider keys, even when a local `.env` defines them.
- README and docs images are regenerated from real demo runs by
  `scripts/render_assets.py`.

## [1.3.0] - 2026-10-04

A release about the first result being right, and about results you can share.

### Fixed
- **Prompts now ask about your category.** Without a category, every prompt read
  "What are the best general brands?", which made the score meaningless. Set one with
  `--category` / `.with_category()`; without one, PromptBeacon asks "alternatives to
  &lt;competitor&gt;" questions when you give competitors, and otherwise warns clearly.
  Reports record `categories` and `prompt_strategy`.
- **The demo no longer adds Adidas and Puma to every brand.** It uses your competitors,
  or clearly labelled placeholders ("Competitor A", "Competitor B"), and your category.
  Each competitor's presence now varies, sources are general sites linked to your topic,
  and cited sources are listed once instead of twice.
- **`--format json` is valid JSON.** A banner was printed on stdout and long lines were
  wrapped at the terminal width. Machine formats now go to stdout untouched; progress,
  notices and errors go to stderr.
- **`scan` then `history` shows your scan.** Real CLI scans are saved to
  `~/.promptbeacon/data.db` by default (`--no-save` to skip, `--storage` to choose a
  file, `PROMPTBEACON_HOME` to move the directory). Demo scans are not saved unless you
  pass `--storage`. Saving the default history is best-effort, so a read-only home
  directory never fails a scan.
- **`--prompts n` / `with_prompt_count(n)` above 10 works.** Counts were silently capped
  at 10, and pinned protocol prompt sets were cut to their first 10. Larger counts are
  extended deterministically; impossible counts raise a clear error.
- **Grounded scans report a cost estimate** from token usage and known per-search fees,
  instead of no cost. Reports gain `cost_status` (complete / partial / unknown / none),
  and outputs say "at least $X" when a fee could not be priced.
- **Empty API keys count as not configured** (for example `OPENAI_API_KEY=` in CI).
- **GitHub Action:** multi-word categories and competitors are no longer split on
  spaces, and inputs are passed to the shell through environment variables.

### Added
- **Badges and share cards.** `promptbeacon badge` writes an SVG badge and a shields.io
  endpoint JSON; `promptbeacon card` writes a 1200×630 card in light and dark, with an
  optional PNG (`pip install 'promptbeacon[share]'`). Both can render from a saved
  `scan -f json` report. Demo output is always labelled as demo.
- **Open-source projects.** `scan --repo owner/name`, `--pypi pkg`, `--npm pkg` (and
  `--project kind:ref`) read public metadata, guess the category and competitor
  candidates, show where each guess came from, and run a developer-oriented scan. Also
  available as `Beacon.from_project()`. New sources are one small class
  (`promptbeacon.projects.MetadataSource`).
- **Category inference (opt-in):** `--infer-category` / `.with_category_inference()`
  names the category, and suggests competitors when none are given, with one model call.
- **GitHub Action outputs, job summary and PR comment.** Outputs `score`,
  `share-of-voice`, `rank`, `presence`, `stability`, `tier`, `passed`, `report-path`; a
  Markdown job summary; an optional sticky PR comment; and `badge-path`,
  `badge-endpoint-path` and `card-path` inputs. Thresholds are applied last.
- **`promptbeacon ci --report report.json`** writes the same outputs, summary and gate for
  any CI system.
- **MCP server and Claude Code plugin.** `promptbeacon mcp` (`pip install
  'promptbeacon[mcp]'`) exposes `scan`, `project_scan`, `sources`, `share_assets` and
  `providers`. The repository is also a plugin marketplace with three skills.
- `--category` on `demo`, `quick`, `compare` and `dashboard`; `--demo` on `compare`;
  `csv` and `html` CLI formats; `configure_beacon()` for building a scan from plain
  options; workflow templates for a weekly badge and a PR check.

### Changed
- **Default prompts are worded for any category.** They no longer add "brands" or
  "company" ("What are the best project management software brands?" is now "What are
  the best project management software?"), so they read naturally for software,
  libraries and services as well as consumer goods. The category is used exactly as you
  give it, so phrase it the way a buyer would ask ("running shoes", "python http
  client"). Industry template sets (`with_industry`) and pinned protocol prompts are
  unchanged. Scores from default prompts are not directly comparable with 1.2.0 runs.
- Providers are queried concurrently (each with its own rate limit), so multi-provider
  scans take about as long as the slowest provider.
- Scans without a category but with competitors use "alternatives to &lt;competitor&gt;"
  prompts instead of the generic set (your own `with_prompts()` templates are never
  replaced). Scores from such scans are not comparable with earlier category-less runs.

## [1.2.0] - 2026-06-19

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

## [0.1.1] - Never released

Never published to PyPI. These changes were made after 0.1.0 and first shipped in
**0.2.0** (2026-02-06); the entry is kept for history.

### Fixed

- Removed `instructor` dependency — no longer required at runtime
- Fixed license field in `pyproject.toml` to use SPDX identifier (`Apache-2.0`)
- Updated default model names: Anthropic to `claude-3-5-haiku-20241022`, Google to `gemini-2.0-flash`
- Added structured logging throughout the package

### Improved

- Sentiment analysis now detects negation (e.g., "not great" correctly classifies as negative)
- Added GEO-specific keywords for more relevant prompt generation

## [0.1.0] - 2026-01-16

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
