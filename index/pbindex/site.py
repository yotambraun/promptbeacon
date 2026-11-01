"""Render the Index as a static site (HTML + JSON + SVG badges, no scripts)."""

from __future__ import annotations

import html
import json
import re
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.parse import quote

from pbindex.protocol import IndexProtocol
from pbindex.runner import DEMO_NOTE, estimate
from promptbeacon.budget import format_usd
from promptbeacon.share.badge import rank_badge_parts, rank_endpoint, render_badge

REPO = "https://github.com/yotambraun/promptbeacon"
ISSUES = f"{REPO}/issues/new"
PROVIDER_NAMES = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google": "Google",
    "mistral": "Mistral",
    "cohere": "Cohere",
    "perplexity": "Perplexity",
    "litellm": "LiteLLM",
}

CSS = """
:root{--bg:#fff;--fg:#0f172a;--muted:#64748b;--line:#e2e8f0;--soft:#f1f5f9;
--accent:#4f46e5;--bar:#c7d2fe;--warn-bg:#fef3c7;--warn-fg:#78350f;--warn-line:#f59e0b}
@media (prefers-color-scheme:dark){:root{--bg:#0b1020;--fg:#f8fafc;--muted:#94a3b8;
--line:#1e293b;--soft:#111a2e;--accent:#a5b4fc;--bar:#3730a3;--warn-bg:#3a2a0a;
--warn-fg:#fde68a;--warn-line:#b45309}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
main{max-width:1040px;margin:0 auto;padding:24px 16px 64px}
a{color:var(--accent)}
header.top{display:flex;gap:16px;align-items:baseline;flex-wrap:wrap;
border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:24px}
header.top a{text-decoration:none;font-weight:600}
h1{font-size:1.9rem;line-height:1.2;margin:.2em 0 .4em}
h2{font-size:1.25rem;margin-top:2em}
.muted{color:var(--muted)}
.banner{background:var(--warn-bg);color:var(--warn-fg);border:1px solid var(--warn-line);
border-radius:10px;padding:12px 16px;margin:0 0 24px;font-weight:600}
.table{width:100%;overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:.95rem}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:.8rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.ci{position:relative;height:12px;min-width:140px;background:var(--soft);border-radius:6px}
.ci .range{position:absolute;top:0;height:12px;background:var(--bar);border-radius:6px}
.ci .point{position:absolute;top:-2px;width:3px;height:16px;background:var(--accent);
border-radius:2px}
code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.85em}
pre{background:var(--soft);padding:10px 12px;border-radius:8px;overflow-x:auto}
.pill{display:inline-block;padding:1px 8px;border-radius:99px;background:var(--soft);
font-size:.8rem;color:var(--muted)}
footer{margin-top:48px;border-top:1px solid var(--line);padding-top:12px;font-size:.85rem}
"""


def _e(text: object) -> str:
    return html.escape(str(text), quote=True)


def _pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "project"


def _page(title: str, body: str, *, demo: bool, depth: int = 0) -> str:
    up = "../" * depth
    robots = '<meta name="robots" content="noindex">' if demo else ""
    banner = f'<div class="banner">{_e(DEMO_NOTE)}</div>' if demo else ""
    prefix = "[DEMO] " if demo else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{robots}
