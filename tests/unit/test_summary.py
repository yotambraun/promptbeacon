"""CI summary / outputs / PR comment content."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from promptbeacon import Beacon
from promptbeacon.cli.main import app
from promptbeacon.share.summary import COMMENT_MARKER, ci_outputs, summary_markdown


def _report(competitors=("Adidas", "Hoka")):
    return (
        Beacon("Nike")
        .demo()
        .with_category("running shoes")
        .with_competitors(*competitors)
        .scan()
    )


def test_outputs_are_strings_with_expected_keys():
    out = ci_outputs(_report(), passed=True)
    assert set(out) >= {"score", "share-of-voice", "rank", "presence", "tier", "passed"}
    assert all(isinstance(v, str) and "\n" not in v for v in out.values())
    assert out["passed"] == "true"


def test_summary_escapes_markdown_in_names():
    report = _report(competitors=["A|B <script>", "C*D_"])
    md = summary_markdown(report)
    assert "A\\|B \\<script\\>" in md
    assert "<script>" not in md


def test_summary_limits_rows_and_keeps_target():
    report = _report(competitors=[f"Rival {i}" for i in range(15)])
    report.share_of_voice.aggregate["Nike"].appearances = 0
    md = summary_markdown(report, max_rows=5)
    assert "**Nike**" in md
    assert "more |" in md


def test_comment_has_marker_and_failures():
    md = summary_markdown(
        _report(), failures=["visibility_score 10 < 50"], thresholds={"min score": 50},
        marker=True,
    )  # fmt: skip
    assert md.startswith(COMMENT_MARKER)
    assert "**Failed**" in md and "visibility\\_score 10 \\< 50" in md


def test_ci_command_writes_github_files(tmp_path, monkeypatch):
    report_file = tmp_path / "r.json"
    report_file.write_text(_report().model_dump_json(), encoding="utf-8")
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "out"))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary"))
    result = CliRunner().invoke(
        app, ["ci", "--report", str(report_file), "--min-score", "101",
              "--comment-file", str(tmp_path / "c.md")],
    )  # fmt: skip
    assert result.exit_code == 1
    assert "passed=false" in (tmp_path / "out").read_text()
    assert "AI visibility: Nike" in (tmp_path / "summary").read_text()
    assert (tmp_path / "c.md").read_text().startswith(COMMENT_MARKER)


def test_ci_command_prints_summary_outside_github(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    report_file = tmp_path / "r.json"
    report_file.write_text(json.dumps(json.loads(_report().model_dump_json())))
    result = CliRunner().invoke(app, ["ci", "--report", str(report_file)])
    assert result.exit_code == 0
    assert "### AI visibility: Nike" in result.stdout
