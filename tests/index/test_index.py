"""The AI Recommendation Index generator, end to end in demo mode ($0)."""

from __future__ import annotations

import asyncio
import json
import re
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from pbindex.__main__ import main
from pbindex.protocol import Candidate, IndexProtocol, load_protocols
from pbindex.ranking import Answer, find_mentions, rank_projects
from pbindex.runner import (
    IndexBudgetError,
    estimate,
    missing_keys,
    run_index,
)
from pbindex.site import build_site, latest_snapshots
from promptbeacon.analysis.statistics import proportion_interval
from promptbeacon.core.config import Provider
from promptbeacon.providers.base import BaseLLMClient, LLMResponse

DAY = date(2026, 11, 1)


@pytest.fixture(scope="module")
def protocols() -> list[IndexProtocol]:
    return load_protocols()


def _proto(**kw: Any) -> IndexProtocol:
    base: dict[str, Any] = {
        "schema": 1,
        "id": "python-http-client",
        "category": "python http client",
        "candidates": [
            {"name": "aiohttp", "url": "u"},
            {"name": "httpx", "url": "u"},
            {
                "name": "requests",
                "url": "u",
                "match": ["Requests", "`requests`"],
                "case_sensitive": True,
            },
        ],  # fmt: skip
        "prompts": ["What is the best python http client?", "Which one?"],
        "providers": {"openai": "gpt-6-luna", "anthropic": "claude-haiku-5-5"},
        "runs": 2,
    }
    base.update(kw)
    return IndexProtocol.model_validate(base)


# --- protocols -------------------------------------------------------------------


def test_thirty_valid_pinned_protocols(protocols):
    assert len(protocols) == 30
    for p in protocols:
        assert len(p.prompts) == 10 and p.runs == 3
        assert p.tier == "base_model"
        assert p.providers == {
            "openai": "gpt-6-luna",
            "anthropic": "claude-haiku-5-5",
            "google": "gemini-3.5-flash-lite",
        }
        assert all(p.category in prompt for prompt in p.prompts)
        assert 4 <= len(p.candidates) <= 9
        assert len(p.fingerprint()) == 64


def test_candidates_must_be_alphabetical_and_unique():
    with pytest.raises(ValueError, match="alphabetical"):
        _proto(candidates=[{"name": "b", "url": "u"}, {"name": "a", "url": "u"},
                           {"name": "c", "url": "u"}])  # fmt: skip
    with pytest.raises(ValueError, match="duplicate"):
        _proto(candidates=[{"name": "a", "url": "u"}, {"name": "A", "url": "u"},
                           {"name": "c", "url": "u"}])  # fmt: skip
    with pytest.raises(ValueError, match="at least 3"):
        _proto(candidates=[{"name": "a", "url": "u"}, {"name": "b", "url": "u"}])
    with pytest.raises(ValueError):
        _proto(providers={"nope": "x"})


def test_unknown_category_is_a_clear_error():
    with pytest.raises(ValueError, match="Unknown categories: nope"):
        load_protocols(only=["nope"])


# --- matching and ranking ----------------------------------------------------------


def test_whole_word_and_case_sensitive_matching():
    cands = _proto().candidates
    text = (
        "Use httpx for async. HTTP requests are easy; Requests is the classic. "
        "aiohttp-session is a plugin."
    )
    assert find_mentions(text, cands) == ["httpx", "requests"]
    assert find_mentions("httpxx and the requests module", cands) == []
    assert find_mentions("pip install `requests`", cands) == ["requests"]


def test_every_protocol_matches_its_own_candidate_names(protocols):
    for p in protocols:
        for c in p.candidates:
            assert find_mentions(f"I recommend {c.terms[0]} here.", [c]) == [c.name]


def test_ranking_rates_intervals_ties_and_overlap():
    cands = [Candidate(name=n, url="u") for n in ("a", "b", "c")]
    answers = []
    for i in range(10):
        mentions = ["a"] + (["b"] if i < 8 else []) + (["c"] if i < 8 else [])
        answers.append(Answer("openai", "m", 0, i, "q", "t", mentions=mentions))
    answers.append(Answer("openai", "m", 0, 10, "q", error="APIError: boom"))
    results = rank_projects(answers, cands)
    assert [(r.name, r.rank, r.tied) for r in results] == [
        ("a", 1, False),
        ("b", 2, True),
        ("c", 2, True),
    ]
    assert results[0].answers == 10 and results[0].rate == 1.0  # failures excluded
    assert (results[0].ci_low, results[0].ci_high) == proportion_interval(10, 10)
    assert results[0].overlaps_next  # 10/10 vs 8/10 is not statistically clear
    assert results[1].by_provider["openai"]["mentions"] == 8


