"""Prompts must be about the user's category — never "the best general brands"."""

from __future__ import annotations

import json
import warnings
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from promptbeacon import Beacon, Provider
from promptbeacon.analysis.category import build_category_prompt, parse_category
from promptbeacon.cli.main import app
from promptbeacon.providers.base import LLMResponse

runner = CliRunner()


def _prompts(report_json: str) -> list[str]:
    return [r["prompt"] for r in json.loads(report_json)["provider_results"]]


# --- library -----------------------------------------------------------------


def test_with_category_singular_builds_category_prompts():
    prompts = Beacon("Nike").with_category("running shoes")._get_prompts()
    assert prompts and all("running shoes" in p for p in prompts)


def test_report_records_category_and_strategy():
    report = Beacon("Nike").demo().with_category("running shoes").scan()
    assert report.categories == ["running shoes"]
    assert report.prompt_strategy == "category"


def test_no_category_with_competitors_uses_competitor_alternatives():
    beacon = Beacon("Nike").with_competitors("Adidas", "Puma")
    prompts = beacon._get_prompts()
    assert prompts
    assert not any("general" in p for p in prompts)
    assert any("Adidas" in p for p in prompts)
    assert any("Puma" in p for p in prompts)
    # The target brand is never named in its own prompts (that would bias it).
    assert not any("Nike" in p for p in prompts)
    assert len(prompts) == 10


def test_no_category_no_competitors_warns_clearly():
    with pytest.warns(UserWarning, match="category"):
        report = Beacon("Nike").demo().scan()
    assert report.prompt_strategy == "generic"


def test_explicit_category_does_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        Beacon("Nike").demo().with_category("running shoes").scan()


def test_category_inference_is_opt_in_and_used():
    calls: list[str] = []

    async def fake_complete(_self, prompt, **_kwargs):
        calls.append(prompt)
        if "product category" in prompt:
            return LLMResponse(
                content="Running shoes", model="m", provider="openai", latency_ms=1
            )
        return LLMResponse(
            content="Nike is great.", model="m", provider="openai", latency_ms=1
        )

    with (
        patch(
            "promptbeacon.beacon.get_available_providers",
            return_value=[Provider.OPENAI],
        ),
        patch("promptbeacon.beacon.LiteLLMClient.complete", new=fake_complete),
    ):
        report = Beacon("Nike").with_category_inference().with_prompt_count(2).scan()

    assert report.categories == ["running shoes"]
    assert report.prompt_strategy == "inferred_category"
    assert sum("product category" in c for c in calls) == 1  # exactly one extra call


def test_category_inference_never_runs_in_demo():
    with patch(
        "promptbeacon.beacon.LiteLLMClient.complete", new_callable=AsyncMock
    ) as complete:
        report = (
            Beacon("Nike")
            .demo()
            .with_competitors("Adidas")
            .with_category_inference()
            .scan()
        )
    complete.assert_not_called()
    assert report.prompt_strategy == "competitor_alternatives"


def test_parse_category_cleans_and_rejects():
    assert parse_category('"Running shoes."', brand="Nike") == "running shoes"
    assert parse_category("Category: CRM software", brand="Acme") == "crm software"
    assert parse_category("", brand="Nike") is None
    assert parse_category("Nike shoes", brand="Nike") is None  # names the brand
    assert parse_category("word " * 12, brand="Nike") is None  # not a category
    assert "Nike" in build_category_prompt("Nike", competitors=["Adidas"])


# --- demo CLI ----------------------------------------------------------------


def test_demo_uses_the_users_category():
    result = runner.invoke(
        app, ["demo", "Acme Widgets", "-t", "industrial widgets", "-f", "json"]
    )
    assert result.exit_code == 0, result.output
    prompts = _prompts(result.stdout)
    assert prompts and all("industrial widgets" in p for p in prompts)


def test_demo_never_injects_real_brands_as_competitors():
    result = runner.invoke(app, ["demo", "Acme Widgets", "-f", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert "Adidas" not in result.stdout and "Puma" not in result.stdout
    assert set(data["competitor_comparison"]) == {"Competitor A", "Competitor B"}
    assert "placeholder" in result.stderr.lower()


def test_demo_uses_the_users_competitors():
    result = runner.invoke(
        app, ["demo", "Acme Widgets", "-c", "Globex", "-t", "widgets", "-f", "json"]
    )
    assert result.exit_code == 0, result.output
    assert set(json.loads(result.stdout)["competitor_comparison"]) == {"Globex"}


def test_demo_text_prints_sources_once():
    result = runner.invoke(app, ["demo", "Nike", "-t", "running shoes"])
    assert result.exit_code == 0, result.output
    # Source domains appear in one table, not also as a duplicated raw list.
    assert "Sources Cited" not in result.stdout
    assert "Top Source Domains" in result.stdout


def test_scan_without_category_tells_the_user_how_to_fix_it():
    result = runner.invoke(app, ["scan", "Nike", "--demo"])
    assert result.exit_code == 0, result.output
    assert "--category" in result.stderr
