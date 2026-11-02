"""Regression gate: `promptbeacon ci --baseline report.json --max-drop POINTS`."""

from __future__ import annotations

from functools import lru_cache

import pytest
from typer.testing import CliRunner

from promptbeacon import Beacon
from promptbeacon.cli.main import app
from promptbeacon.core.schemas import Report
from promptbeacon.share.summary import baseline_changes, ci_outputs, summary_markdown


@lru_cache(maxsize=1)
def _base_json() -> str:
    report = (
        Beacon("Nike")
        .demo()
        .with_category("running shoes")
        .with_competitors("Adidas", "Hoka")
        .scan()
    )
    return report.model_dump_json()


def _report(score: float = 70.0, share: float = 0.4, presence: float = 0.8) -> Report:
    report = Report.model_validate_json(_base_json())
    report.visibility_score = score
    entry = report.share_of_voice.aggregate["Nike"]
    entry.share_of_voice = share
    entry.presence_rate = presence
    return report


def _write(tmp_path, name: str, report: Report):
    path = tmp_path / name
    path.write_text(report.model_dump_json(), encoding="utf-8")
    return str(path)


def ci(*args: str):
    return CliRunner().invoke(app, ["ci", *args])


class TestBaselineChanges:
    def test_changes_in_points(self):
        changes = baseline_changes(
            _report(score=58.5, share=0.30, presence=0.7), _report()
        )
        by_metric = {c.metric: c for c in changes}
        assert set(by_metric) == {"score", "share_of_voice", "presence"}
        assert by_metric["score"].change == pytest.approx(-11.5)
        assert by_metric["share_of_voice"].change == pytest.approx(-10.0)
        assert by_metric["presence"].change == pytest.approx(-10.0)
        assert by_metric["score"].describe() == (
            "visibility score dropped 11.5 points (70.0 → 58.5)"
        )
        assert by_metric["share_of_voice"].describe() == (
            "share of voice dropped 10.0 points (40% → 30%)"
        )

    def test_rise_and_no_change_are_described(self):
        changes = {c.metric: c for c in baseline_changes(_report(score=72), _report())}
        assert changes["score"].describe() == (
            "visibility score rose 2.0 points (70.0 → 72.0)"
        )
        assert changes["presence"].describe() == "presence unchanged (80%)"

    def test_stability_is_compared_when_both_have_it(self):
        current, baseline = _report(), _report()
        assert "stability" not in {
            c.metric for c in baseline_changes(current, baseline)
        }

    def test_summary_shows_the_change(self):
        changes = baseline_changes(_report(score=60), _report())
        md = summary_markdown(_report(score=60), baseline=changes)
        assert "Change vs baseline" in md
        assert "visibility score dropped 10.0 points (70.0 → 60.0)" in md

    def test_outputs_include_the_score_change(self):
        changes = baseline_changes(_report(score=60), _report())
        out = ci_outputs(_report(score=60), passed=False, baseline=changes)
        assert out["score-change"] == "-10.0"


class TestCiGate:
    def test_fails_on_a_drop_beyond_max_drop(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
        monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
        current = _write(tmp_path, "now.json", _report(score=60))
        base = _write(tmp_path, "base.json", _report(score=70))
        result = ci("--report", current, "--baseline", base, "--max-drop", "5")
        assert result.exit_code == 1
        assert "visibility score dropped 10.0 points (70.0 → 60.0)" in result.output
        assert "more than the allowed 5" in result.output

    def test_passes_within_max_drop(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
        monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
        current = _write(tmp_path, "now.json", _report(score=67, share=0.38))
        base = _write(tmp_path, "base.json", _report())
        result = ci("--report", current, "--baseline", base, "--max-drop", "5")
        assert result.exit_code == 0, result.output
        assert "Visibility check passed" in result.output
        assert "Change vs baseline" in result.stdout

    def test_share_of_voice_drop_fails_alone(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
        monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
        current = _write(tmp_path, "now.json", _report(share=0.25))
        base = _write(tmp_path, "base.json", _report())
        result = ci("--report", current, "--baseline", base, "--max-drop", "5")
        assert result.exit_code == 1
        assert "share of voice dropped 15.0 points (40% → 25%)" in result.output
        assert "visibility score" not in result.output.split("failed:")[-1]

    def test_baseline_alone_reports_without_gating(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
        monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
        current = _write(tmp_path, "now.json", _report(score=10))
        base = _write(tmp_path, "base.json", _report())
        result = ci("--report", current, "--baseline", base)
        assert result.exit_code == 0
        assert "visibility score dropped 60.0 points" in result.stdout

    def test_max_drop_needs_a_baseline(self, tmp_path):
        current = _write(tmp_path, "now.json", _report())
        result = ci("--report", current, "--max-drop", "5")
        assert result.exit_code == 1
        assert "--baseline" in result.output

    def test_baseline_for_another_brand_is_an_error(self, tmp_path):
        other = _report()
        other.brand = "Adidas"
        current = _write(tmp_path, "now.json", _report())
        base = _write(tmp_path, "base.json", other)
        result = ci("--report", current, "--baseline", base, "--max-drop", "5")
        assert result.exit_code == 1
        assert "Adidas" in result.output and "Nike" in result.output

    def test_warns_when_the_measurement_differs(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
        monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
        other = _report()
        other.categories = ["trail shoes"]
        current = _write(tmp_path, "now.json", _report())
        base = _write(tmp_path, "base.json", other)
        result = ci("--report", current, "--baseline", base, "--max-drop", "5")
        assert result.exit_code == 0
        assert "not directly comparable" in result.output
        assert "categories" in result.output

    def test_github_outputs(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "out"))
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary"))
        current = _write(tmp_path, "now.json", _report(score=60))
        base = _write(tmp_path, "base.json", _report())
        ci("--report", current, "--baseline", base, "--max-drop", "5")
        out = (tmp_path / "out").read_text()
        assert "score-change=-10.0" in out and "passed=false" in out
        assert "max drop 5" in (tmp_path / "summary").read_text()
