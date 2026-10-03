"""MCP server: use PromptBeacon from Claude Code, Cursor or any MCP client.

Run with ``promptbeacon mcp`` (stdio). Requires the optional extra:
``pip install 'promptbeacon[mcp]'``.

Every tool is a thin wrapper over the public API (``configure_beacon``,
``Beacon.scan_async``, the share renderers) and returns plain JSON. When no
provider API key is configured, scans default to the keyless demo and say so
in the result, so nothing is billed unexpectedly.
"""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path
from typing import Any

from promptbeacon.builder import configure_beacon
from promptbeacon.core.config import Provider, has_api_key, has_tavily_api_key

DEMO_NOTE = (
    "No provider API key is configured, so this used keyless demo data "
    "(canned answers, not a real measurement). Set OPENAI_API_KEY, "
    "ANTHROPIC_API_KEY, GOOGLE_API_KEY, MISTRAL_API_KEY, COHERE_API_KEY or "
    "PERPLEXITY_API_KEY for a real scan."
)

INSTRUCTIONS = (
    "PromptBeacon measures whether AI assistants recommend a brand or "
    "open-source project. Prefer project_scan for software projects (GitHub, "
    "PyPI, npm). Always pass a category when you know it. Results labelled "
    "measurement_tier='demo' are canned data, not a measurement."
)


def _any_keys() -> bool:
    return any(has_api_key(p) for p in Provider)


def _resolve_demo(demo: bool | None) -> tuple[bool, str | None]:
    """Default to demo when no keys are configured, and explain why."""
    if demo is None:
        demo = not _any_keys()
        return demo, DEMO_NOTE if demo else None
    if not demo and not _any_keys():
        raise ValueError("No provider API key is configured. " + DEMO_NOTE)
    return demo, None


@contextlib.contextmanager
def _stdout_to_stderr():
    """Keep stray library prints off stdout, which carries the MCP protocol."""
    with contextlib.redirect_stdout(sys.stderr):
        yield


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


async def _scan(beacon, note: str | None) -> dict[str, Any]:
    import warnings

    from promptbeacon.share.summary import report_summary

    with _stdout_to_stderr(), warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        report = await beacon.scan_async()
    result = report_summary(report)
    if report.prompt_strategy == "generic":
        result["warning"] = (
            "No category was given, so prompts were generic and the score says "
            "little. Pass a category."
        )
    if note:
        result["note"] = note
    return result


# --- tools (plain async functions; registered in create_server) -----------------


def providers() -> dict[str, Any]:
    """Which LLM providers and search backends are configured (never the keys)."""
    configured = {p.value: has_api_key(p) for p in Provider}
    return {
        "providers": configured,
        "tavily": has_tavily_api_key(),
        "default_mode": "live" if any(configured.values()) else "demo",
    }


async def scan(
    brand: str,
    category: str | None = None,
    competitors: list[str] | None = None,
    providers: list[str] | None = None,
    prompts: int | None = None,
    demo: bool | None = None,
    grounded: bool = False,
) -> dict[str, Any]:
    """Measure how often AI assistants mention and recommend a brand.

    Args:
        brand: The brand or product name.
        category: What buyers ask about, e.g. "running shoes" (strongly advised).
        competitors: Competitors to compare share of voice against.
        providers: e.g. ["openai", "anthropic"]; defaults to openai.
        prompts: Prompts per category (default 10).
        demo: True for keyless demo data; default is demo only when no keys exist.
        grounded: Measure web-grounded answers (provider web search; costs more).
    """
    use_demo, note = _resolve_demo(demo)
    beacon = configure_beacon(
        brand,
        competitors=competitors,
        providers=providers,
        categories=[category] if category else None,
        prompt_count=prompts,
        demo=use_demo,
        grounded=grounded,
    )
    return await _scan(beacon, note)