<title>{_e(prefix + title)}</title>
<style>{CSS}</style>
</head>
<body>
<main>
<header class="top">
<a href="{up}index.html">AI Recommendation Index</a>
<a href="{up}methodology.html">Methodology</a>
<a href="{REPO}">PromptBeacon</a>
</header>
{banner}
{body}
<footer class="muted">Measured with <a href="{REPO}">PromptBeacon</a>. Raw answers
and JSON snapshots are published with every page. Rankings are by measured mention
rate only.</footer>
</main>
</body>
</html>
"""


def _models_text(models: dict[str, str]) -> str:
    return ", ".join(f"{PROVIDER_NAMES.get(p, p)} {m}" for p, m in models.items())


def latest_snapshots(data_dir: Path) -> list[dict[str, Any]]:
    """The newest snapshot per category under ``data_dir/<date>/<id>.json``."""
    latest: dict[str, tuple[str, Path]] = {}
    for path in sorted(data_dir.glob("*/*.json")):
        day = path.parent.name
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
            continue
        current = latest.get(path.stem)
        if current is None or day > current[0]:
            latest[path.stem] = (day, path)
    snapshots = []
    for _cid, (_day, path) in sorted(latest.items()):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["_path"] = path
        snapshots.append(data)
    return snapshots


def _ci_bar(r: dict[str, Any]) -> str:
    low, high, rate = r["ci_low"] * 100, r["ci_high"] * 100, r["rate"] * 100
    return (
        f'<div class="ci" title="95% interval {low:.0f}% to {high:.0f}%">'
        f'<div class="range" style="left:{low:.1f}%;width:{max(high - low, 0.5):.1f}%">'
        f'</div><div class="point" style="left:calc({rate:.1f}% - 1px)"></div></div>'
    )


def _badge_url(base_url: str | None, cid: str, name: str) -> str:
    path = f"badges/{cid}/{slug(name)}.json"
    if not base_url:
        return f"&lt;SITE_URL&gt;/{path}"
    return base_url.rstrip("/") + "/" + path


def category_page(snap: dict[str, Any], base_url: str | None) -> str:
    demo = bool(snap["demo"])
    cid = snap["id"]
    providers = list(snap["models"])
    head_cells = "".join(
        f'<th class="num">{_e(PROVIDER_NAMES.get(p, p))}</th>' for p in providers
    )
    rows = []
    for r in snap["results"]:
        rank = f"{'=' if r['tied'] else ''}{r['rank']}"
        approx = (
            ' <span class="muted" title="95% interval overlaps the next project">≈</span>'
            if r["overlaps_next"]
            else ""
        )
        name = (
            f'<a href="{_e(r["url"])}">{_e(r["name"])}</a>'
            if r["url"] and r["url"] != "#"
            else _e(r["name"])
        )
        per = "".join(
            f'<td class="num">{_pct(r["by_provider"].get(p, {}).get("rate", 0.0))}</td>'
            for p in providers
        )
        rows.append(
            f"<tr><td class=num>{rank}</td><td>{name}</td>"
            f'<td class="num">{_pct(r["rate"])}{approx}</td>'
            f'<td class="num">{_pct(r["ci_low"])}–{_pct(r["ci_high"])}</td>'
            f"<td>{_ci_bar(r)}</td>{per}</tr>"
        )
    partial = (
        f'<p class="banner">Partial: the run budget was reached after '
        f"{snap['answers']} of {snap['planned_answers']} answers.</p>"
        if snap.get("partial")
        else ""
    )
    prompts = "".join(f"<li>{_e(p)}</li>" for p in snap["prompts"])
    total = len(snap["results"])
    badges = []
    for r in snap["results"]:
        url = _badge_url(base_url, cid, r["name"])
        shields = (
            "https://img.shields.io/endpoint?url=" + quote(url, safe="")
            if base_url
            else f"https://img.shields.io/endpoint?url={url}"
        )
        position = f"#{r['rank']} of {total}"
        badges.append(
            f"<li>{_e(r['name'])}: <code>{_e(position)}</code>"
            f"<pre>[![AI rank]({_e(shields)})]({_e(base_url or '<SITE_URL>')})</pre></li>"
        )
    body = f"""
<p class="muted">{_e(snap["group"])} · {_e(snap["date"])}</p>
<h1>Which {_e(snap["category"])} do AI assistants recommend?</h1>
<p>Share of {snap["answers"]} answers that mention each project, from
{len(snap["prompts"])} fixed prompts × {snap["runs"]} runs × {len(providers)} models
({_e(_models_text(snap["models"]))}). <span class="pill">tier: base model</span>
measures what the models say from training memory, without web search.</p>
{partial}
<div class="table"><table>
<thead><tr><th class="num">Rank</th><th>Project</th><th class="num">Mentioned in</th>
<th class="num">95% interval</th><th>Interval</th>{head_cells}</tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
<p class="muted">Ranked by mention rate only. "=" marks a tie; "≈" marks an interval that
overlaps the next project's, so the order between them is not statistically clear.
{snap["failed_answers"]} failed answers are excluded. Estimated cost of this category:
{_e(format_usd(snap["cost_usd"]))}.</p>
<h2>Data</h2>
<ul>
<li><a href="../data/{_e(cid)}.json">Snapshot (JSON)</a>: every number on this page,
with the protocol fingerprint <code>{_e(snap["protocol_sha256"][:12])}</code>.</li>
<li><a href="../raw/{_e(cid)}.jsonl">Raw answers (JSON Lines)</a>: every answer, with the
projects it mentions.</li>
<li><a href="{REPO}/blob/main/index/categories/{_e(cid)}.json">Protocol</a>: the pinned
prompts, candidates, models and runs.</li>
</ul>
<h2>Prompts</h2>
<ol>{prompts}</ol>
<h2>Rank badges</h2>
<p class="muted">For a project's README. The badge is regenerated with every run.</p>
<ul>{"".join(badges)}</ul>
<h2>Missing a project, or think something is wrong?</h2>
<p><a href="{ISSUES}?labels=index&amp;title={quote("Index: " + cid + ": ")}">Open an
issue</a>. See <a href="../methodology.html#requests-and-disputes">how requests and
disputes are handled</a>.</p>
"""
    return _page(
        f"{snap['category']} — AI Recommendation Index", body, demo=demo, depth=1
    )


def overview_page(snaps: Sequence[dict[str, Any]]) -> str:
    demo = any(s["demo"] for s in snaps)
    groups: dict[str, list[dict[str, Any]]] = {}
    for s in snaps:
        groups.setdefault(s["group"], []).append(s)
    sections = []
    for group in sorted(groups):
        rows = []
        for s in sorted(groups[group], key=lambda s: s["category"]):
            top = ", ".join(
                f"{_e(r['name'])} {_pct(r['rate'])}" for r in s["results"][:3]
            )
            rows.append(
                f'<tr><td><a href="categories/{_e(s["id"])}.html">{_e(s["category"])}</a></td>'
                f"<td>{top}</td><td class=num>{len(s['results'])}</td>"
                f"<td class=num>{s['answers']}</td><td class=num>{_e(s['date'])}</td></tr>"
            )
        sections.append(
            f"<h2>{_e(group)}</h2><div class=table><table><thead><tr><th>Category</th>"
            "<th>Most mentioned (share of answers)</th><th class=num>Projects</th>"
            "<th class=num>Answers</th><th class=num>Date</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>"
        )
    dates = sorted({s["date"] for s in snaps})
    when = dates[-1] if dates else "not yet run"
    body = f"""
