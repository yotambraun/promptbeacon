"""The 1.4.0 MCP tools: estimate, compare, recommendations, history, funnel,
init_preview, and reusing a saved report. All in-process, with no real requests."""

from __future__ import annotations

import asyncio
import json
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from promptbeacon import Provider, mcp_server
from promptbeacon.core.clock import utc_now
from promptbeacon.providers.base import BaseLLMClient, LLMResponse
from promptbeacon.storage.database import Database

SMART_RECS = json.dumps(
    {
        "recommendations": [
            {
                "action": "Publish a migration guide from requests",
                "rationale": "requests is named in more answers",
                "priority": "high",
                "expected_impact": "More mentions in comparison prompts",
            }
        ]
    }
)


class FakeClient(BaseLLMClient):
    """A live client that answers every prompt without a network call."""

    def __init__(self) -> None:
        self.calls = 0

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return "gpt-6-luna"

    def is_available(self) -> bool:
        return True

    async def complete(self, prompt: str, **_kwargs: Any) -> LLMResponse:
        self.calls += 1
        content = (
            SMART_RECS
            if '"recommendations"' in prompt
            else "I recommend requests; httpx is also good and supports async."
        )
        return LLMResponse(
            content=content,
            model="gpt-6-luna",
            provider="openai",
            latency_ms=1.0,
            cost_usd=0.0001,
        )

    def complete_sync(self, _prompt: str, **_kwargs: Any) -> LLMResponse:
        raise NotImplementedError


@pytest.fixture
def live(monkeypatch):
    """A fake OpenAI key and a client that never leaves the process."""
    client = FakeClient()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    monkeypatch.setattr(
        "promptbeacon.beacon.Beacon._make_client",
        lambda _self, _provider, **_kw: client,
    )
    return client


@pytest.fixture
def in_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def run(coro):
    return asyncio.run(coro)


# --- registration --------------------------------------------------------------


def test_every_tool_describes_its_cost_and_arguments():
    pytest.importorskip("mcp")
    tools = {t.name: t for t in run(mcp_server.create_server().list_tools())}
    assert set(tools) == set(mcp_server.TOOLS)
    for name, tool in tools.items():
        assert "Free" in tool.description or "Cost:" in tool.description, name
        assert not tool.description.startswith(" "), name
        for arg, schema in tool.input_schema["properties"].items():
            assert schema.get("description"), f"{name}.{arg} has no description"
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint == mcp_server.TOOLS[name][1]


# --- estimate ------------------------------------------------------------------


def test_estimate_without_keys_is_zero_and_says_demo():
    result = run(mcp_server.estimate("httpx", category="python http client"))
    assert result["demo"] is True and result["total_usd"] == 0
    assert "demo" in result["note"]
    json.dumps(result)


def test_estimate_prices_a_live_scan_and_sends_nothing(live):
    result = run(
        mcp_server.estimate(
            "httpx", category="python http client", providers=["openai"],
            max_cost=0.000001,
        )
    )  # fmt: skip
    assert result["total_usd"] > 0 and result["answers"] == 10
    assert result["within_budget"] is False
    assert result["lines"][0]["model"] == "gpt-6-luna"
    assert live.calls == 0


# --- scan: saved reports and history -------------------------------------------


def test_real_scan_saves_history_and_report(live, in_tmp):
    result = run(
        mcp_server.scan(
            "httpx", category="python http client", competitors=["requests"],
            providers=["openai"], prompts=2, save_report="pb/report.json",
        )
    )  # fmt: skip
    assert live.calls == 2
    assert Path(result["saved_to_history"]).is_file()
    saved = json.loads((in_tmp / "pb" / "report.json").read_text(encoding="utf-8"))
    assert saved["brand"] == "httpx"
    history = mcp_server.history("httpx")
    assert history["scans"] == 1
    assert history["data_points"][0]["visibility_score"] == result["visibility_score"]


@pytest.mark.usefixtures("in_tmp")
def test_demo_scan_is_not_saved_to_history():
    result = run(mcp_server.scan("httpx", category="python http client"))
    assert result["measurement_tier"] == "demo"
    assert "saved_to_history" not in result
    assert mcp_server.history("httpx")["scans"] == 0


