# Open-source projects

Does AI recommend your library? Point PromptBeacon at a GitHub repository or a
package, and it works out what to ask.

```bash
promptbeacon scan --pypi httpx --demo
promptbeacon scan --repo fastapi/fastapi
promptbeacon scan --npm express
promptbeacon scan --project pypi:httpx          # generic kind:ref form
```

The same options work for `badge` and `card`. In the GitHub Action, pass the project
name as `brand` and its `category` (see [CI & examples](examples.md)).

## What happens

1. **Metadata.** PromptBeacon reads public metadata: the GitHub repository (description,
   topics, language, README), the PyPI JSON API (summary, keywords, classifiers, long
   description), or the npm registry (description, keywords, repository).
2. **Brand.** The project name becomes the brand; the full name (for example
   `fastapi/fastapi` or `@scope/pkg`) is added as an alias.
3. **Category.** A buyer-style category is guessed offline from the description and
   topics, prefixed with the language: `httpx` → "python http client", `express` →
   "javascript web framework", `fastapi` → "python api framework".
4. **Competitors.** Candidates come from how the README describes itself ("inspired by
   Flask", "a requests-compatible API", "alternative to X"). If none are found, the scan
   still runs on the category; add `--competitor` to compare share of voice.
5. **Prompts.** Developer-oriented questions ("Which python http client should I use for
   a new project?").

The CLI prints each guess with its basis and confidence, for example:

```text
Project: httpx (pypi: httpx) — The next generation HTTP client.
Category: 'python http client' (guessed from description, high confidence). Override with --category.
Competitors: requests (README mentions). Override with --competitor.
```

## Overriding the guesses

Explicit options always win:

```bash
promptbeacon scan --pypi httpx -t "async http library" -c requests -c aiohttp
```

With a provider key, `--infer-category` asks one model to name the category (and to
suggest competitors if none were found). It is one extra, logged call; the offline guess
is the fallback, and it is never used in demo mode. For trend tracking, pin the category
with `--category` so every run asks the same questions.

## GitHub limits and caching

The GitHub API allows 60 unauthenticated requests per hour, and a repository scan uses
two (repository and README). Set `GITHUB_TOKEN` (or `GH_TOKEN`) to raise the limit; in
GitHub Actions the built-in token works. Rate limits, missing projects and network errors
produce a clear message and exit code 1.

Successful responses are cached for a day under `$PROMPTBEACON_HOME/cache/projects`
(default `~/.promptbeacon`).

## In Python

```python
from promptbeacon import Beacon

beacon = Beacon.from_project("pypi:httpx")
print(beacon.project.category)  # CategoryGuess(category='python http client', ...)
report = beacon.demo().scan()
```

Lower-level pieces live in `promptbeacon.projects`:

```python
from promptbeacon.projects import fetch_project, guess_category, guess_competitors

meta = fetch_project("github:fastapi/fastapi")
print(guess_category(meta).category, guess_competitors(meta))
```

## Adding a source

Each source is one small class. Subclass `MetadataSource`, implement `fetch`, and
register it; the CLI (`--project kind:ref`), `Beacon.from_project` and the MCP server
pick it up.

```python
from promptbeacon.projects import MetadataSource, ProjectMetadata, register_source


@register_source
class CratesSource(MetadataSource):
    kind = "crates"
    label = "crates.io"
    example = "serde"

    def fetch(self, ref: str) -> ProjectMetadata:
        resp = self._get(f"https://crates.io/api/v1/crates/{ref}")
        if resp.status != 200:
            raise self._error(resp, f"crate {ref}")
        crate = resp.json()["crate"]
        return ProjectMetadata(
            source=self.kind,
            ref=ref,
            name=crate["name"],
            description=crate.get("description") or "",
            keywords=crate.get("keywords") or [],
            language="Rust",
        )
```

`self._get` adds the User-Agent and the cache; `self._error` turns HTTP errors into
clear messages.

!!! note "Heuristics, shown openly"
    The offline guesses are simple and transparent rather than clever. They work well
    for English descriptions and topic lists; for other languages they fall back to the
    topics. Check the printed guess before relying on a number.