<h1>AI Recommendation Index</h1>
<p>Which open-source projects do AI assistants recommend? For {len(snaps)} developer
categories, the same fixed questions go to the same models every month, and projects
are ranked by how often the answers mention them. Every answer is published.</p>
<p class="muted">Latest run: {_e(when)}. Read the
<a href="methodology.html">methodology</a> before quoting a number.</p>
{"".join(sections)}
"""
    return _page("AI Recommendation Index", body, demo=demo)


def methodology_page(
    protocols: Sequence[IndexProtocol], demo: bool, base_url: str | None
) -> str:
    priced = estimate(protocols)
    total = sum(e.total_usd for _, e in priced)
    upper = sum(e.upper_usd for _, e in priced)
    answers = sum(p.planned_answers for p in protocols)
    models = protocols[0].providers if protocols else {}
    runs = protocols[0].runs if protocols else 0
    templates = protocols[0].prompts if protocols else []
    category = protocols[0].category if protocols else ""
    shown = "".join(
        f"<li>{_e(p.replace(category, '{category}'))}</li>" for p in templates
    )
    cats = "".join(
        f"<li><b>{_e(p.category)}</b>: "
        + ", ".join(_e(c.name) for c in p.candidates)
        + "</li>"
        for p in protocols
    )
    lines: dict[str, float] = {}
    for _, est in priced:
        for line in est.lines:
            key = f"{PROVIDER_NAMES.get(line.provider, line.provider)} {line.model}"
            lines[key] = lines.get(key, 0.0) + line.usd
    cost_rows = "".join(
        f"<tr><td>{_e(k)}</td><td class=num>{_e(format_usd(v))}</td></tr>"
        for k, v in lines.items()
    )
    body = f"""
<h1>Methodology</h1>
<p>The Index measures one thing: <b>how often AI assistants mention a project when
asked for recommendations in its category</b>. It does not judge quality, popularity or
anything else, and nobody can pay to change it.</p>

<h2>What is asked</h2>
<p>Each category has a pinned protocol (a JSON file in the repository) with
{len(templates)} fixed prompts. They are the same for every category, with the
category name filled in:</p>
<ol>{shown}</ol>
<p>Each prompt is sent {runs} times to each model, so a category gets
{len(templates) * runs * len(models)} answers per run.</p>

<h2>Models and tier</h2>
<p>Models: {_e(_models_text(models))}, at temperature 0.7 (not sent to Claude models,
which use their default) and up to 1024 output tokens. The measurement tier is
<b>base model</b>: plain API answers from the model's training memory, without web
search. It approximates, but does not equal, what people see in ChatGPT, Claude or
Gemini apps, which add web search and other orchestration. Model versions are pinned
per protocol and change only with a new protocol version, so runs stay comparable.</p>

<h2>Candidates</h2>
<p>Each category lists 4 to 9 widely used open-source projects, in alphabetical order.
The list decides which names are counted, not their order. It was compiled by the
maintainer from the projects most often named in each ecosystem's documentation and
comparisons; additions are welcome (see below). An answer can mention other projects;
they are not counted.</p>
<ul>{cats}</ul>

<h2>Counting a mention</h2>
<p>An answer mentions a project when the project's name (or one of the listed
spellings, such as "Postgres" for PostgreSQL) appears as a whole word. Names that are
also ordinary words are matched case-sensitively or by specific spellings (for
example "Requests" or <code>requests</code> library, not "HTTP requests"). Each answer
counts a project at most once, wherever it appears in the answer.</p>

