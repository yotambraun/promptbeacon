"""Rank-in-category badges: real data only, demo is grey, clear errors."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import pytest
from typer.testing import CliRunner

from promptbeacon import Beacon
from promptbeacon.cli.main import app
from promptbeacon.core.schemas import BudgetReport, Report
from promptbeacon.share import (
    RankUnavailableError,
    badge_endpoint,
    card_data,
    rank_badge_parts,
    rank_endpoint,
    render_badge_svg,
    report_rank,
)
from promptbeacon.share.badge import COLOR_DEMO, COLOR_RANK, pluralize


def _demo(competitors=("requests", "aiohttp"), category="python http client"):
    beacon = Beacon("httpx").demo().with_competitors(*competitors)
    if category:
        beacon = beacon.with_category(category)
    return beacon.scan()


def _real(report: Report, appearances: dict[str, int] | None = None) -> Report:
    copy = report.model_copy(deep=True)
    copy.measurement_tier = "base_model"
    if appearances:
        for name, count in appearances.items():
            copy.share_of_voice.aggregate[name].appearances = count
    return copy


@pytest.mark.parametrize(
    ("category", "plural"),
    [
        ("python http client", "python http clients"),
        ("vector database", "vector databases"),
        ("running shoes", "running shoes"),
        ("javascript test library", "javascript test libraries"),
        ("python linter for ci", "python linter for cis"),  # best effort
        ("static site generator", "static site generators"),
        ("css toolbox", "css toolboxes"),
    ],
)
def test_pluralize(category, plural):
    assert pluralize(category) == plural


def test_rank_from_a_real_report():
    report = _real(_demo(), {"httpx": 7, "requests": 9, "aiohttp": 3})
    assert report_rank(report) == (2, 3, False, "python http client")
    svg = render_badge_svg(report, label="AI rank", metric="rank")
    root = ET.fromstring(svg)
    title = root.find("{http://www.w3.org/2000/svg}title").text
    assert title == "AI rank: #2 of 3 · python http clients"
    assert f"#{COLOR_RANK}" in svg


def test_ties_say_tied():
    report = _real(_demo(), {"httpx": 9, "requests": 9, "aiohttp": 3})
    rank, total, tied, _ = report_rank(report)
    assert (rank, total, tied) == (1, 3, True)
    assert badge_endpoint(report, label="AI rank", metric="rank")["message"] == (
        "tied #1 of 3 · python http clients"
    )


def test_demo_rank_badge_is_grey_and_says_demo():
    data = badge_endpoint(_demo(), label="AI rank", metric="rank")
    assert data["label"] == "AI rank · demo"
    assert data["color"] == COLOR_DEMO


def test_partial_reports_say_partial():
    report = _real(_demo(), {"httpx": 7, "requests": 9, "aiohttp": 3})
    report.budget = BudgetReport(
        max_cost_usd=0.01, planned_answers=10, completed_answers=4, skipped_answers=6
    )
    assert badge_endpoint(report, metric="rank", label="AI rank")["label"] == (
        "AI rank · partial"
    )
    assert badge_endpoint(report)["label"] == "AI visibility · partial"
    assert (
        "partial: cost cap reached after 4 of 10 answers" in card_data(report).subtitle
    )


def test_rank_needs_a_category_and_three_projects():
    with pytest.raises(RankUnavailableError, match="--category"):
        report_rank(_real(_demo(category=None)))
    with pytest.raises(RankUnavailableError, match="at least 3 projects"):
        report_rank(_real(_demo(competitors=("requests",))))


def test_rank_badge_parts_for_external_rankings():
    label, message, color = rank_badge_parts(2, 9, "python http client")
    assert (label, message, color) == (
        "AI rank",
        "#2 of 9 · python http clients",
        COLOR_RANK,
    )
    demo = rank_endpoint(2, 9, "python http client", demo=True)
    assert demo["label"] == "AI rank · demo" and demo["color"] == COLOR_DEMO
    assert demo["schemaVersion"] == 1


def test_cli_rank_badge_and_endpoint(tmp_path):
    report = _real(_demo(), {"httpx": 7, "requests": 9, "aiohttp": 3})
    path = tmp_path / "report.json"
    path.write_text(report.model_dump_json(), encoding="utf-8")
    result = CliRunner().invoke(
        app,
        ["badge", "--report", str(path), "--metric", "rank", "-o",
         str(tmp_path / "rank.svg"), "--endpoint", str(tmp_path / "rank.json")],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    data = json.loads((tmp_path / "rank.json").read_text(encoding="utf-8"))
    assert data["label"] == "AI rank"
    assert data["message"] == "#2 of 3 · python http clients"
    assert "[![AI rank]" in result.stderr


def test_cli_rank_badge_error_has_the_fix(tmp_path):
    result = CliRunner().invoke(
        app,
        ["badge", "httpx", "-t", "python http client", "-c", "requests", "--demo",
         "--metric", "rank", "-o", str(tmp_path / "r.svg")],
    )  # fmt: skip
    assert result.exit_code == 1
    assert "add competitors" in " ".join(result.stderr.split())
    assert not (tmp_path / "r.svg").exists()


async def test_mcp_share_assets_writes_rank_badge(tmp_path, monkeypatch):
    from promptbeacon import mcp_server

    monkeypatch.chdir(tmp_path)
    result = await mcp_server.share_assets(
        brand="httpx",
        category="python http client",
        competitors=["requests", "aiohttp"],
        demo=True,
        output_dir="out",
    )
    assert "rank_svg" in result["files"]
    assert "readme_rank_badge" in result
    data = json.loads((tmp_path / "out" / "rank.json").read_text(encoding="utf-8"))
    assert data["label"] == "AI rank · demo"
