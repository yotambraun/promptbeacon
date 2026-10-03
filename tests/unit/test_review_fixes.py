"""Regression tests for issues found in review of the 1.3.0 branch."""

from __future__ import annotations

import json
import warnings
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from promptbeacon import Beacon, Provider
from promptbeacon.cli.main import app
from promptbeacon.providers.base import LLMResponse
from promptbeacon.share import card_data, render_card_svg
from promptbeacon.share.summary import ci_outputs, summary_markdown

runner = CliRunner()


@pytest.fixture
def mocked_llm():
    resp = LLMResponse(
        content="For running shoes I recommend Nike.",
        model="m",
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
            return_value=resp,
        ),
    ):
        yield


@pytest.mark.usefixtures("mocked_llm")
def test_unwritable_history_does_not_lose_a_paid_scan(tmp_path, monkeypatch):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setenv("PROMPTBEACON_HOME", str(blocker / "sub"))  # cannot mkdir
    result = runner.invoke(
        app, ["scan", "Nike", "-t", "shoes", "-n", "2", "-f", "json"]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["brand"] == "Nike"
    assert "could not save" in result.stderr.lower()


@pytest.mark.usefixtures("mocked_llm")
def test_no_save_wins_over_storage(tmp_path):
    db = tmp_path / "h.db"
    result = runner.invoke(
        app,
        ["scan", "Nike", "-t", "shoes", "-n", "2", "--storage", str(db), "--no-save"],
    )
    assert result.exit_code == 0, result.output
    assert not db.exists()
    assert "Saved to history" not in result.stderr


def test_explicit_custom_prompts_are_respected_with_competitors():
    beacon = (
        Beacon("Nike")
        .with_competitors("Adidas")
        .with_prompts(["Which {category} is best?"])
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        prompts, strategy = beacon._prompt_plan()
    assert prompts == ["Which general is best?"]
    assert strategy == "generic"


@pytest.mark.filterwarnings("error::UserWarning")
@pytest.mark.visibility(brand="Nike", demo=True, min_score=0)
def test_pytest_plugin_does_not_warn_without_category():
    """Projects with filterwarnings=error must not fail on category-less markers."""


def test_inference_cost_is_not_double_counted():
    async def fake(_self, prompt, **_kw):
        if "product category" in prompt:
            return LLMResponse(content="running shoes", model="m", provider="openai",
                               latency_ms=1, cost_usd=0.5)  # fmt: skip
        return LLMResponse(content="Nike", model="m", provider="openai", latency_ms=1,
                           cost_usd=0.01)  # fmt: skip

    with (
        patch(
            "promptbeacon.beacon.get_available_providers",
            return_value=[Provider.OPENAI],
        ),
        patch("promptbeacon.beacon.LiteLLMClient.complete", new=fake),
    ):
        beacon = Beacon("Nike").with_category_inference().with_prompt_count(2)
        first = beacon.scan()
        second = beacon.scan()
    assert first.total_cost_usd == pytest.approx(0.52)
    assert second.total_cost_usd == pytest.approx(0.02)


def _report_without_target():
    report = (
        Beacon("Nike").demo().with_category("shoes").with_competitors("Adidas").scan()
    )
    report.share_of_voice.aggregate.pop("Nike")
    return report


def test_card_and_summary_survive_reports_missing_the_target():
    report = _report_without_target()
    assert any(r.is_target for r in card_data(report).rows)
    render_card_svg(report)
    summary_markdown(report)


def test_ci_outputs_never_contain_newlines():
    report = Beacon("Nike").demo().with_category("shoes").scan()
    report.categories = ["shoes\npassed=true"]
    assert all("\n" not in v for v in ci_outputs(report).values())


def test_svg_strips_characters_invalid_in_xml():
    import xml.etree.ElementTree as ET

    from promptbeacon.share.text import xml

    brand = "Nike" + chr(0xFFFE) + chr(7)
    report = Beacon(brand).demo().with_category("shoes").scan()
    ET.fromstring(render_card_svg(report))
    assert xml("a" + chr(0xD800) + "b" + chr(0xFFFF) + "c") == "abc"


def test_mcp_share_assets_stays_under_working_directory(tmp_path, monkeypatch):
    import asyncio

    from promptbeacon import mcp_server

    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="working directory"):
        asyncio.run(
            mcp_server.share_assets(
                "Nike", category="shoes", demo=True, output_dir="/etc/x"
            )
        )
