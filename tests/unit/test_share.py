"""Badges and share cards: valid output for every kind of input."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import pytest
from typer.testing import CliRunner

from promptbeacon import Beacon
from promptbeacon.cli.main import app
from promptbeacon.core.schemas import Report
from promptbeacon.share import (
    badge_endpoint,
    card_data,
    render_badge_svg,
    render_card_png,
    render_card_svg,
    shields_url,
)
from promptbeacon.share.text import text_width, truncate

SVG_NS = "{http://www.w3.org/2000/svg}"

# Fields allowed by https://shields.io/badges/endpoint-badge
SHIELDS_FIELDS = {
    "schemaVersion",
    "label",
    "message",
    "color",
    "labelColor",
    "isError",
    "namedLogo",
    "logoSvg",
    "logoColor",
    "logoWidth",
    "logoSize",
    "style",
    "cacheSeconds",
}


def _report(brand="Nike", competitors=("Adidas", "Hoka"), category="running shoes"):
    beacon = Beacon(brand).demo().with_competitors(*competitors)
    if category:
        beacon = beacon.with_category(category)
    return beacon.scan()


def _real(report: Report, score: float | None = None) -> Report:
    copy = report.model_copy(deep=True)
    copy.measurement_tier = "base_model"
    if score is not None:
        copy.visibility_score = score
    return copy


def _parse(svg: str) -> ET.Element:
    root = ET.fromstring(svg)
    assert root.tag == f"{SVG_NS}svg"
    return root


def _texts(root: ET.Element) -> list[str]:
    return ["".join(t.itertext()) for t in root.iter(f"{SVG_NS}text")]


# --- shields endpoint ---------------------------------------------------------


def _assert_valid_endpoint(data: dict) -> None:
    assert set(data) <= SHIELDS_FIELDS
    assert data["schemaVersion"] == 1
    assert isinstance(data["label"], str)
    assert isinstance(data["message"], str) and data["message"].strip()
    if "logoSvg" in data:
        _parse(data["logoSvg"])
    json.dumps(data)  # serialisable


@pytest.mark.parametrize("metric", ["both", "score", "sov"])
def test_badge_endpoint_follows_shields_schema(metric):
    data = badge_endpoint(_real(_report()), metric=metric)
    _assert_valid_endpoint(data)


def test_badge_endpoint_content_and_colors():
    report = _real(_report(), score=82)
    data = badge_endpoint(report)
    assert data["label"] == "AI visibility"
    assert data["message"].startswith("82/100 · SoV ")
    assert data["color"] == "15803d"
    assert badge_endpoint(_real(_report(), 55))["color"] == "b45309"
    assert badge_endpoint(_real(_report(), 12))["color"] == "b91c1c"


def test_demo_badges_are_labelled_demo_and_grey():
    data = badge_endpoint(_report())
    assert "demo" in data["label"]
    assert data["color"] == "64748b"
    assert "demo" in render_badge_svg(_report())


@pytest.mark.parametrize("score", [0.0, 100.0])
def test_badge_extreme_scores(score):
    report = _real(_report(), score)
    _assert_valid_endpoint(badge_endpoint(report))
    root = _parse(render_badge_svg(report))
    assert f"{round(score)}/100" in " ".join(_texts(root))


def test_badge_without_share_of_voice_falls_back_to_score():
    report = _real(_report())
    report.share_of_voice = None
    assert badge_endpoint(report)["message"] == f"{round(report.visibility_score)}/100"


def test_badge_svg_escapes_and_handles_unicode():
    report = _real(_report())
    svg = render_badge_svg(report, label='AI <visibility> & "más" 可见度')
    root = _parse(svg)
    assert 'AI <visibility> & "más" 可见度' in _texts(root)
    assert int(root.get("width")) > 100


def test_shields_url_encodes_the_json_url():
    url = shields_url(
        "https://raw.githubusercontent.com/o/r/main/.promptbeacon/badge.json"
    )
    assert url.startswith("https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.")
    assert "/" not in url.split("url=", 1)[1]


# --- card ---------------------------------------------------------------------


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_card_svg_is_well_formed_and_sized(theme):
    root = _parse(render_card_svg(_report(), theme))
    assert root.get("width") == "1200" and root.get("height") == "630"
    texts = _texts(root)
    assert "Which running shoes does AI recommend?" in texts
    assert "Demo data" in texts
    assert root.find(f"{SVG_NS}title") is not None  # accessible name


def test_card_marks_measurement_tier():
    texts = _texts(_parse(render_card_svg(_real(_report()))))
    assert "Base model" in texts and "Demo data" not in texts


def test_card_without_category_asks_about_the_brand():
    data = card_data(_report(category=None))
    assert data.title == "Does AI recommend Nike?"


def test_card_limits_rows_but_always_shows_the_target():
    report = _report(competitors=[f"Rival {i}" for i in range(12)])
    entry = report.share_of_voice.aggregate["Nike"]
    entry.appearances = 0  # target ranks last
    data = card_data(report)
    assert len(data.rows) == 6
    assert data.rows[-1].name == "Nike" and data.rows[-1].is_target
    assert data.hidden_rows == 13 - 6
    _parse(render_card_svg(report))


def test_card_handles_long_and_unicode_names():
    long_name = "Acme Widgets International Holdings Of Exceptionally Long Names"
    report = _report(
        brand=long_name,
        competitors=["饿了么", "Ünïcødé & <Co>", "Globex"],
        category="industrial-grade precision widget manufacturing equipment",
    )
    root = _parse(render_card_svg(report))
    texts = _texts(root)
    assert any(t.startswith("Acme Widgets") and t.endswith("…") for t in texts)
    assert "饿了么" in texts
    assert "Ünïcødé & <Co>" in texts


def test_card_zero_and_full_presence():
    report = _report()
    for name, entry in report.share_of_voice.aggregate.items():
        entry.appearances = entry.total_prompts if name == "Adidas" else 0
    root = _parse(render_card_svg(report))
    texts = _texts(root)
    assert "10/10" in texts and "0/10" in texts


def test_card_without_share_of_voice_or_results():
    report = _real(_report())
    report.share_of_voice = None
    report.provider_results = []
    data = card_data(report)
    assert data.rows[0].is_target and data.rows[0].total == 0
    _parse(render_card_svg(report))


def test_card_png_is_a_2x_png():
    pytest.importorskip("PIL")
    from io import BytesIO

    from PIL import Image

    png = render_card_png(_report(), "dark")
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert Image.open(BytesIO(png)).size == (2400, 1260)


def test_truncate_fits_width():
    text = "x" * 200
    out = truncate(text, 100, 16)
    assert out.endswith("…") and text_width(out, 16) <= 100
    assert truncate("short", 100, 16) == "short"


def test_report_json_round_trips_for_rendering():
    report = _report()
    again = Report.model_validate_json(report.model_dump_json())
    assert render_card_svg(again) == render_card_svg(report)


# --- CLI ----------------------------------------------------------------------

runner = CliRunner()


def test_cli_badge_writes_svg_and_endpoint(tmp_path):
    svg, endpoint = tmp_path / "b.svg", tmp_path / "b.json"
    result = runner.invoke(
        app,
        ["badge", "Nike", "-t", "running shoes", "--demo", "-o", str(svg),
         "--endpoint", str(endpoint)],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    _parse(svg.read_text(encoding="utf-8"))
    _assert_valid_endpoint(json.loads(endpoint.read_text(encoding="utf-8")))
    assert "[![AI visibility]" in result.stderr


def test_cli_badge_and_card_from_saved_report(tmp_path):
    scan = runner.invoke(
        app, ["scan", "Nike", "-t", "running shoes", "-c", "Adidas", "--demo",
              "-f", "json"],
    )  # fmt: skip
    assert scan.exit_code == 0, scan.output
    report_file = tmp_path / "report.json"
    report_file.write_text(scan.stdout, encoding="utf-8")

    result = runner.invoke(
        app, ["badge", "--report", str(report_file), "-o", str(tmp_path / "b.svg")]
    )
    assert result.exit_code == 0, result.output

    result = runner.invoke(
        app,
        ["card", "--report", str(report_file), "-o", str(tmp_path / "c.svg"),
         "--theme", "both"],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    _parse((tmp_path / "c.svg").read_text(encoding="utf-8"))
    _parse((tmp_path / "c-dark.svg").read_text(encoding="utf-8"))


def test_cli_card_png(tmp_path):
    pytest.importorskip("PIL")
    result = runner.invoke(
        app,
        ["card", "Nike", "-t", "running shoes", "--demo", "-o", str(tmp_path / "c.svg"),
         "--png", str(tmp_path / "c.png")],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    assert (tmp_path / "c.png").read_bytes()[:4] == b"\x89PNG"


def test_cli_share_commands_need_a_brand_or_report():
    assert runner.invoke(app, ["badge"]).exit_code == 1
    assert runner.invoke(app, ["card"]).exit_code == 1
