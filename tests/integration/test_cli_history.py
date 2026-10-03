"""`promptbeacon scan` then `promptbeacon history` must show the scan."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from promptbeacon.cli.main import app
from promptbeacon.core.config import Provider, get_default_storage_path
from promptbeacon.providers.base import LLMResponse

runner = CliRunner()


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("PROMPTBEACON_HOME", str(tmp_path / "pb"))
    return tmp_path / "pb"


@pytest.fixture
def mocked_llm():
    response = LLMResponse(
        content="For running shoes I recommend Nike.",
        model="mock",
        provider="openai",
        latency_ms=1.0,
        cost_usd=0.001,
    )
    with (
        patch(
            "promptbeacon.beacon.get_available_providers",
            return_value=[Provider.OPENAI],
        ),
        patch(
            "promptbeacon.beacon.LiteLLMClient.complete",
            new_callable=AsyncMock,
            return_value=response,
        ),
    ):
        yield


def _history_points(brand: str) -> int:
    result = runner.invoke(app, ["history", brand, "-f", "json"])
    assert result.exit_code == 0, result.output
    return len(json.loads(result.stdout)["data_points"])


def test_default_storage_path_honours_promptbeacon_home(home):
    assert get_default_storage_path() == home / "data.db"


@pytest.mark.usefixtures("home", "mocked_llm")
def test_scan_then_history_shows_the_scan():
    result = runner.invoke(app, ["scan", "Nike", "-t", "running shoes", "-n", "2"])
    assert result.exit_code == 0, result.output
    assert "history" in result.stderr.lower()
    assert _history_points("Nike") == 1


@pytest.mark.usefixtures("mocked_llm")
def test_no_save_opts_out(home):
    result = runner.invoke(
        app, ["scan", "Nike", "-t", "running shoes", "-n", "2", "--no-save"]
    )
    assert result.exit_code == 0, result.output
    assert not (home / "data.db").exists()


def test_demo_scans_are_not_saved_by_default(home):
    result = runner.invoke(app, ["scan", "Nike", "-t", "running shoes", "--demo"])
    assert result.exit_code == 0, result.output
    assert not (home / "data.db").exists()


@pytest.mark.usefixtures("home")
def test_history_without_data_explains_how_to_get_some():
    result = runner.invoke(app, ["history", "Nike"])
    assert result.exit_code == 0, result.output
    assert "promptbeacon scan" in result.output
