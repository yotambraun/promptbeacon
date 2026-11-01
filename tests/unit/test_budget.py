"""--max-cost: estimate before, stop during, mark partial results (no real calls)."""

from __future__ import annotations

import json
from typing import Any

import pytest
from typer.testing import CliRunner

from promptbeacon import Beacon, Provider
from promptbeacon.budget import (
    BudgetExceededError,
    BudgetTracker,
    estimate_cost,
    format_usd,
    validate_max_cost,
)
from promptbeacon.cli.main import app
from promptbeacon.core.exceptions import ScanError
from promptbeacon.providers.base import BaseLLMClient, LLMResponse

PROMPTS = ["Which python http client would you recommend?"] * 10


class PricedClient(BaseLLMClient):
    """A fake live client that charges a fixed amount per request."""

    def __init__(self, provider: Provider, cost: float = 0.001):
        self.provider = provider
        self.cost = cost
        self.calls = 0

    @property
    def provider_name(self) -> str:
        return self.provider.value

    @property
    def model(self) -> str:
        return "gpt-6-luna"

    def is_available(self) -> bool:
        return True

    async def complete(self, prompt: str, **_kwargs: Any) -> LLMResponse:
        del prompt
        self.calls += 1
        return LLMResponse(
            content="httpx and requests are both good; httpx supports async.",
            model="gpt-6-luna",
            provider=self.provider.value,
            latency_ms=1.0,
            cost_usd=self.cost,
        )

    def complete_sync(self, _prompt: str, **_kwargs: Any) -> LLMResponse:
        raise NotImplementedError


def _live_beacon(monkeypatch, client: PricedClient, concurrency: int = 1) -> Beacon:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    beacon = (
        Beacon("httpx")
        .with_category("python http client")
        .with_competitors("requests")
        .with_providers(Provider.OPENAI)
    )
    beacon._config = beacon.config.model_copy(
        update={"concurrent_requests": concurrency}
    )
    monkeypatch.setattr(beacon, "_make_client", lambda _provider, **_kw: client)
    return beacon


# --- estimate ------------------------------------------------------------------


def test_estimate_prices_default_model_from_litellm_map():
    est = estimate_cost([(Provider.OPENAI, "gpt-6-luna")], PROMPTS)
    assert est.answers == 10 and est.requests == 10
    assert 0 < est.total_usd < est.upper_usd < 0.05
    assert est.lines[0].priced and not est.unpriced
    assert "LiteLLM" in est.assumptions


def test_estimate_scales_with_runs_providers_and_extras():
    one = estimate_cost([(Provider.OPENAI, "gpt-6-luna")], PROMPTS)
    more = estimate_cost(
        [(Provider.OPENAI, "gpt-6-luna"), (Provider.ANTHROPIC, "claude-haiku-5-5")],
        PROMPTS,
        runs=3,
        smart_extraction=True,
    )
    assert more.answers == 60
    assert more.requests == 120  # one extraction request per answer
    assert more.total_usd > 6 * one.total_usd


def test_unpriced_local_model_counts_as_zero_with_a_note():
    est = estimate_cost([(Provider.LITELLM, "ollama/llama3.2")], PROMPTS)
    assert est.total_usd == 0
    assert est.unpriced == ["ollama/llama3.2"]
    assert "counted as $0" in est.summary()


def test_perplexity_request_fee_is_included():
    est = estimate_cost([(Provider.PERPLEXITY, "sonar")], PROMPTS)
    assert "search fees" in est.lines[0].note
    assert est.total_usd > 10 * 0.001


def test_demo_estimate_is_zero():
    est = Beacon("httpx").with_category("python http client").demo().estimate_cost()
    assert est.demo and est.total_usd == 0
    assert est.summary().startswith("$0")


