---
name: visibility-ci
description: Add a GitHub Actions workflow that measures AI visibility with PromptBeacon, either weekly (refreshing a README badge and share card) or on pull requests (a check plus one sticky PR comment). Use when someone wants to track or gate how AI assistants recommend their product in CI.
disable-model-invocation: true
argument-hint: "[weekly | pr]"
---

# AI visibility in CI

Set up the `yotambraun/promptbeacon@v1` GitHub Action in the user's repository.

For the **weekly** workflow, prefer the CLI, which detects the project and
writes a filled-in workflow after showing it:

- Run `promptbeacon init --dry-run --format json` (in the repository root) and
  show the user the proposed category with its basis, the competitors, the
  estimated cost per run and the workflow. Confirm the category and
  competitors with the user.
- Then write it with `promptbeacon init --yes -t "<category>" -c <competitor>
  ...` (add `--protocol` to pin the prompts and models). It never replaces a
  changed file unless `--force` is added; do not add `--force` unless the user
  asks after seeing the diff.
- Relay the `next_steps` (the `gh secret set` command, committing, running the
  workflow once) and the README badge snippet from the result.

If the CLI is not available, or for the **pr** workflow, do it by hand:

1. Ask which workflow they want:
   - **weekly**: scheduled scan that commits `.promptbeacon/badge.svg`,
     `.promptbeacon/badge.json` and `.promptbeacon/card.svg`. Needs
     `permissions: contents: write`.
   - **pr**: a check on pull requests with one sticky comment that is updated
     in place. Needs `permissions: pull-requests: write`; on forks the comment
     step only warns.
2. Collect `brand`, `category` (required for a meaningful result) and
   `competitors` (one per line). Use the project's own name and category if
   this is the user's repository. Set the Action's `models` input (one
   `provider=model_id` per line, e.g. `openai=gpt-6-luna`) so the tracked
   number does not move when PromptBeacon's default models change; the
   providers named there are the ones queried.
3. Write `.github/workflows/ai-visibility.yml` based on the templates at
   https://github.com/yotambraun/promptbeacon/tree/main/examples/workflows
   (`ai-visibility-weekly.yml` or `ai-visibility-pr.yml`).
4. Tell the user to add an `OPENAI_API_KEY` (or the key for the provider in
   `models`, e.g. `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`) as a repository
   secret and pass it in the step's `env`, and that each run is billed to
   that key. Mention
   `demo: "true"` for a free dry run.
5. For the badge, show both options: the committed SVG
   (`![AI visibility](.promptbeacon/badge.svg)`) or shields.io via
   `https://img.shields.io/endpoint?url=<url-encoded raw URL of badge.json>`.
6. Suggest `max-cost` (e.g. `"0.10"`) so one run cannot spend more than that,
   `trend-path: .promptbeacon/trend.json` for a score sparkline on the card,
   and, with two or more competitors, `rank-badge-path` for an
   "AI rank: #2 of 4" badge.

$ARGUMENTS
