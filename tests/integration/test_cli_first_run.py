"""First-run polish: version, next steps, actionable errors (no real calls)."""

from __future__ import annotations

import logging

from typer.testing import CliRunner

from promptbeacon import __version__
from promptbeacon.cli.main import app


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_version_flag():
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == f"promptbeacon {__version__}"


def test_help_leads_with_demo_and_init():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    text = _flat(result.stdout)
    assert "library or dev product" in text
    assert "promptbeacon init" in text and "Start here" in text


def test_demo_ends_with_the_next_step():
    result = CliRunner().invoke(
        app, ["demo", "httpx", "-t", "python http client", "-c", "requests"]
    )
    assert result.exit_code == 0, result.output
    text = _flat(result.stderr)
    assert (
        "promptbeacon scan httpx -t 'python http client' -c requests --estimate" in text
    )
    assert "promptbeacon init" in text


def test_demo_json_output_has_no_footer():
    result = CliRunner().invoke(app, ["demo", "httpx", "-t", "x", "-f", "json"])
    assert result.exit_code == 0
    assert "Next:" not in result.stderr


def test_missing_key_error_points_to_cli_options():
    result = CliRunner().invoke(app, ["scan", "httpx", "-t", "python http client"])
    assert result.exit_code == 1
    text = _flat(result.stderr)
    assert "Add --demo for a keyless run" in text
    assert "Beacon(...)" not in text


def test_error_text_with_brackets_is_not_eaten_as_markup():
    from promptbeacon.cli.main import _esc

    assert (
        _esc("pip install 'promptbeacon[mcp]'") == "pip install 'promptbeacon\\[mcp]'"
    )


def test_library_warnings_are_shown_without_duplicating_cli_notices():
    result = CliRunner().invoke(app, ["scan", "httpx", "--demo", "-f", "json"])
    assert result.exit_code == 0
    text = _flat(result.stderr)
    assert "No --category given" in text  # the CLI's own explanation
    assert "No category set for" not in text  # the library's duplicate is dropped
    logging.getLogger("promptbeacon").warning("Models set for providers x")  # no crash
