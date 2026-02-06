"""Citation extraction from LLM responses."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """A single citation found in an LLM response."""

    url: str | None = Field(default=None, description="URL if one was cited")
    source_name: str = Field(..., description="Name of the cited source")
    context: str = Field(
        default="", description="Surrounding text where the citation appeared"
    )
    brand_associated: str | None = Field(
        default=None,
        description="Brand name nearest to this citation, if any",
    )


class CitationResult(BaseModel):
    """Aggregated citation extraction results."""

    citations: list[Citation] = Field(default_factory=list)
    total_count: int = 0
    unique_domains: list[str] = Field(default_factory=list)


# Regex for URLs (http/https)
_URL_PATTERN = re.compile(
    r"https?://[^\s\)\]\},\"'<>]+",
    re.IGNORECASE,
)

# Patterns for attribution phrases like "According to X", "Source: X"
_ATTRIBUTION_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"(?:according to|as reported by|as stated by|per)\s+([A-Z][\w\s&'.,-]{1,60}?)(?:[,.]|\s(?:—|-|–))",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:source|sources|cited by|reference|via):\s*([A-Z][\w\s&'.,-]{1,60}?)(?:[,.\n]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:based on(?: data from| research by| a report by)?)\s+([A-Z][\w\s&'.,-]{1,60}?)(?:[,.]|\s(?:—|-|–))",
        re.IGNORECASE,
    ),
]


def _extract_domain(url: str) -> str:
    """Extract the domain from a URL."""
    # Strip protocol
    domain = re.sub(r"^https?://", "", url)
    # Strip path
    domain = domain.split("/")[0]
    # Strip port
    domain = domain.split(":")[0]
    return domain.lower()


def _find_nearest_brand(
    text: str,
    position: int,
    brands: list[str],
    max_distance: int = 300,
) -> str | None:
    """Find the brand name closest to a given character position."""
    best_brand: str | None = None
    best_distance = max_distance + 1

    for brand in brands:
        for match in re.finditer(re.escape(brand), text, re.IGNORECASE):
            distance = min(
                abs(match.start() - position),
                abs(match.end() - position),
            )
            if distance < best_distance:
                best_distance = distance
                best_brand = brand

    return best_brand if best_distance <= max_distance else None


def extract_citations(
    response: str,
    brands: list[str] | None = None,
) -> CitationResult:
    """Extract citations (URLs and attribution phrases) from an LLM response.

    Args:
        response: The LLM response text.
        brands: Optional list of brand names to associate with citations.

    Returns:
        CitationResult with extracted citations.
    """
    if not response:
        return CitationResult()

    brands = brands or []
    citations: list[Citation] = []
    seen_sources: set[str] = set()

    # 1. Extract URLs
    for match in _URL_PATTERN.finditer(response):
        url = match.group(0).rstrip(".,;:!?)")
        domain = _extract_domain(url)

        # Deduplicate by URL
        if url in seen_sources:
            continue
        seen_sources.add(url)

        # Context around the URL
        ctx_start = max(0, match.start() - 80)
        ctx_end = min(len(response), match.end() + 80)
        context = response[ctx_start:ctx_end].strip()

        brand = _find_nearest_brand(response, match.start(), brands)

        citations.append(
            Citation(
                url=url,
                source_name=domain,
                context=context,
                brand_associated=brand,
            )
        )

    # 2. Extract attribution phrases
    for pattern in _ATTRIBUTION_PATTERNS:
        for match in pattern.finditer(response):
            source_name = match.group(1).strip().rstrip(".,;:")
            if not source_name or source_name.lower() in seen_sources:
                continue
            seen_sources.add(source_name.lower())

            ctx_start = max(0, match.start() - 40)
            ctx_end = min(len(response), match.end() + 40)
            context = response[ctx_start:ctx_end].strip()

            brand = _find_nearest_brand(response, match.start(), brands)

            citations.append(
                Citation(
                    url=None,
                    source_name=source_name,
                    context=context,
                    brand_associated=brand,
                )
            )

    # Unique domains (from URL citations only)
    unique_domains = sorted({_extract_domain(c.url) for c in citations if c.url})

    return CitationResult(
        citations=citations,
        total_count=len(citations),
        unique_domains=unique_domains,
    )
