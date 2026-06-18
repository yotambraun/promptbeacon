"""Tests for the web-grounded provider path (parser + beacon wiring)."""

from __future__ import annotations

from types import SimpleNamespace

from promptbeacon import Beacon, Provider
from promptbeacon.core.schemas import Citation
from promptbeacon.providers.grounding import (
    GroundedClient,
    GroundedResponse,
    associate_brands,
    get_grounded_client,
    parse_anthropic_grounded,
)

# Mirrors the documented Anthropic web-search response content blocks.
_BLOCKS = [
    {"type": "text", "text": "I'll search for that."},
    {
        "type": "server_tool_use",
        "id": "srvtoolu_1",
        "name": "web_search",
        "input": {"query": "best running shoes"},
    },
    {
        "type": "web_search_tool_result",
        "tool_use_id": "srvtoolu_1",
        "content": [
            {
                "type": "web_search_result",
                "url": "https://www.reddit.com/r/running",
                "title": "Best running shoes - Reddit",
                "page_age": "April 2026",
            },
            {
                "type": "web_search_result",
                "url": "https://en.wikipedia.org/wiki/Nike,_Inc.",
                "title": "Nike, Inc. - Wikipedia",
                "page_age": "March 2026",
            },
            {
                "type": "web_search_result",
                "url": "https://www.example.com/blog",
                "title": "Some blog",
                "page_age": "2026",
            },
        ],
    },
    {
        "type": "text",
        "text": "Nike is the most discussed brand",
        "citations": [
            {
                "type": "web_search_result_location",
                "url": "https://www.reddit.com/r/running",
                "title": "Best running shoes - Reddit",
                "encrypted_index": "abc",
                "cited_text": "Nike dominates running shoe discussions on Reddit",
            }
        ],
    },
    {
        "type": "text",
        "text": " and well documented.",
        "citations": [
            {
                "type": "web_search_result_location",
                "url": "https://en.wikipedia.org/wiki/Nike,_Inc.",
                "title": "Nike, Inc. - Wikipedia",
                "encrypted_index": "def",
                "cited_text": "Nike, Inc. is an American athletic footwear company",
            }
        ],
    },
]


def test_parse_separates_retrieved_and_cited():
    citations = parse_anthropic_grounded(_BLOCKS, query="best running shoes")
    by_domain = {c.source_name: c for c in citations}

    assert set(by_domain) == {
        "www.reddit.com",
        "en.wikipedia.org",
        "www.example.com",
    }

    reddit = by_domain["www.reddit.com"]
    assert reddit.source_type == "reddit"
    assert reddit.source_rank == 1
    assert reddit.retrieved_but_uncited is False
    assert "Nike dominates" in reddit.context
    assert reddit.query == "best running shoes"

    wiki = by_domain["en.wikipedia.org"]
    assert wiki.source_type == "wikipedia"
    assert wiki.retrieved_but_uncited is False

    # example.com was retrieved but never cited in a text block.
    example = by_domain["www.example.com"]
    assert example.source_rank == 3
    assert example.retrieved_but_uncited is True
    assert example.context == ""


def test_parse_handles_search_error_block():
    blocks = [
        {
            "type": "web_search_tool_result",
            "tool_use_id": "x",
            "content": {
                "type": "web_search_tool_result_error",
                "error_code": "max_uses_exceeded",
            },
        }
    ]
    # Should not raise and should produce no citations.
    assert parse_anthropic_grounded(blocks, query="q") == []


def test_parse_works_with_sdk_style_objects():
    blocks = [
        SimpleNamespace(
            type="web_search_tool_result",
            content=[
                SimpleNamespace(
                    type="web_search_result",
                    url="https://www.reddit.com/r/x",
                    title="t",
                    page_age="2026",
                )
            ],
        ),
        SimpleNamespace(
            type="text",
            text="cited",
            citations=[
                SimpleNamespace(
                    type="web_search_result_location",
                    url="https://www.reddit.com/r/x",
                    title="t",
                    cited_text="snippet",
                )
            ],
        ),
    ]
    citations = parse_anthropic_grounded(blocks, query="q")
    assert len(citations) == 1
    assert citations[0].source_type == "reddit"
    assert citations[0].retrieved_but_uncited is False


def test_associate_brands_from_context():
    citations = [
        Citation(url="https://a.com", source_name="a.com", context="Nike is great"),
        Citation(url="https://b.com", source_name="b.com", context="nothing here"),
    ]
    associate_brands(citations, ["Nike", "Adidas"])
    assert citations[0].brand_associated == "Nike"
    assert citations[1].brand_associated is None


def test_get_grounded_client_only_anthropic_for_now():
    assert get_grounded_client(Provider.ANTHROPIC) is not None
    assert get_grounded_client(Provider.MISTRAL) is None


class _FakeGrounded(GroundedClient):
    provider = Provider.ANTHROPIC

    def is_available(self) -> bool:
        return True

    async def complete_grounded(self, prompt, *, model=None, max_tokens=2048):  # noqa: ARG002
        return GroundedResponse(
            content="Nike is frequently recommended for running shoes.",
            citations=[
                Citation(
                    url="https://www.reddit.com/r/running",
                    source_name="www.reddit.com",
                    context="Nike is a top pick among runners",
                    source_rank=1,
                    source_type="reddit",
                    query=prompt,
                    retrieved_but_uncited=False,
                ),
                Citation(
                    url="https://www.example.com/x",
                    source_name="www.example.com",
                    context="",
                    source_rank=2,
                    source_type="web",
                    query=prompt,
                    retrieved_but_uncited=True,
                ),
            ],
            model="claude-haiku-4-5",
            provider="anthropic",
            latency_ms=12.0,
            search_count=1,
        )


def test_grounded_scan_marks_tier_and_flag(monkeypatch):
    monkeypatch.setattr(
        "promptbeacon.beacon.get_available_providers",
        lambda: [Provider.ANTHROPIC],
    )
    monkeypatch.setattr(
        "promptbeacon.beacon.get_grounded_client",
        lambda p: _FakeGrounded() if p == Provider.ANTHROPIC else None,
    )

    report = (
        Beacon("Nike")
        .with_providers(Provider.ANTHROPIC)
        .with_grounding()
        .with_prompt_count(2)
        .scan()
    )

    # Grounding actually ran -> honest tier + per-result flag.
    assert report.measurement_tier == "api_grounded"
    assert report.provider_results
    assert all(r.grounded for r in report.provider_results)

    # Brand association ran in the beacon -> reddit cites Nike.
    sa = report.source_attribution
    assert "www.reddit.com" in sa.target_cited_domains
    # The retrieved-but-uncited source is preserved.
    assert any(
        c.retrieved_but_uncited for r in report.provider_results for c in r.citations
    )