<h2>How ranking works</h2>
<ul>
<li><b>Mention rate</b> = answers that mention the project ÷ successful answers.</li>
<li><b>Rank</b> = 1 + the number of projects with a higher count. Equal counts share a
rank (shown with "=").</li>
<li><b>95% interval</b>: a Wilson score interval for the mention rate. When two
projects' intervals overlap ("≈"), the order between them is not statistically clear.
The interval treats answers as independent; repeated answers to the same prompt are
correlated, so the real uncertainty is somewhat larger.</li>
<li>Failed requests are excluded and counted on each page. A run stopped by its budget
is marked partial.</li>
</ul>

<h2>Limitations</h2>
<ul>
<li>A base model's answers reflect training data with a cut-off date; recent projects
can be under-mentioned.</li>
<li>Three models and ten prompts are a sample, not every question developers ask.
Answers vary between runs, which is why each prompt runs {runs} times and intervals
are shown.</li>
<li>Name matching is literal. A project with a common-word name may be under- or
over-counted; the matching rules are in each protocol and the raw answers are
published so anyone can check.</li>
<li>A mention is not a recommendation: an answer may mention a project to advise
against it.</li>
</ul>

<h2 id="requests-and-disputes">Requests and disputes</h2>
<p>Everything happens in public GitHub issues with the <code>index</code> label:</p>
<ul>
<li><b>Add a project or a category</b>: <a href="{ISSUES}?labels=index&amp;title=Index%3A+add+">open an
issue</a> with the category, the project and its repository. A project is added when
it is open source and is a real alternative in the category; additions take effect in
the next run (rankings are never edited by hand).</li>
<li><b>Dispute a result</b>: <a href="{ISSUES}?labels=index&amp;title=Index%3A+dispute+">open an
issue</a> pointing at the raw answers. Matching errors are fixed in the protocol and
the category is re-measured in the next run; published snapshots are not changed.</li>
</ul>

<h2>Cost</h2>
<p>A full run is {answers} answers. Estimated with PromptBeacon's cost estimator from
LiteLLM's price map (about 500 output tokens per answer): <b>{_e(format_usd(total))}</b>
per run, at most {_e(format_usd(upper))} if every answer used 1024 tokens. Runs are
capped with <code>--max-cost</code>.</p>
<div class=table><table><thead><tr><th>Model</th><th class=num>Estimate per run</th></tr>
</thead><tbody>{cost_rows}</tbody></table></div>

<h2>Reproduce it</h2>
<pre>pip install promptbeacon
git clone {REPO} &amp;&amp; cd promptbeacon/index
python -m pbindex estimate
python -m pbindex run --max-cost 5 --categories python-http-client
python -m pbindex build</pre>
<p class="muted">Every snapshot records the SHA-256 of the protocol it used.
{"Badge base URL: " + _e(base_url) if base_url else ""}</p>
"""
    return _page("Methodology — AI Recommendation Index", body, demo=demo)


def build_site(
    data_dir: Path,
    out_dir: Path,
    protocols: Sequence[IndexProtocol],
    *,
    base_url: str | None = None,
) -> list[Path]:
    """Render every page, copy the data, and write the rank badges."""
    snaps = latest_snapshots(data_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    for sub in ("categories", "data", "raw", "badges"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)
    demo = any(s["demo"] for s in snaps)
    written = []

    def write(rel: str, text: str) -> None:
        path = out_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)

    write("index.html", overview_page(snaps))
    write("methodology.html", methodology_page(protocols, demo, base_url))
    for snap in snaps:
        cid = snap["id"]
        source: Path = snap.pop("_path")
        write(f"categories/{cid}.html", category_page(snap, base_url))
        shutil.copyfile(source, out_dir / "data" / f"{cid}.json")
        raw = source.parent / "raw" / f"{cid}.jsonl"
        if raw.exists():
            shutil.copyfile(raw, out_dir / "raw" / f"{cid}.jsonl")
        total = len(snap["results"])
        for r in snap["results"]:
            label, message, color = rank_badge_parts(
                r["rank"], total, snap["category"], demo=snap["demo"], tied=r["tied"]
            )
            write(
                f"badges/{cid}/{slug(r['name'])}.svg",
                render_badge(label, message, color),
            )
            endpoint = rank_endpoint(
                r["rank"], total, snap["category"], demo=snap["demo"], tied=r["tied"]
            )
            write(
                f"badges/{cid}/{slug(r['name'])}.json",
                json.dumps(endpoint, indent=2, ensure_ascii=False) + "\n",
            )
    return written
