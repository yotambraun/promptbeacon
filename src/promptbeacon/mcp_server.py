"""MCP server: use PromptBeacon from any AI assistant that speaks MCP.

Run with ``promptbeacon mcp`` (stdio). Requires the optional extra:
``pip install 'promptbeacon[mcp]'``. Setup for Claude Code, Claude Desktop,
Cursor, VS Code, Windsurf, Codex CLI and Gemini CLI is in ``docs/mcp.md``.

PromptBeacon is the measurement layer; the assistant does the reasoning. Every
tool is a thin wrapper over the public API (``configure_beacon``,
``Beacon.scan_async``, ``Beacon.estimate_cost``, the history database, the
share renderers, the funnel and ``init``'s planner) and returns plain JSON.
When no provider API key is configured, scans default to the keyless demo and
say so in the result, so nothing is billed unexpectedly. Nothing is printed on
stdout, which carries the protocol.
"""

from __future__ import annotations

import contextlib
import inspect
import sys
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field

from promptbeacon.builder import configure_beacon
from promptbeacon.core.config import (
    Provider,
    get_default_storage_path,
    get_tavily_api_key,
    has_api_key,
    has_tavily_api_key,
    parse_model_overrides,
    resolve_model,
)

DEMO_NOTE = (
    "No provider API key is configured, so this used keyless demo data "
    "(canned answers, not a real measurement). Set OPENAI_API_KEY, "
    "ANTHROPIC_API_KEY, GOOGLE_API_KEY (or GEMINI_API_KEY), MISTRAL_API_KEY, "
    "COHERE_API_KEY or PERPLEXITY_API_KEY for a real scan, or pass "
    'models={"litellm": "ollama/llama3.2"} for a local model.'
)

FUNNEL_DEMO_NOTE = (
    "TAVILY_API_KEY is not set, so this used the offline mock search backend "
    "(made-up results, not a measurement). Set TAVILY_API_KEY "
    "(https://tavily.com) for live web search."
)

INSTRUCTIONS = (
    "PromptBeacon measures whether AI assistants recommend a brand or "
    "open-source project; you interpret the numbers. Prefer project_scan for "
    "software projects (GitHub, PyPI, npm, crates.io, Hugging Face). Always pass "
    "a category when you know it. Scans with provider keys are billed: call "
    "estimate first, pass max_cost, and ask the user before spending. Scan once "
    "with save_report, then pass that file as report_path to compare, "
    "recommendations and share_assets, which then cost nothing. Results "
    "labelled measurement_tier='demo' are canned data, not a measurement."
)

# --- argument types (the descriptions are what MCP clients show) -----------------

Brand = Annotated[str, Field(description='The brand or product name, e.g. "httpx".')]
OptionalBrand = Annotated[
    str | None,
    Field(description="The brand or product name (or use project / report_path)."),
]
Project = Annotated[
    str,
    Field(
        description='"github:owner/name", "pypi:package", "npm:package", '
        '"crates:name", "hf:owner/name" (also hf:datasets/... and '
        "hf:spaces/...), or owner/name for GitHub."
    ),
]
OptionalProject = Annotated[
    str | None,
    Field(
        description='A project instead of brand: "github:owner/name", '
        '"pypi:package", "npm:package", "crates:name" or "hf:owner/name".'
    ),
]
Category = Annotated[
    str | None,
    Field(
        description="What users ask AI about, phrased the way they would ask, "
        'e.g. "python http client". Strongly advised: without one the prompts '
        "are generic."
    ),
]
Competitors = Annotated[
    list[str] | None,
    Field(description="Competitors to compare share of voice against."),
]
Providers = Annotated[
    list[str] | None,
    Field(
        description='Providers to query, e.g. ["openai", "anthropic"]: openai, '
        "anthropic, google, mistral, cohere, perplexity, litellm. Default: the "
        "providers named in models, otherwise openai."
    ),
]
Models = Annotated[
    dict[str, str] | None,
    Field(
        description='Model per provider, e.g. {"anthropic": "claude-sonnet-5-5"}, '
        'or {"litellm": "ollama/llama3.2"} for a local Ollama model (no key, '
        "no cost). The providers tool shows the defaults."
    ),
]
Prompts = Annotated[
    int | None, Field(description="Prompts per category (default 10).", ge=1)
]
Demo = Annotated[
    bool | None,
    Field(
        description="true: keyless demo data (free, labelled demo). false: a real "
        "scan (an error when no key is configured). Default: real when a key or "
        "a litellm model is configured, otherwise demo."
    ),
]
MaxCost = Annotated[
    float | None,
    Field(
        description="Spending cap in US dollars, e.g. 0.05. The scan is priced "
        "first and refused above the cap; during the scan no new request starts "
        "once it is reached, and the result has partial=true. Models with no "
        "known price (e.g. local) count as $0.",
        gt=0,
    ),
]
SaveReport = Annotated[
    str | None,
    Field(
        description="Also write the full JSON report to this path (inside the "
        "working directory), e.g. .promptbeacon/report.json, so compare, "
        "recommendations and share_assets can reuse it as report_path at no cost."
    ),
]
SaveHistory = Annotated[
    bool,
    Field(
        description="Save a real scan to the local history read by the history "
        "tool (demo scans are never saved)."
    ),
]
ReportPath = Annotated[
    str | None,
    Field(
        description="A report written by scan or project_scan (save_report) or by "
        "`promptbeacon scan -f json`, inside the working directory. When given, "
        "nothing is scanned and the call is free; the scan arguments are ignored."
    ),
]


