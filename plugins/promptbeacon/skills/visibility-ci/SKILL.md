---
name: visibility-ci
description: Add a GitHub Actions workflow that measures AI visibility with PromptBeacon, either weekly (refreshing a README badge and share card) or on pull requests (a check plus one sticky PR comment). Use when someone wants to track or gate how AI assistants recommend their product in CI.
disable-model-invocation: true
argument-hint: "[weekly | pr]"
---

# AI visibility in CI

Set up the `yotambraun/promptbeacon@v1` GitHub Action in the user's repository.

1. Ask which workflow they want:
   - **weekly**: scheduled scan that commits `.promptbeacon/badge.svg`,
     `.promptbeacon/badge.json` and `.promptbeacon/card.svg`. Needs
     `permissions: contents: write`.
   - **pr**: a check on pull requests with one sticky comment that is updated
     in place. Needs `permissions: pull-requests: write`; on forks the comment
     step only warns.
2. Collect `brand`, `category` (required for a meaningful result) and
   `competitors` (one per line). Use the project's own name and category if
   this is the user's repository.
3. Write `.github/workflows/ai-visibility.yml` based on the templates at
   https://github.com/yotambraun/promptbeacon/tree/main/examples/workflows
   (`ai-visibility-weekly.yml` or `ai-visibility-pr.yml`).
4. Tell the user to add an `OPENAI_API_KEY` (or another provider key) as a
   repository secret, and that each run is billed to that key. Mention
   `demo: "true"` for a free dry run.
5. For the badge, show both options: the committed SVG
   (`![AI visibility](.promptbeacon/badge.svg)`) or shields.io via
   `https://img.shields.io/endpoint?url=<url-encoded raw URL of badge.json>`.

$ARGUMENTS
