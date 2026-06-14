"""Tests for presence-based Share of Voice."""

from __future__ import annotations

from promptbeacon.analysis.scorer import calculate_share_of_voice
from promptbeacon.core.schemas import BrandMention, ProviderResult


def _result(provider: str, prompt: str, brands: list[str]) -> ProviderResult:
    """Build a ProviderResult where the given brands are each mentioned once."""
    mentions = [
        BrandMention(
            brand_name=b,
            sentiment="positive",
            position=i,
            context=f"...{b}...",
        )
        for i, b in enumerate(brands)
    ]
    return ProviderResult(
        provider=provider,
        model="m",
        prompt=prompt,
        response=" ".join(brands),
        mentions=mentions,
        latency_ms=1.0,
    )


def test_share_of_voice_basic_counts():
    results = [
        _result("openai", "p1", ["Nike", "Adidas"]),
        _result("openai", "p2", ["Nike"]),
        _result("openai", "p3", ["Adidas"]),
        _result("openai", "p4", []),
    ]
    sov = calculate_share_of_voice(results, "Nike", ["Adidas"])

    nike = sov.aggregate["Nike"]
    adidas = sov.aggregate["Adidas"]
    assert nike.appearances == 2
    assert adidas.appearances == 2
    assert nike.total_prompts == 4
    assert nike.presence_rate == 0.5
    # 2 / (2 + 2)
    assert nike.share_of_voice == 0.5
    assert sov.target_share == 0.5


def test_share_of_voice_rank_and_leader():
    results = [
        _result("openai", "p1", ["Adidas"]),
        _result("openai", "p2", ["Adidas"]),
        _result("openai", "p3", ["Nike"]),
    ]
    sov = calculate_share_of_voice(results, "Nike", ["Adidas"])
    # Adidas appears twice, Nike once -> Nike is rank 2
    assert sov.target_rank == 2
    assert sov.aggregate["Adidas"].appearances == 2


def test_share_of_voice_per_provider():
    results = [
        _result("openai", "p1", ["Nike"]),
        _result("anthropic", "p1", ["Adidas"]),
    ]
    sov = calculate_share_of_voice(results, "Nike", ["Adidas"])
    assert set(sov.by_provider) == {"openai", "anthropic"}
    assert sov.by_provider["openai"]["Nike"].appearances == 1
    assert sov.by_provider["anthropic"]["Nike"].appearances == 0


def test_share_of_voice_no_appearances_is_zero():
    results = [_result("openai", "p1", [])]
    sov = calculate_share_of_voice(results, "Nike", ["Adidas"])
    assert sov.target_share == 0.0
    assert sov.aggregate["Nike"].presence_rate == 0.0


def test_share_of_voice_ignores_failed_results():
    ok = _result("openai", "p1", ["Nike"])
    failed = ProviderResult(
        provider="openai",
        model="m",
        prompt="p2",
        response="",
        mentions=[],
        latency_ms=0.0,
        error="boom",
    )
    sov = calculate_share_of_voice([ok, failed], "Nike", ["Adidas"])
    # Only the successful result counts toward totals
    assert sov.aggregate["Nike"].total_prompts == 1
    assert sov.aggregate["Nike"].presence_rate == 1.0
