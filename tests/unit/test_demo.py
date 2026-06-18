"""Tests for keyless demo mode and the mock provider."""

from __future__ import annotations

from promptbeacon import Beacon, Provider
from promptbeacon.providers.mock_client import MockLLMClient


def test_mock_client_is_available_without_keys():
    client = MockLLMClient(Provider.OPENAI, brand="Nike", competitors=["Adidas"])
    assert client.is_available() is True
    assert client.provider_name == "openai"


def test_mock_client_weaves_in_brand_and_is_deterministic():
    client = MockLLMClient(Provider.OPENAI, brand="Zorptech", competitors=["Adidas"])
    r1 = client.complete_sync("What are the best running shoes brands?")
    r2 = client.complete_sync("What are the best running shoes brands?")
    assert r1.content == r2.content  # deterministic for same prompt+variation
    assert r1.cost_usd == 0.0


def test_mock_client_variation_changes_output():
    a = MockLLMClient(Provider.OPENAI, brand="Nike", variation=0)
    b = MockLLMClient(Provider.OPENAI, brand="Nike", variation=1)
    prompt = "What are the best running shoes brands?"
    # Across the prompt set, different variations should differ somewhere.
    prompts = [f"{prompt} {i}" for i in range(8)]
    diffs = sum(
        1 for p in prompts if a.complete_sync(p).content != b.complete_sync(p).content
    )
    assert diffs > 0


def test_demo_scan_no_keys_produces_report():
    report = (
        Beacon("Nike")
        .with_competitors("Adidas", "Puma")
        .with_categories("running shoes")
        .with_prompt_count(8)
        .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
        .demo()
        .scan()
    )
    assert 0.0 <= report.visibility_score <= 100.0
    assert report.mention_count > 0
    assert report.share_of_voice is not None
    assert "Adidas" in report.share_of_voice.aggregate
    assert set(report.providers_used) == {"openai", "anthropic"}
    assert report.total_cost_usd in (None, 0.0)


def test_demo_scan_labels_tier_and_populates_source_attribution():
    report = (
        Beacon("Nike")
        .with_competitors("Adidas", "Puma")
        .with_categories("running shoes")
        .with_prompt_count(10)
        .demo()
        .scan()
    )
    # Honesty label: demo data is clearly marked, not passed off as real.
    assert report.measurement_tier == "demo"

    sa = report.source_attribution
    assert sa is not None
    # Demo answers weave in citations, so attribution should be non-empty.
    assert sa.total_citations > 0
    assert len(sa.entries) > 0
    # Entries are ranked by citation count (descending).
    counts = [e.citations for e in sa.entries]
    assert counts == sorted(counts, reverse=True)
    # by_type sums to the total citation count.
    assert sum(sa.by_type.values()) == sa.total_citations


def test_with_grounding_is_chainable_and_sets_flag():
    beacon = Beacon("Nike").with_grounding()
    assert beacon._grounded is True
    assert Beacon("Nike")._measurement_tier() == "base_model"