def test_save_report_must_stay_in_the_working_directory(in_tmp):
    with pytest.raises(ValueError, match="inside the working directory"):
        run(
            mcp_server.scan(
                "httpx", category="python http client",
                save_report=str(in_tmp.parent / "elsewhere.json"),
            )
        )  # fmt: skip


@pytest.fixture
def saved_report(in_tmp):
    del in_tmp  # the report is written in the temporary working directory
    run(
        mcp_server.scan(
            "httpx", category="python http client",
            competitors=["requests", "aiohttp"], save_report="report.json",
        )
    )  # fmt: skip
    return "report.json"


@pytest.fixture
def no_scans(monkeypatch, saved_report):
    """After saving the report, fail the test if a tool scans instead of reading it."""
    del saved_report

    def refuse(*_args, **_options):
        raise AssertionError("scanned instead of reading the report")

    monkeypatch.setattr(mcp_server, "configure_beacon", refuse)


# --- compare -------------------------------------------------------------------


@pytest.mark.usefixtures("no_scans")
def test_compare_from_a_saved_report_lists_every_brand(saved_report):
    result = run(mcp_server.compare(report_path=saved_report))
    brands = [row["brand"] for row in result["comparison"]]
    assert sorted(brands) == ["aiohttp", "httpx", "requests"]
    scores = [row["visibility_score"] for row in result["comparison"]]
    assert scores == sorted(scores, reverse=True)
    assert [r for r in result["comparison"] if r["is_target"]][0]["brand"] == "httpx"
    assert result["measurement_tier"] == "demo"
    json.dumps(result)


def test_compare_scans_when_there_is_no_report():
    result = run(
        mcp_server.compare(
            "httpx", competitors=["requests"], category="python http client"
        )
    )
    assert {r["brand"] for r in result["comparison"]} == {"httpx", "requests"}
    assert "demo" in result["note"]


def test_compare_needs_competitors_or_a_report():
    with pytest.raises(ValueError, match="competitors"):
        run(mcp_server.compare("httpx", category="python http client"))


# --- recommendations -----------------------------------------------------------


def test_recommendations_are_rule_based_by_default():
    result = run(
        mcp_server.recommendations(
            "UnknownLib", category="python http client", competitors=["requests"]
        )
    )
    assert result["generated_by"] == "rules"
    assert result["measurement_tier"] == "demo"
    for rec in result["recommendations"]:
        assert set(rec) >= {"action", "rationale", "priority", "expected_impact"}
    json.dumps(result)


@pytest.mark.usefixtures("no_scans")
def test_recommendations_from_a_saved_report(saved_report):
    result = run(mcp_server.recommendations(report_path=saved_report))
    assert result["generated_by"] == "saved report"
    assert result["brand"] == "httpx"


def test_smart_recommendations_use_the_existing_llm_path(live):
    result = run(
        mcp_server.recommendations(
            "httpx", category="python http client", providers=["openai"],
            prompts=2, smart=True,
        )
    )  # fmt: skip
    assert result["generated_by"].startswith("llm")
    assert result["recommendations"][0]["action"].startswith("Publish a migration")
    assert live.calls == 3  # two answers and one recommendations request


def test_smart_is_ignored_in_demo_mode():
    result = run(
        mcp_server.recommendations("httpx", category="python http client", smart=True)
    )
    assert result["generated_by"] == "rules"
    assert "smart is ignored" in result["note"]


def test_report_path_errors_are_clear(in_tmp):
    (in_tmp / "notes.json").write_text('{"hello": 1}', encoding="utf-8")
    with pytest.raises(ValueError, match="not a PromptBeacon JSON report"):
        run(mcp_server.recommendations(report_path="notes.json"))
    with pytest.raises(ValueError, match="does not exist"):
        run(mcp_server.compare(report_path="missing.json"))


# --- history -------------------------------------------------------------------


def test_history_without_a_file_says_so(tmp_path):
    result = mcp_server.history("httpx", storage=str(tmp_path / "none.db"))
    assert result["scans"] == 0 and "No history yet" in result["note"]
    assert not (tmp_path / "none.db").exists()


