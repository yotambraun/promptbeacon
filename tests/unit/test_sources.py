"""Tests for source-domain attribution analysis."""

from __future__ import annotations

from promptbeacon.analysis.sources import (
    aggregate_source_attribution,
    classify_source_type,
)
from promptbeacon.core.schemas import Citation, ProviderResult


def _result(
    provider: str,
    prompt: str,
    citations: list[Citation],
    *,
    error: str | None = None,
) -> ProviderResult:
    return ProviderResult(
        provider=provider,
        model="m",
        prompt=prompt,
        response="...",
        mentions=[],
        citations=citations,
        latency_ms=1.0,
        error=error,
    )


def _cite(source_name: str, url: str | None, brand: str | None) -> Citation:
    return Citation(url=url, source_name=source_name, brand_associated=brand)


def test_classify_source_type():
    assert classify_source_type("reddit.com") == "reddit"
    assert classify_source_type("en.wikipedia.org") == "wikipedia"
    assert classify_source_type("arxiv.org") == "academic"
    assert classify_source_type("www.nytimes.com") == "news"
    assert classify_source_type("g2.com") == "review"
    assert classify_source_type("example.com") == "web"


def test_aggregate_counts_and_ranks_domains():
    results = [
        _result(
            "openai",
            "p1",
            [
                _cite("reddit.com", "https://reddit.com/r/x", "Nike"),
                _cite("nytimes.com", "https://nytimes.com/a", "Adidas"),
            ],
        ),
        _result(
            "openai",
            "p2",
            [_cite("reddit.com", "https://reddit.com/r/y", "Nike")],
        ),
    ]
    report = aggregate_source_attribution(results, "Nike", ["Adidas"])

    assert report.total_citations == 3
    # reddit cited twice -> ranked first
    top = report.entries[0]
    assert top.domain == "reddit.com"
    assert top.citations == 2
    assert top.source_type == "reddit"
    assert top.cites_target is True
    assert top.brands_cited == ["Nike"]
    assert round(top.share, 4) == round(2 / 3, 4)

    nyt = report.entries[1]
    assert nyt.domain == "nytimes.com"
    assert nyt.cites_target is False
    assert report.by_type == {"reddit": 2, "news": 1}


def test_target_cited_domains_property():
    results = [
        _result(
            "openai",
            "p1",
            [
                _cite("reddit.com", "https://reddit.com/r/x", "Nike"),
                _cite("nytimes.com", "https://nytimes.com/a", "Adidas"),
            ],
        )
    ]
    report = aggregate_source_attribution(results, "Nike", ["Adidas"])
    assert report.target_cited_domains == ["reddit.com"]


def test_ignores_failed_results():
    ok = _result("openai", "p1", [_cite("reddit.com", "https://reddit.com/x", "Nike")])
    failed = _result("openai", "p2", [], error="boom")
    report = aggregate_source_attribution([ok, failed], "Nike")
    assert report.total_citations == 1


def test_empty_results():
    report = aggregate_source_attribution([], "Nike")
    assert report.total_citations == 0
    assert report.entries == []
    assert report.target_cited_domains == []


def test_attribution_without_url_classified_as_attribution():
    results = [
        _result("openai", "p1", [_cite("Consumer Reports", None, "Nike")]),
    ]
    report = aggregate_source_attribution(results, "Nike")
    assert report.entries[0].source_type == "attribution"


def test_dedupes_attribution_already_covered_by_url():
    # One sentence often yields both a URL citation and an "According to X"
    # attribution for the same source — count it once, keyed on the domain.
    results = [
        _result(
            "openai",
            "p1",
            [
                _cite(
                    "www.consumerreports.org",
                    "https://www.consumerreports.org/best",
                    "Nike",
                ),
                _cite("Consumer Reports", None, "Nike"),
            ],
        )
    ]
    report = aggregate_source_attribution(results, "Nike")
    assert report.total_citations == 1
    assert [e.domain for e in report.entries] == ["www.consumerreports.org"]


def test_keeps_attribution_when_no_matching_url():
    # A name-only source with no URL anywhere is a real source — keep it.
    results = [
        _result(
            "openai",
            "p1",
            [
                _cite("example.com", "https://example.com/a", "Nike"),
                _cite("Gartner", None, "Nike"),
            ],
        )
    ]
    report = aggregate_source_attribution(results, "Nike")
    assert report.total_citations == 2
    assert {e.domain for e in report.entries} == {"example.com", "Gartner"}
