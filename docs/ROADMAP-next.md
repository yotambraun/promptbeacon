# PromptBeacon: what's next

*Working notes for the maintainer, October 2026. Not linked from the site navigation.*

## 1. Where PromptBeacon stands

| Signal | Value | Source |
|---|---|---|
| GitHub stars / forks / open issues | 1 / 0 / 0 | `api.github.com/repos/yotambraun/promptbeacon` (2026-10-03) |
| Last push to `main` | 2026-06-19 | same |
| PyPI downloads | 38 last month, 6 last week; 675 in total | `pypistats.org/api/packages/promptbeacon/{recent,overall}` |
| Monthly downloads | Mar 2 · Apr 36 · May 54 · **Jun 460** · Jul 58 · Aug 27 · Sep 35 | pypistats, mirrors excluded |
| Repository topics | ai-assistant, cli, data-analysis, llm, monitoring, prompt-engineering, python, sentiment-analysis | GitHub API |
| Category search visibility | 0 appearances in the top 15 of 8 category searches ("generative engine optimization", "AI visibility brand LLM", "answer engine optimization", ...) | GitHub search API |

The June spike is the 1.0 launch; it decayed to the pre-launch baseline within a month.
Nothing in the product turned a first try into a second visit or a mention.

## 2. Why it isn't spreading (evidence)

1. **The first result was wrong.** With no category (as in every README example), the
   prompts read "What are the best general brands?"; the demo inserted Adidas and Puma as
   competitors for *any* brand; `--format json` was not valid JSON; `scan` then `history`
   showed nothing; `--prompts 50` silently ran 10. Each of these was reproduced on
   `main` (cea058d) and is fixed, with a regression test, in 1.3.0.
2. **Nothing to share.** The output lived in a terminal or a local HTML file. The tools
   growing fastest in this space give people an artifact: geo-score ships an SVG badge,
   shields endpoint JSON and a public leaderboard of 324 sites (619 stars in 25 days,
   25.8 stars/day); geo-optimizer-skill offers a live README badge "like a coverage
   badge" (980 stars, 7,010 PyPI downloads/month).
3. **Not where users already work.** Of the fastest risers in GEO/SEO searches, three are
   agent skills or MCP servers: open-seo-mcp-skills (104 stars/day), claude-seo
   (18,232 stars, 76.9/day), fire-your-seo-agency (17.4/day). Self-hosted dashboards grow
   at about one star a day (elmo 1.0, notra 0.8, getcito 1.3).
4. **Invisible in discovery.** Among competitors with 100+ stars the most common topics
   are `aeo` (14), `ai-visibility` (13), `answer-engine-optimization` (13),
   `claude-code` (12), `geo` (12), `chatgpt` (12), `generative-engine-optimization` (9).
   PromptBeacon uses none of them, its GitHub description is the old one, and its
   homepage field points at the 0.1.0 PyPI page.
5. **CI is a multiplier, not a hook.** CI-first tools barely grow on their own (aeorank
   with Action, App and PR checks: 15 stars; answerci: 4). In comparable developer tools
   the action repo always trails the core tool (ossf/scorecard 5,731 vs scorecard-action
   420; lighthouse-ci 7,104 vs lighthouse-ci-action 1,292). CI spreads *usage*; the
   badge and the result are what people see and repeat.

## 3. What the leaders do on the first screen

- **One keyless command that prints a score** (geo-score: `curl ... | python3 - stripe.com`;
  geo-optimizer-skill: one `uvx` command). Tools that need an API key before showing
  anything sit near one star a day.
- **Show proof immediately:** a GIF or terminal image, real numbers, a growth chart.
- **An embeddable artifact** (badge, card, public report) with a link back.
- **Packaging for agents** (Claude Code plugin, skills, MCP).
- **Clear audience framing.** Most target marketers ("fire your SEO agency"). Nobody owns
  *developers and open-source maintainers*; no public leaderboard ranks which libraries
  AI assistants recommend (closest: amplifying-ai/claude-code-picks, 71 stars;
  doesaipickyou.com, 0 stars).

## 4. Positioning

PromptBeacon is the **developer-native measurement library and CI check**: Python API,
CLI, GitHub Action, MCP server. Its distinct angle is **developers' own products and
open-source projects** ("does ChatGPT recommend my library?"). Saylent remains the
product for brand and website teams (auditing what AI says about a brand, site
gate-checks); PromptBeacon should not grow a hosted dashboard, site audits or marketing
workflows.

## 5. Bets

| Bet | Status | Evidence | Main risk |
|---|---|---|---|
| Fix the first result | **Done in 1.3.0** | Section 2.1 | None; regression tests guard each fix |
| Badge + shields endpoint + weekly workflow | **Done in 1.3.0** | geo-score, geo-optimizer-skill, codecov, scorecard | A badge on demo data could mislead: demo badges are grey and say "demo" |
| Share card (SVG/PNG, light/dark) | **Done in 1.3.0** | github-readme-stats (79,825 stars) shows how much people share good-looking cards | Base-model numbers read as "what ChatGPT says": the card always shows the tier |
| Action outputs, job summary, sticky PR comment | **Done in 1.3.0** | codecov / Lighthouse CI patterns | Fork PRs without write access: comment step only warns |
| `--repo` / `--pypi` / `--npm` | **Done in 1.3.0** | Unclaimed developer niche | Offline category guess can be off: shown with its basis, overridable, optional one-call inference |
| MCP server + Claude Code plugin | **Done in 1.3.0** | Skills/MCP are the fastest-growing pattern | Real scans spend the user's keys: tools default to demo without keys and say so |
| **AI Recommendation Index** for open-source categories | Next (1.4.0) | No such public leaderboard exists | Methodology criticism; ranking third-party projects needs care |
| `promptbeacon init` (writes the weekly workflow and badge snippet) | Next (1.4.0) | Reduce setup from minutes to one command | Low |

