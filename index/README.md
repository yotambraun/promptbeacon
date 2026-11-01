# AI Recommendation Index

**Status: built, not launched.** No live run has been made and no ranking has been
published. Everything under [`demo/`](demo/) is canned demo data with placeholder
project names.

A monthly, reproducible index of which open-source projects AI assistants recommend,
in 30 developer categories ("python http client", "vector database", "static site
generator", ...). Projects are ranked by **measured mention rate only**: no editorial
judgement, no pre-ranking, every raw answer published.

## Why a folder here, and not a `promptbeacon index` command

The Index is an operated dataset (its own protocols, schedule, raw answers and site),
not something PromptBeacon users run against their own project. Keeping it out of the
`promptbeacon` package keeps the wheel small and the CLI focused on "measure my
project", and lets the folder move to its own repository later without changes. It
uses only PromptBeacon's public pieces: the LiteLLM and demo clients, the cost
estimator and budget (`--max-cost`), the statistics module (Wilson intervals) and the
rank badge renderer.

## Layout

| Path | What it is |
| --- | --- |
| `categories/<id>.json` | One pinned protocol per category: the category, candidate projects (alphabetical, with the spellings that count as a mention), 10 fixed prompts, the providers and models, runs, temperature and max tokens |
| `pbindex/` | The generator: `validate`, `estimate`, `run`, `build` |
| `data/<date>/<id>.json` | A JSON snapshot per category per run (written by live runs; none yet) |
| `data/<date>/raw/<id>.jsonl` | Every raw answer, with the projects it mentions |
| `demo/html/` | The site built from a demo run (3 categories, placeholder names) |
| `../.github/workflows/index-monthly.yml` | The monthly workflow, **disabled** (see below) |

## Use it

From this directory, with PromptBeacon installed (`pip install -e ..` from a clone):

```bash
python -m pbindex validate                    # check every protocol
python -m pbindex estimate                    # cost of a run; sends nothing
python -m pbindex run --demo                  # offline mock answers, $0, into demo/data/
python -m pbindex build --demo                # demo/data/ -> demo/html/
python -m pbindex run --max-cost 5            # live: needs OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY
python -m pbindex build --base-url https://<where the site is hosted>/
```

A live run refuses to start without `--max-cost` or when the estimate is above it, and
stops issuing requests once the cap is reached (that category's snapshot is then marked
partial). `--categories a,b` runs a subset.

## How a run works

1. For each category: every prompt × every model × `runs` (3), at the pinned
   temperature and token limit. 90 answers per category, 2,700 per full run.
2. Each answer is matched against the candidates: a whole-word match of the name or one
   of its listed spellings (case-sensitive for names that are also common words).
3. Mention rate = answers mentioning the project ÷ successful answers, with a 95% Wilson
   interval. Rank = 1 + projects with a higher count; ties share a rank; overlapping
   intervals are flagged.
4. The site shows an overview, one page per category (ranking table with intervals and
   per-model rates, the prompts, links to the snapshot and raw answers), a methodology
   page, and a rank badge per project ("AI rank: #2 of 7 · python http clients", as
   SVG and shields.io endpoint JSON).

## Estimated cost

From PromptBeacon's estimator (LiteLLM's bundled price map, about 500 output tokens per
answer; checked 2026-11-01):

| Model | Answers per run | Estimate | At most (1024 tokens each) |
| --- | ---: | ---: | ---: |
| OpenAI gpt-6-luna | 900 | $0.23 | $0.46 |
| Anthropic claude-haiku-5-5 | 900 | $0.23 | $0.46 |
| Google gemini-3.5-flash-lite | 900 | $1.13 | $2.31 |
| **Monthly run (30 categories)** | **2,700** | **about $1.59** | **$3.24** |

A web-grounded tier (provider web search) would cost about $1.12 per category, about
$34 per run, mostly search fees; it is not part of the protocols. Re-check with
`python -m pbindex estimate` before launch: prices and default models change.

## Candidates

Each category lists 4 to 9 widely used open-source projects, chosen by the maintainer
from the projects most often named in each ecosystem's documentation and comparisons,
and listed alphabetically. The list decides which names are counted, never their
order. Additions and disputes go through public GitHub issues with the `index` label;
changes take effect in the next run and published snapshots are never edited.

## Launch checklist (owner)

1. Re-run `python -m pbindex estimate` and review the candidate lists.
2. Add the repository secrets `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` and
   `GEMINI_API_KEY` (or move the Index to its own repository first).
3. Set the repository variable `PB_INDEX_ENABLED` to `true`, run the workflow once by
   hand (`gh workflow run index-monthly.yml`), and check the snapshots and site.
4. Decide where the site is hosted (see the workflow) and pass `--base-url`.
5. Uncomment the `schedule` in `.github/workflows/index-monthly.yml`.
