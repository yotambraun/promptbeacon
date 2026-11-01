"""Score sparklines on share cards: real data only, from history or a file."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import pytest
from typer.testing import CliRunner

from promptbeacon import Beacon
from promptbeacon.cli.main import app
from promptbeacon.core.schemas import Report
from promptbeacon.share import card_data, render_card_png, render_card_svg
from promptbeacon.share.card import _sparkline
from promptbeacon.share.trend import (
    TrendPoint,
    history_points,
    load_trend_file,
    trend_values,
    update_trend_file,
)
from promptbeacon.storage.database import Database

SVG = "{http://www.w3.org/2000/svg}"


def _demo() -> Report:
    return (
        Beacon("httpx")
        .demo()
        .with_category("python http client")
        .with_competitors("requests", "aiohttp")
        .scan()
    )


def _real(score: float = 60.0, when: datetime | None = None, tier="base_model"):
    report = _demo().model_copy(deep=True)
    report.measurement_tier = tier
    report.visibility_score = score
    if when is not None:
        report.timestamp = when
    return report


def _polylines(svg: str):
    return ET.fromstring(svg).findall(f".//{SVG}polyline")


# --- rendering -----------------------------------------------------------------


def test_card_draws_a_sparkline_with_three_real_points():
    svg = render_card_svg(_real(62), trend=[40, 55, 62])
    lines = _polylines(svg)
    assert len(lines) == 1
    points = lines[0].get("points").split()
    assert len(points) == 3
    ys = [float(p.split(",")[1]) for p in points]
    assert ys[0] > ys[1] > ys[2]  # rising scores are drawn higher (smaller y)
    texts = [t.text for t in ET.fromstring(svg).iter(f"{SVG}text")]
    assert "Score, last 3 scans" in texts and "62" in texts
    title = ET.fromstring(svg).find(f"{SVG}title").text
    assert "Visibility score over the last 3 scans: 40, 55, 62." in title


def test_sparkline_stays_inside_the_card_and_away_from_the_pill():
    svg = render_card_svg(_real(62), theme="dark", trend=list(range(10, 100, 7)))
    xs = [float(p.split(",")[0]) for p in _polylines(svg)[0].get("points").split()]
    assert min(xs) > 300 and max(xs) < 1000
    assert len(xs) == 13  # card_data keeps what it is given; the CLI caps at 12


def test_fewer_than_three_points_or_demo_draw_nothing():
    assert _polylines(render_card_svg(_real(), trend=[50, 60])) == []
    assert _polylines(render_card_svg(_real(), trend=None)) == []
    assert _polylines(render_card_svg(_demo(), trend=[40, 50, 60])) == []
    assert card_data(_demo(), trend=[40, 50, 60]).trend == []


def test_flat_and_noisy_series_are_not_exaggerated():
    flat = _sparkline([50, 50, 50], 0, 0, 100, 30)
    assert len({y for _, y in flat}) == 1
    noisy = _sparkline([50, 52, 51], 0, 0, 100, 30)
    spread = max(y for _, y in noisy) - min(y for _, y in noisy)
    assert spread <= 30 * 2 / 10 + 0.1  # a 2-point move uses a fifth of the box


def test_png_renders_with_a_trend():
    pytest.importorskip("PIL")
    data = render_card_png(_real(62), trend=[40, 55, 62], scale=1)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


# --- data sources --------------------------------------------------------------


def test_trend_values_need_three_comparable_real_points():
    now = datetime(2026, 10, 1)
    points = [
        TrendPoint(now, 40, "base_model", ["python http client"]),
        TrendPoint(now + timedelta(days=7), 45, "api_grounded", ["python http client"]),
        TrendPoint(now + timedelta(days=14), 50, "base_model", ["other category"]),
        TrendPoint(now + timedelta(days=21), 55, "demo", ["python http client"]),
        TrendPoint(now + timedelta(days=28), 58, "base_model", ["python http client"]),
    ]
    report = _real(62, now + timedelta(days=35))
    assert trend_values(points, report) == [40, 58, 62]
    assert trend_values(points[:1], report) is None
    assert trend_values(points, _demo()) is None


def test_trend_file_round_trip_skips_demo_and_duplicates(tmp_path):
    path = tmp_path / ".promptbeacon" / "trend.json"
    start = datetime(2026, 10, 1)
    for i in range(3):
        update_trend_file(path, _real(50 + i, start + timedelta(days=7 * i)))
    update_trend_file(path, _real(52, start + timedelta(days=14)))  # same scan again
    update_trend_file(path, _demo())  # never added
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == 1 and data["brand"] == "httpx"
    assert [p["score"] for p in data["points"]] == [50, 51, 52]
    assert all(p["tier"] == "base_model" for p in data["points"])
    assert len(load_trend_file(path)) == 3


def test_bad_trend_file_is_a_clear_error(tmp_path):
    path = tmp_path / "trend.json"
    path.write_text('{"points": [{"nope": 1}]}', encoding="utf-8")
    with pytest.raises(ValueError, match="not a PromptBeacon trend file"):
        load_trend_file(path)


def test_history_database_records_tier_and_feeds_the_trend(tmp_path):
    db_path = tmp_path / "data.db"
    db = Database(db_path)
    start = datetime(2026, 10, 1)
    for i, tier in enumerate(["base_model", "demo", "base_model", "base_model"]):
        db.save_report(_real(40 + 5 * i, start + timedelta(days=i), tier=tier))
    db.close()
    report = _real(70, start + timedelta(days=10))
    assert [p.score for p in history_points(db_path, report)] == [40, 50, 55]
    assert trend_values(history_points(db_path, report), report) == [40, 50, 55, 70]
    assert history_points(tmp_path / "missing.db", report) == []


def test_old_history_files_gain_the_new_columns(tmp_path):
    import duckdb

    db_path = tmp_path / "old.db"
    conn = duckdb.connect(str(db_path))
    conn.execute(
        "CREATE TABLE scans (id VARCHAR PRIMARY KEY, brand VARCHAR NOT NULL, "
        "timestamp TIMESTAMP NOT NULL, visibility_score DOUBLE NOT NULL, "
        "mention_count INTEGER NOT NULL, sentiment_positive DOUBLE, "
        "sentiment_neutral DOUBLE, sentiment_negative DOUBLE, "
        "scan_duration_seconds DOUBLE, total_cost_usd DOUBLE, "
        "providers_used VARCHAR[], created_at TIMESTAMP)"
    )
    conn.execute(
        "INSERT INTO scans VALUES ('a', 'httpx', '2026-09-01', 50, 3, 0, 0, 0, 1, "
        "NULL, ['openai'], NULL)"
    )
    conn.close()
    db = Database(db_path)
    db.save_report(_real(60))
    db.close()
    # The pre-1.4.0 row has no tier, so it is not part of the trend.
    assert [p.score for p in history_points(db_path, _real(70))] == [60]


# --- CLI -----------------------------------------------------------------------


def test_cli_card_with_trend_file(tmp_path):
    trend = tmp_path / "trend.json"
    start = datetime(2026, 10, 1)
    outputs = []
    for i in range(3):
        report = tmp_path / f"r{i}.json"
        report.write_text(
            _real(50 + 5 * i, start + timedelta(days=7 * i)).model_dump_json(),
            encoding="utf-8",
        )
        out = tmp_path / f"card{i}.svg"
        result = CliRunner().invoke(
            app,
            ["card", "--report", str(report), "-o", str(out), "--trend", str(trend)],
        )
        assert result.exit_code == 0, result.output
        outputs.append((out.read_text(encoding="utf-8"), result.stderr))
    assert _polylines(outputs[0][0]) == [] and "No trend yet" in outputs[0][1]
    assert _polylines(outputs[1][0]) == []
    assert len(_polylines(outputs[2][0])) == 1
    assert "Trend: the last 3" in outputs[2][1]


def test_cli_card_reads_local_history_and_no_trend_disables(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("PROMPTBEACON_HOME", str(home))
    db = Database(home / "data.db")
    start = datetime(2026, 10, 1)
    for i in range(2):
        db.save_report(_real(50 + i, start + timedelta(days=i)))
    db.close()
    report = tmp_path / "r.json"
    report.write_text(_real(60, start + timedelta(days=5)).model_dump_json(), "utf-8")
    out = tmp_path / "card.svg"
    result = CliRunner().invoke(app, ["card", "--report", str(report), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert len(_polylines(out.read_text(encoding="utf-8"))) == 1
    result = CliRunner().invoke(
        app, ["card", "--report", str(report), "-o", str(out), "--no-trend"]
    )
    assert _polylines(out.read_text(encoding="utf-8")) == []


def test_cli_demo_card_never_has_a_trend(tmp_path):
    out = tmp_path / "card.svg"
    trend = tmp_path / "trend.json"
    result = CliRunner().invoke(
        app,
        ["card", "httpx", "-t", "python http client", "--demo", "-o", str(out),
         "--trend", str(trend)],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    assert not trend.exists()
    assert _polylines(out.read_text(encoding="utf-8")) == []
