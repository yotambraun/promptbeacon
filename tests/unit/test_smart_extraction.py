"""Tests for LLM-based smart extraction (pure functions + fallback)."""

from __future__ import annotations

import pytest

from promptbeacon import Beacon, Provider
from promptbeacon.extraction.llm_extraction import (
    build_extraction_prompt,
    parse_llm_extraction,
)

TEXT = "Nike and Adidas are both strong. I'd recommend Nike for runners."


def test_prompt_lists_tracked_brands():
    prompt = build_extraction_prompt(TEXT, "Nike", ["Adidas"], ["Nike Inc"])
    assert "Nike" in prompt and "Adidas" in prompt and "Nike Inc" in prompt
    assert "JSON" in prompt


def test_parse_valid_json():
    raw = (
        '{"mentions": ['
        '{"brand": "Nike", "sentiment": "positive", "recommended": true},'
        '{"brand": "Adidas", "sentiment": "neutral", "recommended": false}]}'
    )
    result = parse_llm_extraction(raw, TEXT, "Nike", ["Adidas"])
    by_brand = {m.brand_name: m for m in result.mentions}
    assert by_brand["Nike"].sentiment == "positive"
    assert by_brand["Nike"].is_recommendation is True
    assert by_brand["Adidas"].sentiment == "neutral"
    assert by_brand["Nike"].confidence == 0.9
    assert by_brand["Nike"].context  # found in the text


def test_parse_maps_aliases_to_canonical():
    raw = '{"mentions": [{"brand": "Nike Inc", "sentiment": "positive"}]}'
    result = parse_llm_extraction(raw, TEXT, "Nike", [], ["Nike Inc"])
    assert [m.brand_name for m in result.mentions] == ["Nike"]


def test_parse_ignores_untracked_brands():
    raw = '{"mentions": [{"brand": "Reebok", "sentiment": "positive"}]}'
    result = parse_llm_extraction(raw, TEXT, "Nike", ["Adidas"])
    assert result.mentions == []


def test_parse_strips_code_fences():
    raw = '```json\n{"mentions": [{"brand": "Nike", "sentiment": "positive"}]}\n```'
    result = parse_llm_extraction(raw, TEXT, "Nike", ["Adidas"])
    assert len(result.mentions) == 1


def test_parse_invalid_json_raises():
    with pytest.raises(ValueError):
        parse_llm_extraction("not json", TEXT, "Nike", [])


def test_parse_missing_key_raises():
    with pytest.raises(ValueError):
        parse_llm_extraction('{"foo": 1}', TEXT, "Nike", [])


def test_demo_with_smart_extraction_falls_back_to_regex():
    # Demo mode makes no real LLM calls, so smart extraction must not break it.
    report = (
        Beacon("Nike")
        .with_competitors("Adidas")
        .with_categories("running shoes")
        .with_prompt_count(4)
        .with_providers(Provider.OPENAI)
        .with_smart_extraction()
        .demo()
        .scan()
    )
    assert report.mention_count >= 0
    assert report.share_of_voice is not None
