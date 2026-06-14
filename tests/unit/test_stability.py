"""Tests for run-to-run stability analysis."""

from __future__ import annotations

from promptbeacon.analysis.stability import aggregate_stability
from promptbeacon.core.schemas import BrandMention, ProviderResult


def _result(prompt: str, mentioned: bool) -> ProviderResult:
    mentions = (
        [BrandMention(brand_name="Nike", sentiment="positive", position=0, context="x")]
        if mentioned
        else []
    )
    return ProviderResult(
        provider="openai",
        model="m",
        prompt=prompt,
        response="Nike" if mentioned else "nobody",
        mentions=mentions,
        latency_ms=1.0,
    )


def test_perfectly_stable_runs():
    # Same outcome every run -> high stability, no flip-flops.
    runs = [[_result("p1", True), _result("p2", True)] for _ in range(4)]
    report = aggregate_stability(runs, "Nike")
    assert report.runs == 4
    assert report.overall_presence_consistency == 1.0
    assert report.flip_flop_count == 0
    assert report.volatility.stability_rating == "stable"
    assert report.stability_score >= 90


def test_flip_flopping_detected():
    # p1 appears every run; p2 alternates -> p2 flip-flops.
    runs = [
        [_result("p1", True), _result("p2", True)],
        [_result("p1", True), _result("p2", False)],
        [_result("p1", True), _result("p2", True)],
        [_result("p1", True), _result("p2", False)],
    ]
    report = aggregate_stability(runs, "Nike")
    flips = {p.prompt: p.flip_flopped for p in report.prompt_stability}
    assert flips["p2"] is True
    assert flips["p1"] is False
    assert report.flip_flop_count == 1
    assert 0.0 < report.overall_presence_consistency < 1.0


def test_score_per_run_recorded():
    runs = [[_result("p1", True)], [_result("p1", False)]]
    report = aggregate_stability(runs, "Nike")
    assert len(report.score_per_run) == 2
    assert report.score_per_run[0] > report.score_per_run[1]
    lo, hi = report.score_confidence_interval
    assert lo <= report.mean_score <= hi


def test_demo_stability_is_not_fake_perfect():
    """Demo mode with cache off should produce genuine run-to-run variation."""
    from promptbeacon import Beacon

    report = (
        Beacon("Acme")
        .with_competitors("Globex")
        .with_categories("widgets")
        .with_prompt_count(6)
        .with_stability(5)
        .demo()
        .scan_stability()
    )
    assert report.stability is not None
    # Not every run identical -> at least some movement or flip-flops.
    distinct_scores = set(report.stability.score_per_run)
    assert len(distinct_scores) > 1 or report.stability.flip_flop_count > 0