def _live_possible(models: dict[str, str] | None = None) -> bool:
    """A key is configured, or a LiteLLM model (e.g. local Ollama) is set."""
    if any(has_api_key(p) for p in Provider.all()):
        return True
    overrides = parse_model_overrides(models)
    return resolve_model(Provider.LITELLM, overrides) is not None


def _resolve_demo(
    demo: bool | None, models: dict[str, str] | None = None
) -> tuple[bool, str | None]:
    """Default to demo when nothing live is configured, and explain why."""
    live = _live_possible(models)
    if demo is None:
        return (False, None) if live else (True, DEMO_NOTE)
    if not demo and not live:
        raise ValueError("No provider API key is configured. " + DEMO_NOTE)
    return demo, None


@contextlib.contextmanager
def _stdout_to_stderr():
    """Keep stray library prints off stdout, which carries the MCP protocol."""
    with contextlib.redirect_stdout(sys.stderr):
        yield


def _inside_cwd(path: str, what: str) -> Path:
    """Resolve ``path``; it must be inside the working directory."""
    resolved = Path(path).expanduser().resolve()
    cwd = Path.cwd().resolve()
    if resolved != cwd and cwd not in resolved.parents:
        raise ValueError(
            f"{what} must be inside the working directory ({cwd}); got {resolved}"
        )
    return resolved


def _load_report(report_path: str):
    from promptbeacon.core.schemas import Report

    path = _inside_cwd(report_path, "report_path")
    if not path.is_file():
        raise ValueError(f"report_path {path} does not exist.")
    try:
        return Report.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(
            f"report_path {path} is not a PromptBeacon JSON report "
            f"({type(e).__name__})."
        ) from None


def _project_info(beacon) -> dict[str, Any] | None:
    profile = getattr(beacon, "project", None)
    if profile is None:
        return None
    meta = profile.metadata
    return {
        "source": meta.source,
        "ref": meta.ref,
        "name": meta.name,
        "description": meta.description,
        "url": meta.url,
        "category_guess": profile.category.category,
        "category_basis": profile.category.basis,
        "category_confidence": profile.category.confidence,
        "competitor_candidates": profile.competitors,
    }


async def _build(**options):
    """configure_beacon off the event loop (project metadata reads the network)."""
    import anyio

    def build():
        return configure_beacon(**options)

    with _stdout_to_stderr():
        return await anyio.to_thread.run_sync(build)


async def _run(beacon):
    """Run a scan with stdout kept clean (generic-prompt warnings go in the result)."""
    import warnings

    with _stdout_to_stderr(), warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return await beacon.scan_async()


def _summary(report, note: str | None) -> dict[str, Any]:
    from promptbeacon.share.summary import report_summary

    result = report_summary(report)
    if report.prompt_strategy == "generic":
        result["warning"] = (
            "No category was given, so prompts were generic and the score says "
            "little. Pass a category."
        )
    if note:
        result["note"] = note
    return result