def test_wilson_interval():
    assert proportion_interval(0, 0) == (0.0, 1.0)
    low, high = proportion_interval(0, 30)
    assert low == 0.0 and 0.1 < high < 0.13
    low, high = proportion_interval(15, 30)
    assert low < 0.5 < high and abs((0.5 - low) - (high - 0.5)) < 1e-3
    with pytest.raises(ValueError):
        proportion_interval(5, 3)


# --- cost and budget -----------------------------------------------------------------


def test_monthly_estimate_uses_promptbeacon_prices(protocols):
    priced = estimate(protocols)
    total = sum(e.total_usd for _, e in priced)
    assert sum(e.answers for _, e in priced) == 2700
    assert 0 < total < 10
    assert all(not e.unpriced for _, e in priced)


def test_live_run_needs_a_cap_and_refuses_over_budget(tmp_path):
    proto = _proto()
    with pytest.raises(IndexBudgetError, match="need --max-cost"):
        asyncio.run(run_index([proto], tmp_path, demo=False, max_cost=None))
    with pytest.raises(IndexBudgetError, match="nothing was sent"):
        asyncio.run(run_index([proto], tmp_path, demo=False, max_cost=1e-9))
    assert not any(tmp_path.iterdir())


class _PricedClient(BaseLLMClient):
    def __init__(self, provider: Provider):
        self.provider = provider

    @property
    def provider_name(self) -> str:
        return self.provider.value

    @property
    def model(self) -> str:
        return "m"

    def is_available(self) -> bool:
        return True

    async def complete(self, prompt: str, **_kw: Any) -> LLMResponse:
        del prompt
        return LLMResponse(
            content="I like httpx and Requests.",
            model="m",
            provider=self.provider.value,
            latency_ms=1,
            cost_usd=0.001,
        )

    def complete_sync(self, _prompt: str, **_kw: Any) -> LLMResponse:
        raise NotImplementedError


def test_live_run_stops_at_the_cap_and_marks_partial(tmp_path):
    proto = _proto()
    logs: list[str] = []
    paths = asyncio.run(
        run_index(
            [proto],
            tmp_path,
            demo=False,
            max_cost=0.003,
            day=DAY,
            concurrency=1,
            client_factory=lambda provider, *_a: _PricedClient(provider),
            log=logs.append,
        )
    )
    snap = json.loads(paths[0].read_text(encoding="utf-8"))
    assert snap["partial"] is True and snap["demo"] is False
    assert snap["answers"] < snap["planned_answers"] == 8
    assert snap["answers"] + snap["skipped_answers"] == 8
    assert "partial" in logs[0]


def test_missing_keys_lists_providers(protocols):
    assert missing_keys(protocols[:1]) == ["anthropic", "google", "openai"]


# --- demo end to end ---------------------------------------------------------------


@pytest.fixture(scope="module")
def demo_site(tmp_path_factory, protocols):
    root = tmp_path_factory.mktemp("index")
    chosen = [p for p in protocols if p.id in ("python-http-client", "vector-database")]
    asyncio.run(run_index(chosen, root / "data", demo=True, max_cost=None, day=DAY,
                          log=lambda _m: None))  # fmt: skip
    build_site(
        root / "data", root / "site", protocols, base_url="https://example.org/index"
    )
    return root


def test_demo_run_uses_placeholders_and_records_everything(demo_site, protocols):
    snap = json.loads(
        (demo_site / "data/2026-11-01/python-http-client.json").read_text("utf-8")
    )
    assert snap["demo"] is True and "DEMO DATA" in snap["note"]
    assert snap["answers"] == snap["planned_answers"] == 90
    assert snap["cost_usd"] == 0
    names = {r["name"] for r in snap["results"]}
    assert all(n.startswith("Project ") for n in names)
    real = {c.name for p in protocols for c in p.candidates}
    assert not names & real
    raw = (demo_site / "data/2026-11-01/raw/python-http-client.jsonl").read_text(
        "utf-8"
    )
    lines = [json.loads(line) for line in raw.splitlines()]
    assert len(lines) == 90 and {"text", "mentions", "provider", "run"} <= set(lines[0])
    ranks = [r["rank"] for r in snap["results"]]
    assert ranks == sorted(ranks)


