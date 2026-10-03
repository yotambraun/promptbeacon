"""Machine-readable CLI output must be clean, parseable stdout.

Banners, spinners and notices go to stderr; ``--format json`` (and the other
machine formats) write exactly one document to stdout, never wrapped at the
terminal width.
"""

from __future__ import annotations

import csv
import io
import json

import pytest
from typer.testing import CliRunner

from promptbeacon.cli.main import app

runner = CliRunner()

# A long brand name makes Rich-style wrapping at 80 columns observable.
LONG_BRAND = "Acme Widgets International Holdings Of Exceptionally Long Names"


@pytest.mark.integration
class TestMachineOutput:
    def test_demo_json_is_valid_json_on_stdout(self):
        result = runner.invoke(app, ["demo", "Acme Widgets", "-f", "json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.stdout)
        assert data["brand"] == "Acme Widgets"

    def test_demo_json_long_lines_are_not_wrapped(self):
        result = runner.invoke(app, ["demo", LONG_BRAND, "-f", "json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.stdout)
        assert data["brand"] == LONG_BRAND

    def test_scan_demo_json_is_valid_json_on_stdout(self):
        result = runner.invoke(
            app,
            [
                "scan",
                LONG_BRAND,
                "--demo",
                "-c",
                "Globex",
                "-t",
                "widgets",
                "-f",
                "json",
            ],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.stdout)
        assert data["brand"] == LONG_BRAND
        assert data["visibility_score"] >= 0

    def test_scan_demo_json_with_assertion_keeps_stdout_clean(self):
        result = runner.invoke(
            app,
            ["scan", "Nike", "--demo", "-f", "json", "--assert-min-score", "0"],
        )
        assert result.exit_code == 0, result.output
        json.loads(result.stdout)

    def test_sources_demo_json_is_valid(self):
        result = runner.invoke(app, ["sources", "Nike", "--demo", "-f", "json"])
        assert result.exit_code == 0, result.output
        json.loads(result.stdout)

    def test_funnel_demo_json_is_valid(self):
        result = runner.invoke(
            app, ["funnel", "Nike", "-t", "running shoes", "--demo", "-f", "json"]
        )
        assert result.exit_code == 0, result.output
        json.loads(result.stdout)

    def test_demo_markdown_goes_to_stdout_without_banner(self):
        result = runner.invoke(app, ["demo", "Nike", "-f", "markdown"])
        assert result.exit_code == 0, result.output
        assert result.stdout.lstrip().startswith("#")
        assert "DEMO mode" not in result.stdout

    def test_demo_csv_format_parses(self):
        result = runner.invoke(app, ["demo", "Nike", "-f", "csv"])
        assert result.exit_code == 0, result.output
        rows = list(csv.reader(io.StringIO(result.stdout)))
        assert rows and rows[0]

    def test_demo_html_format(self):
        result = runner.invoke(app, ["demo", "Nike", "-f", "html"])
        assert result.exit_code == 0, result.output
        assert result.stdout.lstrip().lower().startswith("<!doctype html")