def _save_history(report) -> dict[str, Any]:
    """Best-effort save to the default history, as the CLI does for real scans."""
    from promptbeacon.storage.database import Database

    try:
        path = get_default_storage_path()
        with _stdout_to_stderr():
            db = Database(path)
            try:
                db.save_report(report)
            finally:
                db.close()
    except Exception as e:  # noqa: BLE001 - history is a convenience
        return {"history_warning": f"Not saved to history: {type(e).__name__}: {e}"}
    return {"saved_to_history": str(path)}


def _write_report(report, save_report: str) -> str:
    from promptbeacon.reporting.formats import to_json

    path = _inside_cwd(save_report, "save_report")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_json(report) + "\n", encoding="utf-8")
    return str(path)


async def _finish_scan(
    beacon,
    note: str | None,
    *,
    use_demo: bool,
    save_report: str | None,
    save_history: bool,
) -> dict[str, Any]:
    report = await _run(beacon)
    result = _summary(report, note)
    if save_report:
        result["report_path"] = _write_report(report, save_report)
    if save_history and not use_demo:
        result.update(_save_history(report))
    return result


# --- tools (plain functions; registered in create_server) -----------------------


def providers() -> dict[str, Any]:
    """Which LLM providers and search backends are configured (never the key values).

    Returns each provider's key status, the model each one will use, whether
    TAVILY_API_KEY is set (for funnel), and default_mode: "live" when a key or a
    litellm model is configured, otherwise "demo".

    Free: sends no requests.
    """
    configured = {p.value: has_api_key(p) for p in Provider.all()}
    models = {p.value: resolve_model(p) for p in Provider}
    return {
        "providers": configured,
        "models": models,
        "tavily": has_tavily_api_key(),
        "default_mode": "live" if _live_possible() else "demo",
    }


async def estimate(
    brand: OptionalBrand = None,
    project: OptionalProject = None,
    category: Category = None,
    competitors: Competitors = None,
    providers: Providers = None,
    models: Models = None,
    prompts: Prompts = None,
    grounded: Annotated[
        bool, Field(description="Price a web-grounded scan (adds search fees).")
    ] = False,
    max_cost: MaxCost = None,
) -> dict[str, Any]:
    """Price a scan before running it, from LiteLLM's bundled price map.

    Returns the expected and upper-bound cost per model, the number of answers
    and requests, models with no known price (counted as $0, e.g. local models),
    a one-line summary, and within_budget when max_cost is given. With no key
    configured, scans run in demo mode and the estimate is $0.

    Free: sends no requests (a project reads its public metadata).
    """
    use_demo, note = _resolve_demo(None, models)
    beacon = await _build(
        brand=brand,
        project=project,
        competitors=competitors,
        providers=providers,
        models=models,
        categories=[category] if category else None,
        prompt_count=prompts,
        demo=use_demo,
        grounded=grounded,
        max_cost=max_cost,
    )
    with _stdout_to_stderr():
        est = beacon.estimate_cost()
    result: dict[str, Any] = est.as_dict()
    result["summary"] = est.summary()
    result["max_cost_usd"] = max_cost
    result["within_budget"] = None if max_cost is None else est.total_usd <= max_cost
    if note:
        result["note"] = note
    return result


async def scan(
    brand: Brand,
    category: Category = None,
    competitors: Competitors = None,
    providers: Providers = None,
    models: Models = None,
    prompts: Prompts = None,
    demo: Demo = None,
    grounded: Annotated[
        bool,
        Field(
            description="Measure web-grounded answers (provider web search; costs "
            "more, records the cited pages)."
        ),
    ] = False,
    max_cost: MaxCost = None,
    save_report: SaveReport = None,
    save_history: SaveHistory = True,
) -> dict[str, Any]:
    """Measure how often AI assistants mention and recommend a brand.

    Returns the visibility score (0-100), share of voice and rank against the
    competitors, presence, a per-brand table, top cited sources, the models that
    answered, the cost, partial and budget, the top recommendations, and
    measurement_tier (demo, base_model or api_grounded).

    Cost: with provider keys this sends real requests billed to those keys (one
    per prompt per provider); call estimate first and pass max_cost. Without
    keys it uses keyless demo data, costs nothing, and says so in note.
    """
    use_demo, note = _resolve_demo(demo, models)
    beacon = configure_beacon(
        brand,
        competitors=competitors,
        providers=providers,
        models=models,
        categories=[category] if category else None,
        prompt_count=prompts,
        demo=use_demo,
        grounded=grounded,
        max_cost=max_cost,
    )
    return await _finish_scan(
        beacon,
        note,
        use_demo=use_demo,
        save_report=save_report,
        save_history=save_history,
    )