### The AI Recommendation Index (launch asset for 1.4.0)

A public, monthly, reproducible index of which open-source projects AI assistants
recommend in about 30 developer categories ("python http client", "python web framework",
"javascript test runner", "vector database", "static site generator", ...).

- **How:** a scheduled workflow in a separate repository runs pinned protocols (fixed
  prompts, providers and runs), commits JSON snapshots, and publishes a static page plus
  a card per category. Methodology page with the measurement tier, prompt set and
  confidence intervals.
- **Hook for maintainers:** "#2 of 9 in python http clients" badge, linking to the index
  and to `promptbeacon scan --repo` for their own project.
- **Cost (base model, 10 prompts, 3 runs, 4 models, 30 categories):** about 3,600 answers.
  At litellm list prices and about 40 input / 500 output tokens per answer: gpt-4o-mini
  $0.0031, claude-haiku-4-5 $0.025 and sonar $0.0054 per 10-prompt scan, so roughly
  **$3–4 per monthly run** (Gemini and Cohere defaults are missing from litellm's current
  price map; see open questions). Web-grounded runs add search fees (Anthropic $10 per
  1,000 searches; OpenAI's price map lists $0.025 per search for gpt-4o-mini) and larger
  inputs: plan on **$30–60 per monthly grounded run**.
- **Risks:** accusations of bias (publish everything, including raw answers); projects
  objecting to their ranking (rank by measured mention rate only, no editorial
  judgement); cost creep (pin runs, keep base-model as the default tier).

### Cost per scan (for docs and the MCP tool descriptions)

| Scan | gpt-4o-mini | claude-haiku-4-5 | sonar |
|---|---|---|---|
| 10 prompts, base model | ≈ $0.003 | ≈ $0.025 | ≈ $0.005 |
| + stability ×5 | ≈ $0.015 | ≈ $0.13 | ≈ $0.03 |
| + category inference | + < $0.001 | + < $0.001 | + < $0.001 |
| 10 prompts, grounded | tokens + ≈ $0.25 search | tokens + $0.01/search | included in sonar request fees |

Assumes about 40 input and 500 output tokens per answer; real answers vary.

## 6. Version plan

- **1.3.0 (this branch):** the first-result fixes; badges, cards and endpoint JSON; Action
  outputs, job summary and PR comment; `promptbeacon ci`; project scans; MCP server and
  plugin; docs.
- **1.4.0:** AI Recommendation Index (separate repository + site); `promptbeacon init`;
  "rank in category" badge variant; trend sparkline on cards from history; crates.io and
  Hugging Face sources; scan cost budget (`--max-cost`).
- **1.5.0:** multi-language prompt templates; Slack/webhook alerts on drops; optional
  hosted endpoint for the badge JSON only if users ask (keep local-first).

## 7. Metrics to watch

| Metric | How to measure | 90-day target |
|---|---|---|
| PyPI downloads | pypistats weekly | sustained > 300/week |
| GitHub stars | API, weekly | 150 |
| Badge adoption | GitHub code search for `.promptbeacon/badge.json` / `promptbeacon-badge.svg` | 25 public repos |
| Action adoption | "Used by" / code search for `yotambraun/promptbeacon@v1` | 15 workflows |
| Plugin/MCP usage | `uvx` installs show up in PyPI downloads; issues mentioning MCP | qualitative |
| First-run quality | issues tagged "first run" or "wrong result" | trending to zero |
| Index reach (after 1.4.0) | page views, inbound links, badge embeds | 10 maintainers embed the rank badge |

## 8. Repository housekeeping (maintainer action)

- **Topics:** add `ai-visibility`, `generative-engine-optimization`, `geo`, `aeo`,
  `answer-engine-optimization`, `llm-seo`, `share-of-voice`, `mcp-server`,
  `claude-code-plugin`, `github-action`, `pytest-plugin`, `brand-monitoring`; keep `llm`,
  `cli`, `python`, `monitoring`; drop `data-analysis`, `sentiment-analysis`,
  `prompt-engineering`, `ai-assistant` (GitHub allows 20 topics).
- **Description:** "Does AI recommend your product? Measure, track and CI-test your
  visibility in ChatGPT, Claude and Gemini answers, for brands and open-source projects."
- **Homepage:** `https://yotambraun.github.io/promptbeacon/` (currently the 0.1.0 PyPI page).
- **Social preview:** upload `assets/card-light.png` (1200×630) as the repository social
  image.

## 9. Open questions

1. Default Google and Cohere models (`gemini-2.0-flash`, `command-r`) are no longer in
   litellm's current price map, which suggests they are retired or renamed. Confirm with a
   live call and update the defaults (for example `gemini-2.5-flash`).
2. Should a demo badge be allowed at all in a README? 1.3.0 allows it but labels it.
3. Index governance: who can request a category, and how are disputes handled?
4. Which name should the plugin marketplace use once more plugins exist?
