"""Source-domain attribution — which sites feed AI-search visibility.

Web-grounded AI answers cite their sources. Aggregating those citations by
domain answers the actionable GEO question: *which sites do the engines trust
for my category, and which of them mention me?* Research shows a small set of
domains (Reddit, Wikipedia, major news) drives most brand visibility, so this
is the lever teams act on ("get cited on these sites").
"""

from __future__ import annotations

import re
from typing import TypedDict

from promptbeacon.core.schemas import (
    Citation,
    ProviderResult,
    SourceAttributionEntry,
    SourceAttributionReport,
)


class _Bucket(TypedDict):
    """Mutable per-domain accumulator used while aggregating citations."""

    type: str
    count: int
    brands: set[str]
    cites_target: bool

_NEWS = {
    "nytimes.com",
    "bbc.com",
    "bbc.co.uk",
    "cnn.com",
    "reuters.com",
    "forbes.com",
    "techcrunch.com",
    "theverge.com",
    "wsj.com",
    "bloomberg.com",
    "businessinsider.com",
    "theguardian.com",
    "wired.com",
    "engadget.com",
    "cnbc.com",
    "apnews.com",
}
_REVIEW = {
    "g2.com",
    "trustpilot.com",
    "capterra.com",
    "yelp.com",
    "tripadvisor.com",
    "consumerreports.org",
    "trustradius.com",
}
_SOCIAL = {
    "twitter.com",
    "x.com",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "quora.com",
    "medium.com",
}


def _host_match(host: str, base: str) -> bool:
    """True if ``host`` is ``base`` or a subdomain of it."""
    return host == base or host.endswith("." + base)


def classify_source_type(domain: str) -> str:
    """Classify a source domain into a coarse type used for GEO attribution.

    Returns one of: ``reddit``, ``wikipedia``, ``video``, ``code``,
    ``academic``, ``news``, ``review``, ``social``, or ``web`` (default).
    """
    d = domain.strip().lower()
    if d.startswith("www."):
        d = d[4:]

    if _host_match(d, "reddit.com"):
        return "reddit"
    if _host_match(d, "wikipedia.org"):
        return "wikipedia"
    if _host_match(d, "youtube.com") or _host_match(d, "youtu.be"):
        return "video"
    if _host_match(d, "github.com"):
        return "code"
    if (
        _host_match(d, "arxiv.org")
        or _host_match(d, "ncbi.nlm.nih.gov")
        or _host_match(d, "pubmed.gov")
        or d.endswith(".edu")
    ):
        return "academic"
    if any(_host_match(d, n) for n in _NEWS):
        return "news"
    if any(_host_match(d, r) for r in _REVIEW):
        return "review"
    if any(_host_match(d, s) for s in _SOCIAL):
        return "social"
    return "web"


def _source_type_for(source_type: str | None, url: str | None, domain: str) -> str:
    """Resolve a citation's source type, preferring an explicit grounded value."""
    if source_type:
        return source_type
    if url:
        return classify_source_type(domain)
    return "attribution"


def _core(name: str) -> str:
    """Reduce a domain or source name to a comparable alphanumeric core.

    ``"www.consumerreports.org"`` and ``"Consumer Reports"`` both reduce to
    ``"consumerreports"``, so an attribution phrase can be matched to the URL
    citation of the same source.
    """
    s = name.strip().lower()
    if "." in s and "/" not in s and " " not in s:  # looks like a domain
        if s.startswith("www."):
            s = s[4:]
        s = s.split(".")[0]
    return re.sub(r"[^a-z0-9]", "", s)


def _dedupe_citations(citations: list[Citation]) -> list[Citation]:
    """Drop attribution-only citations already represented by a URL citation.

    Many answers phrase a single source two ways in one sentence — e.g.
    ``"According to Consumer Reports (https://consumerreports.org/...)"`` — which
    the regex extractor surfaces as both an attribution phrase and a URL. For
    source attribution we want one count per source, keyed on its domain.
    """
    domain_cores = {_core(c.source_name) for c in citations if c.url}
    domain_cores.discard("")
    kept: list[Citation] = []
    for c in citations:
        if c.url is None:
            name_core = _core(c.source_name)
            if name_core and any(
                name_core.startswith(dc) or dc.startswith(name_core)
                for dc in domain_cores
            ):
                continue  # same source already counted via its URL
        kept.append(c)
    return kept


def aggregate_source_attribution(
    results: list[ProviderResult],
    target_brand: str,
    competitors: list[str] | None = None,  # noqa: ARG001 — reserved for future filtering
) -> SourceAttributionReport:
    """Aggregate citations across a scan into a ranked source-domain report.

    Args:
        results: Provider results from a scan (failed results are ignored).
        target_brand: The brand being analyzed.
        competitors: Reserved for future competitor-specific breakdowns.

    Returns:
        SourceAttributionReport with domains ranked by citation count.
    """
    target = target_brand.lower()
    agg: dict[str, _Bucket] = {}
    total = 0

    for result in results:
        if not result.success:
            continue
        for citation in _dedupe_citations(result.citations):
            domain = citation.source_name
            stype = _source_type_for(citation.source_type, citation.url, domain)
            total += 1
            bucket = agg.setdefault(
                domain,
                _Bucket(type=stype, count=0, brands=set(), cites_target=False),
            )
            bucket["count"] += 1
            if citation.brand_associated:
                bucket["brands"].add(citation.brand_associated)
                if citation.brand_associated.lower() == target:
                    bucket["cites_target"] = True

    entries = [
        SourceAttributionEntry(
            domain=domain,
            source_type=data["type"],
            citations=data["count"],
            share=round(data["count"] / total, 4) if total else 0.0,
            brands_cited=sorted(data["brands"]),
            cites_target=data["cites_target"],
        )
        for domain, data in agg.items()
    ]
    entries.sort(key=lambda e: (-e.citations, e.domain))

    by_type: dict[str, int] = {}
    for entry in entries:
        by_type[entry.source_type] = by_type.get(entry.source_type, 0) + entry.citations

    return SourceAttributionReport(
        target_brand=target_brand,
        total_citations=total,
        entries=entries,
        by_type=by_type,
    )