async def project_scan(
    project: Project,
    category: Annotated[
        str | None,
        Field(description='Override the guessed category, e.g. "python http client".'),
    ] = None,
    competitors: Annotated[
        list[str] | None, Field(description="Override the competitor candidates.")
    ] = None,
    providers: Providers = None,
    models: Models = None,
    prompts: Prompts = None,
    demo: Demo = None,
    infer_category: Annotated[
        bool,
        Field(
            description="Refine the category with one extra LLM request (live "
            "mode only)."
        ),
    ] = False,
    max_cost: MaxCost = None,
    save_report: SaveReport = None,
    save_history: SaveHistory = True,
) -> dict[str, Any]:
    """Does AI recommend this open-source project or package?

    Reads the project's public metadata (free public APIs) to guess its category
    and competitors, then scans. Returns the scan result plus a project object
    with the metadata and the guessed category and competitors, with their
    basis. Show the user the guess; pass category or competitors to correct it.

    Cost: as scan (billed with provider keys, free demo data without).
    """
    use_demo, note = _resolve_demo(demo, models)
    beacon = await _build(
        brand=None,
        project=project,
        competitors=competitors,
        providers=providers,
        models=models,
        categories=[category] if category else None,
        prompt_count=prompts,
        demo=use_demo,
        infer_category=infer_category,
        max_cost=max_cost,
    )
    result = await _finish_scan(
        beacon,
        note,
        use_demo=use_demo,
        save_report=save_report,
        save_history=save_history,
    )
    result["project"] = _project_info(beacon)
    return result


async def sources(
    brand: Brand,
    category: Category = None,
    competitors: Competitors = None,
    providers: Annotated[
        list[str] | None,
        Field(
            description="Providers with web search: openai, anthropic, google, "
            "perplexity."
        ),
    ] = None,
    models: Models = None,
    demo: Demo = None,
    grounded: Annotated[
        bool, Field(description="Use provider web search (needed for real citations).")
    ] = True,
    max_cost: MaxCost = None,
) -> dict[str, Any]:
    """Which websites AI answers cite for this category, and which cite the brand.

    Returns the cited domains with their type, citation count and whether each
    cites the brand.

    Cost: runs a web-grounded scan by default, which costs more than a plain
    scan (search fees); call estimate with grounded=true first. Free demo data
    without keys.
    """
    result = await scan(
        brand,
        category=category,
        competitors=competitors,
        providers=providers,
        models=models,
        demo=demo,
        grounded=grounded,
        max_cost=max_cost,
        save_history=False,
    )
    keep = (
        "brand",
        "categories",
        "measurement_tier",
        "top_sources",
        "note",
        "cost",
        "partial",
        "budget",
    )
    return {k: v for k, v in result.items() if k in keep}


async def _report_or_scan(
    report_path: str | None,
    *,
    brand: str | None,
    demo: bool | None,
    models: dict[str, str] | None,
    project: str | None = None,
    smart_recommendations: bool = False,
    **options,
):
    """A saved report (free), or a scan from the options. Returns (report, note)."""
    if report_path:
        return _load_report(report_path), None
    if not brand and not project:
        raise ValueError(
            "Provide brand (or project), or report_path with a saved report."
        )
    use_demo, note = _resolve_demo(demo, models)
    beacon = await _build(
        brand=brand, project=project, models=models, demo=use_demo, **options
    )
    if smart_recommendations:
        beacon = beacon.with_smart_recommendations()
    return await _run(beacon), note