def test_history_reports_trend_change_and_significance(tmp_path, sample_report):
    path = tmp_path / "history.db"
    db = Database(path)
    start = utc_now() - timedelta(days=5)
    for i, score in enumerate([40.0, 42.0, 41.0, 70.0, 72.0, 71.0]):
        db.save_report(
            sample_report.model_copy(
                update={
                    "brand": "httpx",
                    "visibility_score": score,
                    "timestamp": start + timedelta(hours=i),
                }
            )
        )
    db.close()

    result = mcp_server.history("httpx", storage=str(path))
    assert result["scans"] == 6
    assert result["visibility_trend"] == [40.0, 42.0, 41.0, 70.0, 72.0, 71.0]
    assert result["trend_direction"] == "up"
    assert result["significance"]["compared"] == "first 3 vs last 3 scans"
    assert result["significance"]["is_significant"] is True
    assert result["latest_change"]["score_change"] == pytest.approx(-1.0)
    json.dumps(result)


# --- funnel --------------------------------------------------------------------


def test_funnel_without_tavily_uses_the_mock_backend_and_says_so():
    result = run(mcp_server.funnel("httpx", category="python http client"))
    assert result["backend"] == "mock" and result["demo"] is True
    assert "TAVILY_API_KEY" in result["note"]
    assert result["prompt"] == "What are the best python http client?"
    assert len(result["sub_query_results"]) == 8
    assert "snippet" not in result["sub_query_results"][0]["retrieved"][0]
    json.dumps(result)


def test_funnel_live_without_tavily_is_a_clear_error():
    with pytest.raises(ValueError, match="TAVILY_API_KEY"):
        run(mcp_server.funnel("httpx", category="python http client", demo=False))


def test_funnel_uses_tavily_when_the_key_is_set(monkeypatch):
    from promptbeacon.funnel.backends import SearchResult

    searches: list[str] = []

    async def fake_search(_self, query, max_results=8):
        del max_results
        searches.append(query)
        return [
            SearchResult(url="https://example.org/a", title="httpx guide", snippet="")
        ]

    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-not-real")
    monkeypatch.setattr("promptbeacon.funnel.TavilyBackend.search", fake_search)
    result = run(
        mcp_server.funnel("httpx", prompt="best python http client", sub_queries=3)
    )
    assert result["backend"] == "tavily" and result["demo"] is False
    assert "note" not in result
    assert len(searches) == 3


# --- init_preview ----------------------------------------------------------------


def _project(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        '[project]\nname = "fastq"\ndescription = "A fast task queue for Python"\n',
        encoding="utf-8",
    )


def test_init_preview_returns_the_plan_and_writes_nothing(tmp_path):
    _project(tmp_path)
    before = sorted(p.name for p in tmp_path.rglob("*"))
    result = mcp_server.init_preview(
        str(tmp_path), category="python task queue", competitors=["celery", "rq"]
    )
    assert sorted(p.name for p in tmp_path.rglob("*")) == before
    assert result["written"] == []
    assert result["category"] == "python task queue"
    assert result["files"][0]["path"] == ".github/workflows/ai-visibility.yml"
    assert result["files"][0]["status"] == "create"
    assert "yotambraun/promptbeacon@v1" in result["files"][0]["content"]
    assert result["command"].startswith("promptbeacon init --yes ")
    assert "--category 'python task queue'" in result["command"]
    assert "--competitor celery --competitor rq" in result["command"]
    json.dumps(result)


def test_init_preview_rejects_a_missing_directory(tmp_path):
    with pytest.raises(ValueError, match="not a directory"):
        mcp_server.init_preview(str(tmp_path / "nope"))


# --- share_assets from a saved report ----------------------------------------------


@pytest.mark.usefixtures("no_scans")
def test_share_assets_from_a_saved_report(saved_report, in_tmp):
    result = run(mcp_server.share_assets(report_path=saved_report, output_dir="out"))
    assert (in_tmp / "out" / "badge.svg").is_file()
    assert "rank_svg" in result["files"]  # two competitors and a category
    assert "demo" in result["note"].lower()


def test_providers_lists_tavily_and_litellm():
    result = mcp_server.providers()
    assert result["tavily"] is False
    assert Provider.LITELLM.value in result["models"]
