---
name: ai-visibility-review
description: Run a full, evidence-based review of whether AI assistants (ChatGPT, Claude, Gemini, local models) recommend a product, library or open-source project, using the PromptBeacon MCP tools - cost check, one scan, competitor comparison, the answers behind the numbers, cited sources, history and significance, recommendations - and end with a summary and next actions. Use when someone asks for an AI visibility review, audit or report, wants to know why AI doesn't recommend their project and what to do about it, or wants to track whether their AI visibility is changing.
---

# AI visibility review

PromptBeacon measures; you reason. Use its MCP tools to collect the numbers,
then explain what they mean for this project. Every number you report must come
from a tool result. Scans with provider keys cost the user money: price them
first and ask before spending.

## 1. Subject, category, competitors

- An open-source project or package: use a ref such as `github:owner/name`,
  `pypi:package`, `npm:package`, `crates:name` or `hf:owner/name`. For the
  repository you are working in, `init_preview` (free, reads local files) shows
  the detected name, a category guess with its basis, and competitor guesses.
- Anything else: the brand name.
- The category is what people would ask an AI about ("python http client",
  "crm software"). Confirm it with the user if you guessed it. Ask for two to
  four competitors if you don't know them; they make share of voice and rank
  meaningful.

## 2. Mode

Call `providers`.

- `default_mode: "demo"`: no key is configured. Tell the user the review will
  use keyless demo data (canned, labelled, free, not a measurement), run it in
  demo mode to show what a real review contains, and explain how to get a real
  one: a provider key in the client's MCP configuration, or a free local model
  (`models: {"litellm": "ollama/llama3.2"}` with Ollama running).
- `"live"`: real scans, billed to the user's keys. Note which models will
  answer (`models`) unless the user asked for specific ones.

## 3. Price it, then ask

Call `estimate` with the same subject, category, competitors and models you will
scan with, and a cap: `max_cost` from the user, or 0.05 (US dollars) by default.
Tell the user the estimate (`summary`) and the cap, and ask before scanning.
Skip the question only when the user already approved a budget, the estimate is
$0 (demo or local models), or they said not to ask. If it is above the cap,
offer fewer prompts (`prompts: 5`), fewer providers, or a cheaper model.

## 4. Scan once

Call `project_scan` (projects) or `scan` (anything else) with the category,
competitors, models, `max_cost`, and `save_report: ".promptbeacon/report.json"`.
Everything below reads that file and costs nothing.

- `partial: true` means the cap stopped the scan early: the numbers cover only
  `budget.completed_answers` of `budget.planned_answers` answers. Say so.
- A `warning` about generic prompts means no category was used: fix the
  category and scan again before drawing conclusions.
- For `project_scan`, show the guessed category and competitors and their
  basis, and offer to correct them.

## 5. Compare

Call `compare` with `report_path`. Report the rank, the share of voice, and how
many answers mentioned each brand ("6 of 10 answers").

## 6. Evidence

Call `answers` with `report_path` (free) to see the answers behind the numbers:
`missing: "<subject>"` lists the answers that left the subject out and which
brands they named instead; `mentions: "<subject>"` shows how it was named, its
position and list rank. Quote one or two short excerpts, with the prompt and
model, when you explain a result. Page with `offset` when `next_offset` is set.

## 7. Sources (optional, costs more)

Which sites AI answers cite shapes what they recommend. `sources` runs a
web-grounded scan, which costs more than a plain one: call `estimate` with
`grounded: true` and ask first. Report the most-cited domains and which ones
cite the subject. In demo mode the domains are illustrative only.

## 8. History and significance

Call `history` with the brand name (free). With fewer than two saved scans,
say there is no trend yet and that each real scan is saved. Otherwise report
`trend_direction`, `latest_change` and `significance`. The significance check
is an effect-size test on the earlier against the later scans (Cohen's d of 0.5
or more counts as significant), not a p-value, and scans with different models,
categories or measurement tiers are not comparable: say so when it applies.
Under the Claude Code plugin the history is separate from the CLI's; pass
`storage: "~/.promptbeacon/data.db"` to read the CLI history.

## 9. Recommendations

Call `recommendations` with `report_path`. They are rule-based, derived from the
scan's answers. Offer `smart: true` (an LLM writes them from the same data; one
more billed request, so ask) only in live mode and only if the user wants more.

## 10. Summary

Write a short report:

- **Result:** visibility score, share of voice, rank, presence ("mentioned in 6
  of 10 answers"), and the competitor table.
- **How it was measured:** `measurement_tier` (`demo`, `base_model`: the
  model's training memory, or `api_grounded`: provider web search), the models
  that answered, the number of prompts, the cost, and whether it was partial.
- **What the evidence supports, and what it doesn't:** ten prompts is a small
  sample; one scan is one snapshot; demo data supports nothing.
- **Next actions,** each tied to evidence above: the recommendations; sites
  from `sources` that cite competitors but not the subject; tracking the
  number weekly (`init_preview` shows the workflow and the command that writes
  it, for the user to run); a README badge (`share_assets` with `report_path`).

Never present demo data as findings, never invent or round numbers into
claims the tools did not return, and never spend beyond what the user approved.
