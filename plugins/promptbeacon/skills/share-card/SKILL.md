---
name: share-card
description: Create a README badge (SVG and shields.io endpoint JSON) and a 1200x630 share card showing how often AI assistants recommend a product or open-source project versus its competitors. Use when someone wants an "AI visibility" badge for their README or an image to share their results.
argument-hint: "[brand or github:owner/name | pypi:package | npm:package] [category]"
---

# Badge and share card

1. Call `providers`. If it reports demo mode, explain that the badge and card
   will be labelled as demo data, and that a real measurement needs a provider
   API key.
2. Confirm the subject, its category and (if known) competitors, as in the
   `ai-visibility` skill.
3. Call `share_assets` with `brand` or `project`, `category`, `competitors`,
   and `output_dir` (default `.promptbeacon`). Set `png: true` if the user
   wants to post the card on social networks (they do not accept SVG).
4. Show the user the files that were written and the README snippets from the
   result: `readme_badge`, and `readme_card`, which uses `<picture>` so GitHub
   shows the dark card in dark mode.
5. If the user wants the badge to stay current, offer the `visibility-ci`
   skill to add a weekly GitHub workflow that refreshes it.

$ARGUMENTS
