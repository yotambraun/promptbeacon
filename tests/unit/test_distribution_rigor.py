"""Tests for Phase 2 distribution rigor: bootstrap CIs, source stability,
buyer-intent prompts."""

from __future__ import annotations

import pytest

from promptbeacon.analysis.stability import aggregate_stability
from promptbeacon.analysis.statistics import bootstrap_ci
from promptbeacon.core.schemas import BrandMention, Citation, ProviderResult
from promptbeacon.prompts.templates import generate_buyer_intent_prompts

# --- bootstrap_ci ---------------------------------------------------------


def test_bootstrap_ci_empty():
    assert bootstrap_ci([]) == (0.0, 0.0)


def test_bootstrap_ci_single():
    assert bootstrap_ci([42.0]) == (42.0, 42.0)


def test_bootstrap_ci_identical_scores_collapse():
    assert bootstrap_ci([50.0, 50.0, 50.0, 50.0]) == (50.0, 50.0)


def test_bootstrap_ci_is_deterministic():
    scores = [40.0, 55.0, 60.0, 48.0, 52.0]
    assert bootstrap_ci(scores) == bootstrap_ci(scores)


def test_bootstrap_ci_stays_within_observed_range():
    # Every resample mean of [40, 50, 60] lies in [40, 60].
    lo, hi = bootstrap_ci([40.0, 50.0, 60.0])
    assert 40.0 <= lo <= hi <= 60.0


def test_bootstrap_ci_clamped_to_bounds():
    assert bootstrap_ci([0.0, 0.0, 0.0]) == (0.0, 0.0)
    _, hi = bootstrap_ci([100.0, 100.0, 90.0])
    assert hi <= 100.0


# --- source stability -----------------------------------------------------


def _result(
    prompt: str, *, brand_mentioned: bool, domains: list[str]
) -> ProviderResult:
    citations = [Citation(url=f"https://{d}/x", source_name=d) for d in domains]
    mentions = (
        [
            BrandMention(
                brand_name="Nike", sentiment="positive", position=0, context="Nike"
            )
        ]
        if brand_mentioned
        else []
    )
    return ProviderResult(
        provider="openai",
        model="m",
        prompt=prompt,
        response="...",
        mentions=mentions,
        citations=citations,
        latency_ms=1.0,
    )


def test_source_stability_tracks_consistency_and_flipflop():
    runs = [
        [_result("p1", brand_mentioned=True, domains=["reddit.com", "nytimes.com"])],
        [_result("p1", brand_mentioned=True, domains=["reddit.com"])],
        [_result("p1", brand_mentioned=False, domains=["reddit.com"])],
    ]
    report = aggregate_stability(runs, "Nike")

    by_domain = {s.domain: s for s in report.source_stability}
    # reddit cited in all 3 runs -> stable.
    assert by_domain["reddit.com"].appearances == 3
    assert by_domain["reddit.com"].flip_flopped is False
    assert by_domain["reddit.com"].presence_rate == 1.0
    # nytimes cited in only 1 of 3 runs -> flip-flop.
    assert by_domain["nytimes.com"].appearances == 1
    assert by_domain["nytimes.com"].flip_flopped is True
    # entries are ranked by appearances (descending).
    assert report.source_stability[0].domain == "reddit.com"


def test_stability_report_has_bootstrap_interval():
    runs = [
        [_result("p1", brand_mentioned=True, domains=["reddit.com"])],
        [_result("p1", brand_mentioned=False, domains=[])],
    ]
    report = aggregate_stability(runs, "Nike")
    lo, hi = report.score_bootstrap_interval
    assert 0.0 <= lo <= hi <= 100.0


# --- buyer-intent prompts -------------------------------------------------


def test_buyer_intent_prompts_count_and_distinct():
    prompts = generate_buyer_intent_prompts("running shoes", 50)
    assert len(prompts) == 50
    assert len(set(prompts)) == 50  # all distinct
    assert all("running shoes" in p for p in prompts)


def test_buyer_intent_prompts_cap_at_available():
    prompts = generate_buyer_intent_prompts("widgets", 10_000)
    assert len(prompts) == len(set(prompts))  # never duplicates
    assert len(prompts) >= 50  # enough for the recommended protocol


def test_buyer_intent_prompts_reject_bad_n():
    with pytest.raises(ValueError):
        generate_buyer_intent_prompts("widgets", 0)
