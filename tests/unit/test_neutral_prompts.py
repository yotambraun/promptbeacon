"""Default prompts read naturally for any category (software, services, goods)."""

from __future__ import annotations

import re

import pytest

from promptbeacon import Beacon
from promptbeacon.prompts.templates import get_industry_prompts
from promptbeacon.protocol import ScanProtocol, build_beacon


@pytest.mark.parametrize(
    "category", ["project management software", "python http client", "running shoes"]
)
def test_default_prompts_are_noun_neutral(category):
    prompts = Beacon("X").with_category(category).with_prompt_count(25)._get_prompts()
    assert len(prompts) == 25
    for p in prompts:
        assert category in p  # used exactly as given, never re-pluralised
        assert not re.search(r"\b(brands?|company|companies)\b", p), p


def test_first_default_prompt():
    prompts = Beacon("X").with_category("python http client")._get_prompts()
    assert prompts[0] == "What are the best python http client?"


def test_industry_and_pinned_prompts_are_unchanged():
    ecommerce = Beacon("X").with_category("shoes").with_industry("ecommerce")
    assert ecommerce._get_prompts()[0] == get_industry_prompts("ecommerce")[0].format(
        category="shoes"
    )
    pinned = ["Which shoe brand is best?"]
    assert (
        build_beacon(ScanProtocol(brand="X", prompts=pinned))._get_prompts() == pinned
    )


def test_demo_answers_name_the_category_for_every_template():
    report = (
        Beacon("httpx")
        .demo()
        .with_category("python http client")
        .with_competitors("requests")
        .scan()
    )
    for r in report.provider_results:
        assert "python http client" in r.response.splitlines()[0], r.prompt