async def compare(
    brand: OptionalBrand = None,
    competitors: Competitors = None,
    category: Category = None,
    providers: Providers = None,
    models: Models = None,
    prompts: Prompts = None,
    demo: Demo = None,
    max_cost: MaxCost = None,
    report_path: ReportPath = None,
) -> dict[str, Any]:
    """Compare the brand with each competitor, side by side.

    Returns comparison (per brand: visibility score, mentions and the share of
    positive mentions, best first) and brands (appearances and share of voice),
    plus the brand's rank, measurement_tier and the models that answered.

    Cost: free with report_path (a saved report). Otherwise it runs a scan with
    the competitors: billed with provider keys, free demo data without.
    """
    if not report_path and not competitors:
        raise ValueError("Pass competitors to compare against, or report_path.")
    report, note = await _report_or_scan(
        report_path,
        brand=brand,
        demo=demo,
        models=models,
        competitors=competitors,
        providers=providers,
        categories=[category] if category else None,
        prompt_count=prompts,
        max_cost=max_cost,
    )
    rows = [
        {
            "brand": report.brand,
            "is_target": True,
            "visibility_score": round(report.visibility_score, 1),
            "mention_count": report.mention_count,
            "positive_share": round(report.sentiment_breakdown.positive, 4),
        }
    ]
    rows += [
        {
            "brand": score.brand_name,
            "is_target": False,
            "visibility_score": round(score.visibility_score, 1),
            "mention_count": score.mention_count,
            "positive_share": round(score.sentiment.positive, 4),
        }
        for score in report.competitor_comparison.values()
    ]
    rows.sort(key=lambda r: -r["visibility_score"])
    result = _summary(report, note)
    for key in ("top_sources", "recommendations"):
        result.pop(key, None)
    result["comparison"] = rows
    if not report.competitor_comparison:
        result["warning"] = "The report has no competitors to compare with."
    return result


async def recommendations(
    brand: OptionalBrand = None,
    project: OptionalProject = None,
    category: Category = None,
    competitors: Competitors = None,
    providers: Providers = None,
    models: Models = None,
    prompts: Prompts = None,
    demo: Demo = None,
    max_cost: MaxCost = None,
    smart: Annotated[
        bool,
        Field(
            description="Ask an LLM to write the recommendations from the scan's "
            "data (one extra billed request; live scans only; keeps the rule-based "
            "ones if that request fails)."
        ),
    ] = False,
    report_path: ReportPath = None,
) -> dict[str, Any]:
    """What to change to be recommended more often, with the evidence behind it.

    Returns each recommendation's action, rationale, priority and expected
    impact, and the explanations of the score (for example which prompts or
    providers missed the brand). By default they are rule-based, derived from
    the scan's own answers; generated_by says which.

    Cost: free with report_path. Otherwise it runs a scan: billed with provider
    keys, free demo data without (demo recommendations describe canned data).
    smart=true adds one LLM request.
    """
    report, note = await _report_or_scan(
        report_path,
        brand=brand,
        project=project,
        demo=demo,
        models=models,
        smart_recommendations=smart,
        competitors=competitors,
        providers=providers,
        categories=[category] if category else None,
        prompt_count=prompts,
        max_cost=max_cost,
    )
    if report_path:
        generated_by = "saved report"
    elif smart and report.measurement_tier != "demo":
        generated_by = "llm (rule-based if the extra request failed)"
    else:
        generated_by = "rules"
    result: dict[str, Any] = {
        "brand": report.brand,
        "categories": report.categories,
        "measurement_tier": report.measurement_tier,
        "visibility_score": round(report.visibility_score, 1),
        "generated_by": generated_by,
        "recommendations": [r.model_dump(mode="json") for r in report.recommendations],
        "explanations": [e.model_dump(mode="json") for e in report.explanations],
    }
    if smart and not report_path and report.measurement_tier == "demo":
        ignored = "smart is ignored in demo mode."
        note = f"{note} {ignored}" if note else ignored
    if note:
        result["note"] = note
    return result