def test_demo_site_pages_are_labelled_and_link_their_data(demo_site):
    site = demo_site / "site"
    for page in ["index.html", "methodology.html", "categories/vector-database.html"]:
        text = (site / page).read_text(encoding="utf-8")
        assert "DEMO DATA" in text
        assert '<meta name="robots" content="noindex">' in text
        assert "<title>[DEMO]" in text
    cat = (site / "categories/python-http-client.html").read_text(encoding="utf-8")
    assert "Which python http client do AI assistants recommend?" in cat
    assert 'href="../raw/python-http-client.jsonl"' in cat
    assert 'href="../data/python-http-client.json"' in cat
    assert "95% interval" in cat and "gpt-6-luna" in cat
    assert "https%3A%2F%2Fexample.org%2Findex%2Fbadges%2Fpython-http-client" in cat
    assert (site / "raw/python-http-client.jsonl").exists()
    overview = (site / "index.html").read_text(encoding="utf-8")
    assert 'href="categories/vector-database.html"' in overview


def test_methodology_has_prompts_limits_disputes_and_cost(demo_site):
    text = (demo_site / "site/methodology.html").read_text(encoding="utf-8")
    for needle in (
        "What is the best {category}?",
        "Wilson",
        "Limitations",
        'id="requests-and-disputes"',
        "issues/new?labels=index",
        "per run",
        "claude-haiku-5-5",
    ):
        assert needle in text, needle


def test_demo_rank_badges_are_grey_and_say_demo(demo_site):
    folder = demo_site / "site/badges/python-http-client"
    data = json.loads((folder / "project-a.json").read_text(encoding="utf-8"))
    assert data["label"] == "AI rank · demo"
    assert re.fullmatch(r"(tied )?#\d of 7 · python http clients", data["message"])
    root = ET.fromstring((folder / "project-a.svg").read_text(encoding="utf-8"))
    assert root.tag.endswith("svg")


def test_latest_snapshot_wins(tmp_path):
    for day, rate in (("2026-10-02", 0.1), ("2026-11-02", 0.9)):
        folder = tmp_path / day
        folder.mkdir()
        (folder / "x.json").write_text(json.dumps({"id": "x", "rate": rate}), "utf-8")
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "x.json").write_text("{}", "utf-8")
    assert [s["rate"] for s in latest_snapshots(tmp_path)] == [0.9]


def test_cli(tmp_path, capsys):
    assert main(["validate"]) == 0
    assert "30 protocols" in capsys.readouterr().out
    assert main(["estimate", "--categories", "vector-database"]) == 0
    assert "90 answers" in capsys.readouterr().out
    data = tmp_path / "data"
    assert main(["run", "--demo", "--categories", "vector-database", "--data",
                 str(data), "--date", "2026-11-01"]) == 0  # fmt: skip
    assert "DEMO snapshots" in capsys.readouterr().out
    assert main(["build", "--data", str(data), "--out", str(tmp_path / "s")]) == 0
    assert (tmp_path / "s/categories/vector-database.html").exists()
    assert main(["run", "--categories", "vector-database", "--max-cost", "1"]) == 2
    assert "Missing API keys" in capsys.readouterr().err
    assert main(["run", "--demo", "--categories", "nope"]) == 1


def test_committed_demo_site_is_labelled():
    html_dir = Path(__file__).resolve().parents[2] / "index" / "demo" / "html"
    if not html_dir.exists():
        pytest.skip("the demo site is not part of the sdist")
    pages = sorted(html_dir.rglob("*.html"))
    assert pages, "index/demo/html should hold the labelled demo site"
    for page in pages:
        text = page.read_text(encoding="utf-8")
        assert "DEMO DATA" in text and "noindex" in text
    for badge in html_dir.rglob("*.json"):
        if badge.parent.parent.name == "badges":
            assert json.loads(badge.read_text("utf-8"))["label"].endswith("demo")