def test_validate_and_format():
    assert validate_max_cost(None) is None
    assert validate_max_cost(0.5) == 0.5
    for bad in (0, -1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            validate_max_cost(bad)
    assert format_usd(0) == "$0"
    assert format_usd(0.00321) == "$0.0032"
    assert format_usd(0.123) == "$0.123"
    assert format_usd(3.4) == "$3.40"


def test_tracker_stops_when_spend_plus_in_flight_reaches_cap():
    tracker = BudgetTracker(0.01)
    assert tracker.reserve(0.004)
    assert tracker.reserve(0.004)
    assert tracker.reserve(0.004)  # 0.008 committed < cap
    assert not tracker.reserve(0.004)  # 0.012 committed >= cap
    tracker.settle(0.004, 0.004)
    assert tracker.skipped == 1 and tracker.completed == 1


# --- during a scan --------------------------------------------------------------


def test_scan_refuses_when_estimate_is_above_cap(monkeypatch):
    client = PricedClient(Provider.OPENAI)
    beacon = _live_beacon(monkeypatch, client).with_max_cost(0.0001)
    with pytest.raises(BudgetExceededError) as info:
        beacon.scan()
    assert client.calls == 0
    message = str(info.value)
    assert "No request was sent" in message and "--prompts" in message
    assert info.value.estimate.total_usd > 0.0001


def test_scan_stops_at_cap_and_marks_result_partial(monkeypatch):
    client = PricedClient(Provider.OPENAI, cost=0.001)
    beacon = _live_beacon(monkeypatch, client).with_max_cost(0.004)
    report = beacon.scan()
    assert client.calls == 4
    assert len(report.provider_results) == 4
    assert report.partial
    budget = report.budget
    assert budget is not None
    assert budget.completed_answers == 4 and budget.skipped_answers == 6
    assert budget.planned_answers == 10 and budget.stopped_early
    assert budget.spent_usd == pytest.approx(0.004)
    assert report.total_cost_usd == pytest.approx(0.004)
    data = json.loads(report.model_dump_json())
    assert data["partial"] is True and data["budget"]["stopped_early"] is True


def test_scan_within_budget_is_not_partial(monkeypatch):
    client = PricedClient(Provider.OPENAI, cost=0.0001)
    report = _live_beacon(monkeypatch, client).with_max_cost(1.0).scan()
    assert client.calls == 10
    assert report.budget is not None and not report.partial
    assert report.budget.skipped_answers == 0


def test_concurrent_requests_overshoot_is_bounded(monkeypatch):
    client = PricedClient(Provider.OPENAI, cost=0.001)
    report = _live_beacon(monkeypatch, client, concurrency=5).with_max_cost(0.004)
    report = report.scan()
    # Requests already in flight finish; nothing new starts after the cap.
    assert report.partial
    assert client.calls <= 5


def test_stability_scan_keeps_complete_runs_only(monkeypatch):
    client = PricedClient(Provider.OPENAI, cost=0.001)
    beacon = (
        _live_beacon(monkeypatch, client)
        .with_prompt_count(2)
        .with_stability(3)
        .with_max_cost(0.005)
    )
    report = beacon.scan_stability()
    assert client.calls == 5  # runs 1 and 2 complete, run 3 cut short
    assert report.stability is not None and report.stability.runs == 2
    assert report.partial and report.budget.planned_answers == 6


def test_budget_used_up_before_any_answer_is_a_clear_error(monkeypatch):
    client = PricedClient(Provider.OPENAI)
    beacon = _live_beacon(monkeypatch, client).with_max_cost(1.0)
    beacon._start_budget()
    monkeypatch.setattr(beacon, "_start_budget", lambda _runs=1: None)
    assert beacon._budget is not None
    beacon._budget.spent = 1.0  # e.g. category inference used it all
    with pytest.raises(ScanError, match="budget was used up"):
        beacon.scan()


def test_demo_scan_with_cap_runs_and_reports_budget():
    report = (
        Beacon("httpx")
        .with_category("python http client")
        .demo()
        .with_max_cost(0.01)
        .scan()
    )
    assert report.budget is not None and not report.partial
    assert report.budget.estimated_cost_usd == 0


# --- CLI ------------------------------------------------------------------------


def test_cli_estimate_prints_json_and_sends_nothing(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")

    def boom(*_a, **_k):
        raise AssertionError("no request may be sent by --estimate")

    monkeypatch.setattr("promptbeacon.beacon.Beacon.scan", boom)
    result = CliRunner().invoke(
        app,
        ["scan", "httpx", "-t", "python http client", "-p", "openai", "-p",
         "anthropic", "--estimate", "--max-cost", "0.5", "-f", "json"],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["answers"] == 20
    assert {line["model"] for line in data["lines"]} == {
        "gpt-6-luna",
        "claude-haiku-5-5",
    }
    assert data["within_budget"] is True


def test_cli_estimate_text_mentions_budget():
    result = CliRunner().invoke(
        app,
        ["scan", "httpx", "-t", "python http client", "-m", "openai=gpt-6-luna",
         "--estimate", "--max-cost", "0.0001"],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    text = " ".join(result.stdout.split())
    assert "Nothing was sent" in text
    assert "would not start" in text


def test_cli_scan_refuses_over_budget(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    result = CliRunner().invoke(
        app,
        ["scan", "httpx", "-t", "python http client", "-p", "openai",
         "--max-cost", "0.0001", "--no-save"],
    )  # fmt: skip
    assert result.exit_code == 1
    assert "above the $0.0001 budget" in result.stderr
    assert "--max-cost" in result.stderr


def test_cli_partial_scan_is_marked(monkeypatch):
    client = PricedClient(Provider.OPENAI, cost=0.001)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    monkeypatch.setattr(
        "promptbeacon.beacon.Beacon._make_client",
        lambda _self, _provider, **_kw: client,
    )
    result = CliRunner().invoke(
        app,
        ["scan", "httpx", "-t", "python http client", "-p", "openai",
         "--max-cost", "0.003", "--no-save"],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    assert "PARTIAL: the $0.0030 budget was reached after" in " ".join(
        result.stdout.split()
    )


def test_cli_compare_badge_card_accept_max_cost(tmp_path):
    common = ["-t", "python http client", "--demo", "--max-cost", "0.01"]
    for args in (
        ["compare", "httpx", "-a", "requests", *common],
        ["badge", "httpx", *common, "-o", str(tmp_path / "b.svg")],
        ["card", "httpx", *common, "-o", str(tmp_path / "c.svg")],
        ["sources", "httpx", *common],
    ):
        result = CliRunner().invoke(app, args)
        assert result.exit_code == 0, (args, result.output)


def test_cli_rejects_non_positive_max_cost():
    result = CliRunner().invoke(
        app, ["scan", "httpx", "-t", "x", "--demo", "--max-cost", "0"]
    )
    assert result.exit_code == 2


def _report_file(tmp_path, cost: float | None, partial: bool = False):
    report = Beacon("httpx").with_category("python http client").demo().scan()
    report.total_cost_usd = cost
    if partial:
        from promptbeacon.core.schemas import BudgetReport

        report.budget = BudgetReport(
            max_cost_usd=0.01,
            estimated_cost_usd=0.008,
            spent_usd=0.01,
            planned_answers=10,
            completed_answers=6,
            skipped_answers=4,
        )
    path = tmp_path / "report.json"
    path.write_text(report.model_dump_json(), encoding="utf-8")
    return path


def test_ci_max_cost_gate(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    path = _report_file(tmp_path, 0.02)
    result = CliRunner().invoke(
        app, ["ci", "--report", str(path), "--max-cost", "0.01"]
    )
    assert result.exit_code == 1
    assert "cost $0.0200 > $0.01" in result.output
    ok = CliRunner().invoke(app, ["ci", "--report", str(path), "--max-cost", "0.05"])
    assert ok.exit_code == 0, ok.output


def test_ci_summary_and_outputs_mark_partial(tmp_path, monkeypatch):
    out = tmp_path / "out.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    path = _report_file(tmp_path, 0.01, partial=True)
    result = CliRunner().invoke(app, ["ci", "--report", str(path)])
    assert result.exit_code == 0, result.output
    assert "PARTIAL: the $0.010 budget was reached after 6 of 10 answers" in " ".join(
        result.stdout.split()
    )
    assert "partial=true" in out.read_text(encoding="utf-8")


async def test_mcp_scan_accepts_max_cost():
    from promptbeacon import mcp_server

    result = await mcp_server.scan(
        "httpx", category="python http client", demo=True, max_cost=0.01
    )
    assert result["partial"] is False
    assert result["budget"]["max_cost_usd"] == 0.01