def history(
    brand: Brand,
    days: Annotated[
        int, Field(description="How many days back to read (default 30).", ge=1)
    ] = 30,
    storage: Annotated[
        str | None,
        Field(
            description="A history file to read instead of this server's default "
            "($PROMPTBEACON_HOME/data.db, else ~/.promptbeacon/data.db). The CLI "
            "saves to ~/.promptbeacon/data.db."
        ),
    ] = None,
) -> dict[str, Any]:
    """The brand's saved scans over time, the trend, and whether the change is significant.

    Returns each saved scan's score and mentions (data_points), trend_direction,
    the average and volatility, latest_change (the latest scan against the one
    before it), and significance: the earlier half of the scans against the
    later half, with PromptBeacon's effect-size check (Cohen's d of 0.5 or more
    counts as significant; it is not a p-value). Only real scans are saved: by
    scan and project_scan here, and by `promptbeacon scan` in a terminal.
    Scores from different models, categories or measurement tiers are not
    comparable.

    Free and offline: reads a local file.
    """
    from promptbeacon.analysis.statistics import check_significance
    from promptbeacon.beacon import Beacon

    path = Path(storage).expanduser() if storage else get_default_storage_path()
    if not path.is_file():
        return {
            "brand": brand,
            "storage": str(path),
            "scans": 0,
            "data_points": [],
            "note": "No history yet. Real scans (not demo) are saved by scan and "
            "project_scan, and by `promptbeacon scan`.",
        }
    with _stdout_to_stderr():
        beacon = Beacon(brand).with_storage(path)
        try:
            report = beacon.get_history(days)
            previous = beacon.compare_with_previous()
        finally:
            beacon.close()
    scores = report.visibility_trend
    half = len(scores) // 2
    test = check_significance(scores[:half], scores[half:])
    result: dict[str, Any] = report.model_dump(mode="json")
    result["storage"] = str(path)
    result["scans"] = len(scores)
    result["latest_change"] = previous.model_dump(mode="json") if previous else None
    result["significance"] = {
        "compared": f"first {half} vs last {len(scores) - half} scans",
        **test.model_dump(mode="json"),
    }
    return result


async def funnel(
    brand: Brand,
    category: Category = None,
    prompt: Annotated[
        str | None,
        Field(
            description="A buyer-intent prompt to fan out (default, from the "
            'category: "What are the best <category>?").'
        ),
    ] = None,
    competitors: Competitors = None,
    demo: Annotated[
        bool | None,
        Field(
            description="true: offline mock search (free). false: live Tavily "
            "search (an error without TAVILY_API_KEY). Default: live when "
            "TAVILY_API_KEY is set, otherwise mock."
        ),
    ] = None,
    sub_queries: Annotated[
        int, Field(description="Fan-out width: sub-queries per prompt.", ge=1, le=20)
    ] = 8,
) -> dict[str, Any]:
    """Where the brand drops out of an agentic web search: retrieval, rerank or citation.

    Fans a buyer prompt out into sub-queries, retrieves web results for each,
    reranks them and keeps the top ones as citations, and reports
    sub_query_coverage, rerank_survival_rate, retrieval_to_citation_ratio and
    stage_failure, with the result of each sub-query. It is a local model of
    agentic search, not a consumer AI product.

    Cost: live mode makes one Tavily search per sub-query, billed to
    TAVILY_API_KEY; no LLM requests. Without TAVILY_API_KEY it uses an offline
    mock search backend (free) and says so in note.
    """
    from promptbeacon.funnel import (
        MockSearchBackend,
        SearchBackend,
        TavilyBackend,
        run_funnel,
    )

    if prompt:
        query = prompt
    elif category:
        query = f"What are the best {category}?"
    else:
        query = f"What are the best alternatives to {brand}?"

    api_key = get_tavily_api_key()
    note = None
    if demo is None:
        demo = api_key is None
        note = FUNNEL_DEMO_NOTE if demo else None
    backend: SearchBackend
    if demo:
        backend = MockSearchBackend(brand, competitors or [])
    elif api_key is None:
        raise ValueError(
            "funnel needs TAVILY_API_KEY for live web search (get a key at "
            "https://tavily.com), or demo=true for the offline mock backend."
        )
    else:
        backend = TavilyBackend(api_key)

    with _stdout_to_stderr():
        report = await run_funnel(
            brand,
            query,
            backend=backend,
            competitors=competitors or [],
            n_sub_queries=sub_queries,
        )
    result: dict[str, Any] = report.model_dump(
        mode="json",
        exclude={
            "sub_query_results": {"__all__": {"retrieved": {"__all__": {"snippet"}}}}
        },
    )
    result["backend"] = backend.name
    result["demo"] = demo
    if note:
        result["note"] = note
    return result


