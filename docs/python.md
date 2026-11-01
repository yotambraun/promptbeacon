# Use it from your code

Everything the CLI, the GitHub Action and the MCP server do goes through one Python
class, `Beacon`. Every example on this page runs as is, offline and for free, because it
uses the keyless demo (`.demo()`) or only prices a scan. Remove `.demo()` and set a
provider key for a real measurement. The full list of methods is in the
[API reference](api-reference.md).

## A scan

```python
from promptbeacon import Beacon

report = (
    Beacon("httpx")
    .with_category("python http client")
    .with_competitors("requests", "aiohttp")
    .demo()  # keyless and free; remove it for a real scan
    .scan()
)

sov = report.share_of_voice
print(f"measured:       {report.measurement_tier}")
print(f"score:          {report.visibility_score:.0f}/100")
print(f"share of voice: {sov.target_share:.0%} (rank {sov.target_rank})")
print(f"presence:       {sov.target_presence_rate:.0%} of answers")
```

```text
measured:       demo
score:          79/100
share of voice: 33% (rank 2)
presence:       60% of answers
```

`report.measurement_tier` says how the numbers were measured: `demo`, `base_model` (the
model's training memory) or `api_grounded` (with `.with_grounding()`, the provider's
web search). `report.recommendations` and `report.explanations` hold the rule-based
advice and the reasons behind the score.

For an open-source project, start from its metadata instead:
`Beacon.from_project("pypi:httpx")` (also `github:`, `npm:`, `crates:` and `hf:`) guesses
the category and competitors; `beacon.project` shows the guesses and their basis.

## Models and cost

Choose a model per provider; the providers you name are the ones queried. Before a real
scan, price it: `estimate_cost()` uses LiteLLM's bundled price map and sends nothing.
`with_max_cost()` caps a scan in US dollars.

```python
from promptbeacon import Beacon

beacon = (
    Beacon("httpx")
    .with_category("python http client")
    .with_competitors("requests", "aiohttp")
    .with_models({"anthropic": "claude-sonnet-5-5", "openai": "gpt-6-luna"})
    .with_max_cost(0.05)
)

estimate = beacon.estimate_cost()  # prices the scan; sends nothing
print(estimate.summary())
for line in estimate.lines:
    print(f"  {line.provider}/{line.model}: {line.requests} requests, ${line.usd:.4f}")
```

```text
about $0.053 (at most $0.108) for 20 answers
  anthropic/claude-sonnet-5-5: 10 requests, $0.0504
  openai/gpt-6-luna: 10 requests, $0.0025
```

This estimate is above the $0.05 cap, so `beacon.scan()` would raise
`BudgetExceededError` without sending a request. Lower it with
`.with_prompt_count(5)`, one provider, or a cheaper model. When a scan reaches the cap
part-way, `report.partial` is `True` and `report.budget` has the counts. A local model
costs nothing: `.with_models(litellm="ollama/llama3.2")`. See
[Models & local LLMs](models.md).

## Async

`scan_async()` is the same scan as a coroutine, so several scans can run together:

```python
import asyncio

from promptbeacon import Beacon


async def scan_all(projects: list[str]) -> None:
    beacons = [
        Beacon(name)
        .with_category("python http client")
        .with_competitors(*[other for other in projects if other != name])
        .demo()
        for name in projects
    ]
    reports = await asyncio.gather(*(b.scan_async() for b in beacons))
    for report in reports:
        print(f"{report.brand:10} {report.visibility_score:5.1f}")


asyncio.run(scan_all(["httpx", "requests", "aiohttp"]))
```

```text
httpx       79.0
requests    78.6
aiohttp     78.4
```

(Demo data: these numbers describe canned answers, not the projects.)

## JSON

A report is a Pydantic model: write it with `to_json()`, read it back with
`Report.model_validate_json()`. `report_summary()` gives the compact, JSON-safe view the
MCP tools return. The CLI's `badge`, `card` and `ci` commands take the same file with
`--report`.

```python
import json
from pathlib import Path

from promptbeacon import Beacon, Report, to_json
from promptbeacon.share.summary import report_summary

report = Beacon("httpx").with_category("python http client").demo().scan()

Path("report.json").write_text(to_json(report), encoding="utf-8")  # the full report
summary = report_summary(report)  # compact, JSON-safe dict
print(
    json.dumps(
        {k: summary[k] for k in ("brand", "visibility_score", "measurement_tier")}
    )
)

again = Report.model_validate_json(Path("report.json").read_text(encoding="utf-8"))
print(again.visibility_score == report.visibility_score)
```

```text
{"brand": "httpx", "visibility_score": 82.3, "measurement_tier": "demo"}
True
```

## History

`with_storage(path)` saves every scan to a local DuckDB file (demo scans too, unlike the
CLI, which saves only real ones). Read it back with `get_history()` and
`compare_with_previous()`:

```python
from promptbeacon import Beacon

with (
    Beacon("httpx")
    .with_category("python http client")
    .with_storage("visibility.db")
    .demo() as beacon
):
    beacon.scan()
    beacon.scan()
    history = beacon.get_history(days=30)
    change = beacon.compare_with_previous()

print(f"{len(history.data_points)} scans, scores {history.visibility_trend}")
print(f"latest vs previous: {change.score_change:+.1f} ({change.change_direction})")
```

```text
2 scans, scores [82.3, 82.3]
latest vs previous: +0.0 (stable)
```

The CLI's history lives in `~/.promptbeacon/data.db`; `Beacon(...).with_storage()` can
read it. See [Storage & history](storage.md) for the schema and SQL examples.

## A CI script

A script for any CI system: it scans (in demo mode when no key is set), saves the
report, and fails the build below your thresholds.

```python
"""Fail the build when AI visibility drops. Demo mode when no key is set."""

import os
import sys
from pathlib import Path

from promptbeacon import Beacon, VisibilityAssertionError, to_json

beacon = (
    Beacon("httpx")
    .with_category("python http client")
    .with_competitors("requests", "aiohttp")
    .with_models({"openai": "gpt-6-luna"})  # pin the model to keep the trend comparable
    .with_max_cost(0.05)
)
if not os.environ.get("OPENAI_API_KEY"):
    beacon = beacon.demo()

report = beacon.scan()
Path("report.json").write_text(to_json(report), encoding="utf-8")
print(
    f"{report.measurement_tier}: score {report.visibility_score:.0f}, "
    f"share of voice {report.share_of_voice.target_share:.0%}"
)

try:
    report.assert_visibility(min_score=50, min_share_of_voice=0.3)
except VisibilityAssertionError as error:
    print(f"AI visibility check failed: {error}")
    sys.exit(1)
```

```text
demo: score 79, share of voice 33%
```

Then `promptbeacon ci --report report.json` writes a Markdown job summary and CI outputs
from the same file. On GitHub, the [Action](examples.md) does all of this in one step;
in a test suite, use the [pytest marker](examples.md).