async def project_scan(
    project: str,
    category: str | None = None,
    competitors: list[str] | None = None,
    providers: list[str] | None = None,
    prompts: int | None = None,
    demo: bool | None = None,
    infer_category: bool = False,
) -> dict[str, Any]:
    """Does AI recommend this open-source project or package?

    Reads public metadata to guess the category and competitors, then scans.

    Args:
        project: "github:owner/name", "pypi:package", "npm:package", or owner/name.
        category: Override the guessed category, e.g. "python http client".
        competitors: Override the competitor candidates.
        providers: e.g. ["openai", "anthropic"].
        prompts: Prompts per category (default 10).
        demo: True for keyless demo data; default is demo only when no keys exist.
        infer_category: Refine the category with one LLM call (live mode only).
    """
    import anyio

    use_demo, note = _resolve_demo(demo)

    def build():
        return configure_beacon(
            None,
            project=project,
            competitors=competitors,
            providers=providers,
            categories=[category] if category else None,
            prompt_count=prompts,
            demo=use_demo,
            infer_category=infer_category,
        )

    with _stdout_to_stderr():
        beacon = await anyio.to_thread.run_sync(build)
    result = await _scan(beacon, note)
    result["project"] = _project_info(beacon)
    return result


async def sources(
    brand: str,
    category: str | None = None,
    competitors: list[str] | None = None,
    providers: list[str] | None = None,
    demo: bool | None = None,
    grounded: bool = True,
) -> dict[str, Any]:
    """Which websites AI answers cite for this category, and which cite the brand.

    Args:
        brand: The brand or product name.
        category: The category, e.g. "running shoes".
        competitors: Competitors to attribute citations to.
        providers: Providers with web search (openai, anthropic, google, perplexity).
        demo: True for keyless demo data; default is demo only when no keys exist.
        grounded: Use provider web search (needed for real citations).
    """
    result = await scan(
        brand,
        category=category,
        competitors=competitors,
        providers=providers,
        demo=demo,
        grounded=grounded,
    )
    keep = ("brand", "categories", "measurement_tier", "top_sources", "note", "cost")
    return {k: v for k, v in result.items() if k in keep}


async def share_assets(
    brand: str | None = None,
    project: str | None = None,
    category: str | None = None,
    competitors: list[str] | None = None,
    providers: list[str] | None = None,
    demo: bool | None = None,
    output_dir: str = ".promptbeacon",
    png: bool = False,
) -> dict[str, Any]:
    """Scan once and write a README badge, shields.io JSON and share cards.

    Args:
        brand: Brand to scan (or use project).
        project: "github:owner/name", "pypi:package" or "npm:package".
        category: The category, e.g. "python http client".
        competitors: Competitors to compare against.
        providers: e.g. ["openai", "anthropic"].
        demo: True for keyless demo data; default is demo only when no keys exist.
        output_dir: Directory for badge.svg, badge.json, card.svg, card-dark.svg.
        png: Also write card.png (needs the 'promptbeacon[share]' extra).
    """
    import json
    import warnings

    import anyio

    from promptbeacon.share import (
        badge_endpoint,
        render_badge_svg,
        render_card_png,
        render_card_svg,
    )
    from promptbeacon.share.summary import report_summary

    out = Path(output_dir).expanduser().resolve()
    cwd = Path.cwd().resolve()
    if out != cwd and cwd not in out.parents:
        raise ValueError(
            f"output_dir must be inside the working directory ({cwd}); got {out}"
        )
    use_demo, note = _resolve_demo(demo)

    def build():
        return configure_beacon(
            brand,
            project=project,
            competitors=competitors,
            providers=providers,
            categories=[category] if category else None,
            demo=use_demo,
        )

    with _stdout_to_stderr():
        beacon = await anyio.to_thread.run_sync(build)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            report = await beacon.scan_async()

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
        "summary": report_summary(report),
    }
    if report.measurement_tier == "demo":
        result["note"] = note or "Demo data: the badge and card are labelled as demo."
    if warning:
        result["warning"] = warning
    project_info = _project_info(beacon)
    if project_info:
        result["project"] = project_info
    return result


def create_server():
    """Build the MCP server (requires the ``mcp`` extra)."""
    try:
        from mcp.server import MCPServer
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
    server.tool()(providers)
    server.tool()(scan)
    server.tool()(project_scan)
    server.tool()(sources)
    server.tool()(share_assets)
    return server


def main() -> None:
    """Run the server over stdio."""
    create_server().run("stdio")