def init_preview(
    path: Annotated[
        str,
        Field(description="The repository root (default: the working directory)."),
    ] = ".",
    brand: Annotated[
        str | None, Field(description="Name to measure (default: the project name).")
    ] = None,
    category: Category = None,
    competitors: Competitors = None,
    providers: Providers = None,
    models: Models = None,
    max_cost: Annotated[
        float | None,
        Field(
            description="Cap per weekly run in US dollars (default: twice the "
            "estimate, rounded up to $0.05).",
            gt=0,
        ),
    ] = None,
    protocol: Annotated[
        bool,
        Field(
            description="Also plan .promptbeacon/protocol.json, pinning the prompts "
            "and models."
        ),
    ] = False,
) -> dict[str, Any]:
    """Preview what `promptbeacon init` would set up in a repository. Never writes files.

    Reads pyproject.toml, package.json, Cargo.toml, the README and the git
    remote (no network) and returns the detected project, the proposed category
    and competitors with their basis, the estimated cost per weekly run and its
    cap, the files it would write (the weekly GitHub workflow, with a diff
    against an existing file), the README badge snippets, the secrets to add,
    the next steps, and command: the terminal command that writes this plan.
    Show the user the plan and let them run the command.

    Free: reads local files only.
    """
    import shlex

    from promptbeacon.init_project import build_plan, detect_project

    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"{root} is not a directory.")
    model_args = [f"{k}={v}" for k, v in (models or {}).items()] or None
    with _stdout_to_stderr():
        project = detect_project(root)
        plan = build_plan(
            project,
            brand=brand,
            category=category,
            competitors=competitors,
            providers=providers,
            models=model_args,
            max_cost=max_cost,
            protocol=protocol,
        )
    if not plan.category and not plan.uses_protocol:
        raise ValueError(
            "No category: PromptBeacon could not guess one from the project files. "
            'Ask the user and pass category, e.g. "python http client".'
        )
    # The plan's own choices, so the command writes what was previewed. --yes
    # writes new files only; a changed file is never replaced without --force.
    args = ["promptbeacon", "init", "--yes"]
    if root != Path.cwd().resolve():
        args.append(str(root))
    if brand:
        args += ["--brand", brand]
    pinned = project.protocol is not None  # an existing protocol.json decides
    if plan.category and not pinned:
        args += ["--category", plan.category]
    for name in [] if pinned else plan.competitors:
        args += ["--competitor", name]
    for name in providers or []:
        args += ["--provider", name]
    for value in model_args or []:
        args += ["--model", value]
    if max_cost is not None:
        args += ["--max-cost", str(max_cost)]
    if protocol:
        args.append("--protocol")
    result = plan.as_dict()
    result["written"] = []
    result["command"] = shlex.join(args)
    return result


