"""Tests for LLM-based smart recommendations (pure functions + fallback)."""

from __future__ import annotations

import pytest

from promptbeacon import Beacon, Provider
from promptbeacon.analysis.llm_recommendations import (
    build_recommendations_prompt,
    parse_recommendations,
)


@pytest.fixture(scope="module")
def demo_report():
    return (
        Beacon("Nike")
        .with_competitors("Adidas")
        .with_categories("running shoes")
        .with_prompt_count(4)
        .with_providers(Provider.OPENAI)
        .demo()
        .scan()
    )


def test_prompt_includes_brand_and_score(demo_report):
    prompt = build_recommendations_prompt(demo_report)
    assert "Nike" in prompt
    assert "Visibility score" in prompt
    assert "JSON" in prompt


def test_parse_valid_recommendations():
    raw = (
        '{"recommendations": ['
        '{"action": "Publish a comparison page", "rationale": "Low SoV vs Adidas",'
        ' "priority": "high", "expected_impact": "More citations"},'
        '{"action": "Earn reviews", "rationale": "Few sources", "priority": "low"}]}'
    )
    recs = parse_recommendations(raw)
    assert len(recs) == 2
    assert recs[0].priority == "high"
    assert recs[0].action.startswith("Publish")
    assert recs[1].priority == "low"


def test_parse_normalizes_bad_priority():
    raw = '{"recommendations": [{"action": "Do X", "priority": "urgent"}]}'
    recs = parse_recommendations(raw)
    assert recs[0].priority == "medium"


def test_parse_strips_code_fences():
    raw = '```json\n{"recommendations": [{"action": "Do X", "priority": "high"}]}\n```'
    recs = parse_recommendations(raw)
    assert len(recs) == 1


def test_parse_invalid_raises():
    with pytest.raises(ValueError):
        parse_recommendations("nope")


def test_parse_empty_raises():
    with pytest.raises(ValueError):
        parse_recommendations('{"recommendations": []}')


def test_demo_with_smart_recommendations_keeps_rule_based():
    # Demo mode makes no real LLM calls; smart recs must be a no-op there.
    report = (
        Beacon("Nike")
        .with_categories("running shoes")
        .with_prompt_count(4)
        .with_smart_recommendations()
        .demo()
        .scan()
    )
    # Recommendations still present (rule-based), scan didn't error.
    assert isinstance(report.recommendations, list)
