"""Pluggable search backends for the funnel.

The funnel's *retrieval* stage is deliberately separate from Phase 1's
provider-native grounding: here PromptBeacon runs its own observable retrieval
so it can watch what is retrieved vs. cited. Backends use ``httpx`` (already a
dependency) — no extra SDK needed.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod

import httpx
from pydantic import BaseModel

# Realistic, varied domains for the keyless mock backend.
_MOCK_DOMAINS = [
    "reddit.com",
    "en.wikipedia.org",
    "www.consumerreports.org",
    "www.nytimes.com",
    "www.cnbc.com",
    "www.techradar.com",
    "www.g2.com",
]
_MOCK_FILLER = ["Globex", "Initech", "Acme United", "Hooli", "Vandelay"]


class SearchResult(BaseModel):
    """A raw search result from a backend (before brand analysis)."""

    url: str | None = None
    title: str = ""
    snippet: str = ""


class SearchBackend(ABC):
    """Abstract live-web search backend."""

    name: str

    @abstractmethod
    async def search(self, query: str, max_results: int = 8) -> list[SearchResult]:
        """Return up to ``max_results`` results for ``query``."""


def _seed(*parts: str) -> int:
    raw = "|".join(parts).encode()
    return int(hashlib.sha256(raw).hexdigest()[:8], 16)


class MockSearchBackend(SearchBackend):
    """Deterministic offline backend for the keyless demo and tests.

    Weaves the target brand into ~70% of sub-queries' result sets, at a varying
    rank, so the funnel's coverage / rerank / citation metrics are non-trivial.
    """

    name = "mock"

    def __init__(
        self, brand: str, competitors: list[str] | None = None, variation: int = 0
    ) -> None:
        self._brand = brand
        self._competitors = competitors or []
        self._variation = variation

    async def search(self, query: str, max_results: int = 8) -> list[SearchResult]:
        salt = str(self._variation)
        others = self._competitors + _MOCK_FILLER
        brand_present = _seed(query, salt, "hit") % 100 < 70
        brand_rank = _seed(query, salt, "rank") % max_results

        results: list[SearchResult] = []
        for i in range(max_results):
            domain = _MOCK_DOMAINS[_seed(query, salt, "d", str(i)) % len(_MOCK_DOMAINS)]
            if brand_present and i == brand_rank:
                mention = self._brand
            else:
                mention = others[_seed(query, salt, "o", str(i)) % len(others)]
            results.append(
                SearchResult(
                    url=f"https://{domain}/{_seed(query, str(i)) % 9999}",
                    title=f"{mention} — {query}",
                    snippet=f"{mention} is frequently discussed for {query}.",
                )
            )
        return results


class TavilyBackend(SearchBackend):
    """Live web search via the Tavily API (called directly with httpx)."""

    name = "tavily"

    def __init__(self, api_key: str, timeout: float = 30.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    async def search(self, query: str, max_results: int = 8) -> list[SearchResult]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self._api_key,
                    "query": query,
                    "max_results": max_results,
                    "include_answer": False,
                },
            )
            response.raise_for_status()
            payload = response.json()

        return [
            SearchResult(
                url=item.get("url"),
                title=item.get("title", ""),
                snippet=item.get("content", ""),
            )
            for item in payload.get("results", [])
        ]