async def share_assets(
    brand: OptionalBrand = None,
    project: OptionalProject = None,
    category: Category = None,
    competitors: Competitors = None,
    providers: Providers = None,
    models: Models = None,
    demo: Demo = None,
    output_dir: Annotated[
        str,
        Field(
            description="Directory for the files, inside the working directory "
            "(default .promptbeacon)."
        ),
    ] = ".promptbeacon",
    png: Annotated[
        bool,
        Field(description="Also write card.png (needs the promptbeacon[share] extra)."),
    ] = False,
    max_cost: MaxCost = None,
    report_path: ReportPath = None,
) -> dict[str, Any]:
    """Write a README badge, shields.io JSON and light and dark share cards.

    Writes badge.svg, badge.json, card.svg and card-dark.svg (and card.png),
    plus a rank badge (rank.svg, rank.json: "#2 of 3 · python http clients")
    when there is a category and at least two competitors. Returns the file
    paths, README snippets and the scan summary. Demo results are labelled demo
    on the badge and card.

    Cost: free with report_path. Otherwise it runs one scan: billed with
    provider keys, free demo data without.
    """
    import json

    from promptbeacon.share import (
        RankUnavailableError,
        badge_endpoint,
        render_badge_svg,
        render_card_png,
        render_card_svg,
    )

    out = _inside_cwd(output_dir, "output_dir")
    beacon = None
    if report_path:
        report, note = _load_report(report_path), None
    else:
        use_demo, note = _resolve_demo(demo, models)
        beacon = await _build(
            brand=brand,
            project=project,
            competitors=competitors,
            providers=providers,
            models=models,
            categories=[category] if category else None,
            demo=use_demo,
            max_cost=max_cost,
        )
        report = await _run(beacon)

    out.mkdir(parents=True, exist_ok=True)
    files = {
        "badge_svg": out / "badge.svg",
        "badge_json": out / "badge.json",
        "card_svg": out / "card.svg",
        "card_dark_svg": out / "card-dark.svg",
    }
    files["badge_svg"].write_text(render_badge_svg(report), encoding="utf-8")
    files["badge_json"].write_text(
        json.dumps(badge_endpoint(report), indent=2) + "\n", encoding="utf-8"
    )
    files["card_svg"].write_text(render_card_svg(report, "light"), encoding="utf-8")
    files["card_dark_svg"].write_text(render_card_svg(report, "dark"), encoding="utf-8")
    rank_note = None
    try:
        rank_svg = render_badge_svg(report, label="AI rank", metric="rank")
    except RankUnavailableError as e:
        rank_note = str(e)
    else:
        files["rank_svg"] = out / "rank.svg"
        files["rank_json"] = out / "rank.json"
        files["rank_svg"].write_text(rank_svg, encoding="utf-8")
        files["rank_json"].write_text(
            json.dumps(badge_endpoint(report, label="AI rank", metric="rank"), indent=2)
            + "\n",
            encoding="utf-8",
        )
    warning = None
    if png:
        try:
            (out / "card.png").write_bytes(render_card_png(report))
            files["card_png"] = out / "card.png"
        except ImportError as e:
            warning = str(e)

    badge_path = files["badge_svg"].as_posix()
    card, card_dark = files["card_svg"].as_posix(), files["card_dark_svg"].as_posix()
    result: dict[str, Any] = {
        "files": {k: str(v) for k, v in files.items()},
        "readme_badge": (
            f"[![AI visibility]({badge_path})](https://github.com/yotambraun/promptbeacon)"
        ),
        "readme_card": (
            "<picture>\n"
            f'  <source media="(prefers-color-scheme: dark)" srcset="{card_dark}">\n'
            f'  <img alt="AI recommendation card" src="{card}" width="600">\n'
            "</picture>"
        ),
        "summary": _summary(report, None),
    }
    if "rank_svg" in files:
        result["readme_rank_badge"] = (
            f"[![AI rank]({files['rank_svg'].as_posix()})]"
            "(https://github.com/yotambraun/promptbeacon)"
        )
    else:
        result["rank_badge"] = rank_note
    if report.measurement_tier == "demo":
        result["note"] = note or "Demo data: the badge and card are labelled as demo."
    if warning:
        result["warning"] = warning
    project_info = _project_info(beacon) if beacon is not None else None
    if project_info:
        result["project"] = project_info
    return result


# name -> (tool, read-only, reaches outside the machine). Read-only means the
# tool changes nothing locally; scan and project_scan save to the history, and
# share_assets writes files.
TOOLS = {
    "providers": (providers, True, False),
    "estimate": (estimate, True, True),
    "scan": (scan, False, True),
    "project_scan": (project_scan, False, True),
    "sources": (sources, True, True),
    "compare": (compare, True, True),
    "recommendations": (recommendations, True, True),
    "history": (history, True, False),
    "funnel": (funnel, True, True),
    "init_preview": (init_preview, True, False),
    "share_assets": (share_assets, False, True),
}


def create_server():
    """Build the MCP server (requires the ``mcp`` extra)."""
    try:
        from mcp.server import MCPServer
        from mcp.types import ToolAnnotations
    except ImportError as e:  # pragma: no cover - exercised via the CLI
        raise ImportError(
            "The MCP server needs the 'mcp' extra: pip install 'promptbeacon[mcp]'"
        ) from e

    from promptbeacon import __version__

    server = MCPServer(
        "promptbeacon",
        title="PromptBeacon",
        description="Measure whether AI assistants recommend a brand or project.",
        instructions=INSTRUCTIONS,
        website_url="https://github.com/yotambraun/promptbeacon",
        version=__version__,
    )
    for name, (fn, read_only, open_world) in TOOLS.items():
        server.tool(
            name=name,
            description=inspect.cleandoc(fn.__doc__ or ""),
            annotations=ToolAnnotations(
                readOnlyHint=read_only,
                destructiveHint=False,
                openWorldHint=open_world,
            ),
        )(fn)
    return server


def main() -> None:
    """Run the server over stdio."""
    create_server().run("stdio")
