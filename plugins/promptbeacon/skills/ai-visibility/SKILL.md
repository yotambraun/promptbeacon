---
name: ai-visibility
description: Check whether AI assistants (ChatGPT, Claude, Gemini and others) mention and recommend a product, brand, or open-source project, and how it compares with competitors. Use when someone asks "does AI recommend my product/library?", wants their share of voice in AI answers, or wants to know which sites AI cites for their category.
when_to_use: Trigger phrases include "does ChatGPT recommend", "AI visibility", "share of voice", "is my library recommended by AI", "GEO", "AEO", "which sites does AI cite".
argument-hint: "[brand or github:owner/name | pypi:package | npm:package] [category]"
---

# AI visibility check

Use the PromptBeacon MCP tools to measure how often AI answers mention the
subject, compared with its competitors.

1. Call the `providers` tool first. If `default_mode` is `demo`, tell the user
   that no provider key is configured, so results will be keyless demo data
   (canned, clearly labelled, and not a measurement). Real scans use their own
   API keys and are billed to them.
2. Work out what to scan:
   - An open-source project or package: use `project_scan` with
     `github:owner/name`, `pypi:package` or `npm:package`. If the user means
     the current repository, read its name and description from
     `pyproject.toml`, `package.json` or the git remote first.
   - Anything else: use `scan` with the brand name.
3. Always pass a `category` phrased the way a buyer would ask ("python http
   client", "running shoes"). If you are unsure, ask the user, or let
   `project_scan` guess it and show the user the guess and its basis.
   Add `competitors` when the user knows them.
4. Report the result plainly:
   - visibility score (0-100), share of voice and rank, and how many answers
     mentioned the subject (for example "8 of 10 answers");
   - a short table of brands and how often each was mentioned;
   - `measurement_tier`: `demo` (canned data), `base_model` (the model's
     training memory, no web search) or `api_grounded` (provider web search);
   - the estimated cost, if any.
5. Suggest one concrete next step: re-run with competitors, run `sources`
   with `grounded: true` to see which sites shape these answers, or create a
   badge and share card with the `share-card` skill.

Do not present demo results as real findings. Do not invent numbers that the
tools did not return.

$ARGUMENTS
