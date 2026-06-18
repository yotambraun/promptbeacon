"""Web-grounded provider clients (official SDKs).

A base-model completion reflects the model's training memory. A *grounded* query
enables the provider's native web-search tool, so the answer reflects what the
engine returns when it searches the live web — and it returns the **real sources
it cited**. We route grounded calls through the official provider SDKs rather
than LiteLLM, because LiteLLM's passthrough drops the structured citation blocks
we depend on (litellm #17737 / #14011).

Anthropic ships first (Brave-backed web search). OpenAI and Gemini adapters
follow the same `GroundedClient` shape.

Honesty: this measures the provider *API's* web search, which approximates but
does **not** equal the consumer product (ChatGPT.com etc.).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from promptbeacon.analysis.sources import classify_source_type
from promptbeacon.core.config import Provider, get_api_key
from promptbeacon.core.schemas import Citation
from promptbeacon.extraction.citations import _extract_domain

logger = logging.getLogger(__name__)

# Stable web-search tool (no code-execution dependency). The 20260209 version
# adds dynamic filtering but requires the code-execution tool; the stable
# version returns the same citation structure we parse.
ANTHROPIC_WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search"}


@dataclass
class GroundedResponse:
    """Result of a web-grounded query: the answer plus the real cited sources."""

    content: str
    citations: list[Citation]
    model: str
    provider: str
    latency_ms: float
    cost_usd: float | None = None
    search_count: int = 0


def _field(block: Any, name: str, default: Any = None) -> Any:
    """Read a field from a block that may be a dict or an SDK object."""
    if isinstance(block, dict):
        return block.get(name, default)
    return getattr(block, name, default)


def parse_anthropic_grounded(content_blocks: list[Any], query: str) -> list[Citation]:
    """Parse Anthropic web-search content blocks into Citations.

    Handles the documented response shape (works with SDK objects or plain
    dicts). Distinguishes **retrieved** sources (in ``web_search_tool_result``
    blocks) from **cited** sources (``web_search_result_location`` citations on
    text blocks) so ``retrieved_but_uncited`` is populated.
    """
    # Retrieved sources, in first-seen order (rank).
    retrieved: list[str] = []
    retrieved_titles: dict[str, str] = {}
    # Cited sources -> cited_text snippet.
    cited: dict[str, str] = {}

    for block in content_blocks:
        btype = _field(block, "type")
        if btype == "web_search_tool_result":
            results = _field(block, "content")
            if not isinstance(results, list):
                continue  # error object (web_search_tool_result_error) — skip
            for item in results:
                if _field(item, "type") != "web_search_result":
                    continue
                url = _field(item, "url")
                if url and url not in retrieved_titles:
                    retrieved.append(url)
                    retrieved_titles[url] = _field(item, "title") or ""
        elif btype == "text":
            for citation in _field(block, "citations") or []:
                if _field(citation, "type") != "web_search_result_location":
                    continue
                url = _field(citation, "url")
                if url and url not in cited:
                    cited[url] = _field(citation, "cited_text") or ""

    citations: list[Citation] = []
    # Cited sources first, in retrieval order where known.
    ordered = retrieved + [u for u in cited if u not in retrieved_titles]
    for url in ordered:
        domain = _extract_domain(url)
        is_cited = url in cited
        rank = retrieved.index(url) + 1 if url in retrieved else None
        citations.append(
            Citation(
                url=url,
                source_name=domain,
                context=cited.get(url, "")[:300],
                source_rank=rank,
                source_type=classify_source_type(domain),
                query=query,
                retrieved_but_uncited=not is_cited,
            )
        )
    return citations


def associate_brands(citations: list[Citation], brands: list[str]) -> list[Citation]:
    """Tag each citation with the brand named in its cited snippet, if any.

    Grounded citations carry the snippet the engine cited (``context``). If a
    tracked brand appears in that snippet, attribute the source to it — this is
    what drives ``cites_target`` in source attribution.
    """
    lowered = [(b, b.lower()) for b in brands]
    for citation in citations:
        ctx = citation.context.lower()
        for original, low in lowered:
            if low and low in ctx:
                citation.brand_associated = original
                break
    return citations


class GroundedClient:
    """Base for provider-native web-grounded clients."""

    provider: Provider

    def is_available(self) -> bool:  # pragma: no cover - trivial
        raise NotImplementedError

    async def complete_grounded(
        self, prompt: str, *, model: str | None = None, max_tokens: int = 2048
    ) -> GroundedResponse:
        raise NotImplementedError


class AnthropicGroundedClient(GroundedClient):
    """Web-grounded client using the official ``anthropic`` SDK (Brave-backed)."""

    provider = Provider.ANTHROPIC

    def __init__(self, model: str | None = None, timeout: float = 60.0) -> None:
        self._model = model or "claude-haiku-4-5"
        self.timeout = timeout

    def is_available(self) -> bool:
        if get_api_key(Provider.ANTHROPIC) is None:
            return False
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False
        return True

    async def complete_grounded(
        self, prompt: str, *, model: str | None = None, max_tokens: int = 2048
    ) -> GroundedResponse:
        import anthropic  # lazy: only needed for the [grounded] extra

        client = anthropic.AsyncAnthropic(timeout=self.timeout)
        use_model = model or self._model
        start = time.time()
        response = await client.messages.create(
            model=use_model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            tools=[ANTHROPIC_WEB_SEARCH_TOOL],
        )
        latency_ms = (time.time() - start) * 1000

        content = "".join(
            _field(b, "text") or ""
            for b in response.content
            if _field(b, "type") == "text"
        )
        citations = parse_anthropic_grounded(list(response.content), query=prompt)

        search_count = 0
        usage = getattr(response, "usage", None)
        server_tool_use = getattr(usage, "server_tool_use", None) if usage else None
        if server_tool_use is not None:
            search_count = getattr(server_tool_use, "web_search_requests", 0) or 0

        return GroundedResponse(
            content=content,
            citations=citations,
            model=use_model,
            provider=Provider.ANTHROPIC.value,
            latency_ms=latency_ms,
            cost_usd=None,  # token+search cost not computed here; billed to user
            search_count=search_count,
        )


# Providers with a grounded adapter. Others fall back to base completion (and
# the scan is honestly labelled base_model). OpenAI/Gemini land here next.
_GROUNDED_CLIENTS: dict[Provider, type[GroundedClient]] = {
    Provider.ANTHROPIC: AnthropicGroundedClient,
}


def get_grounded_client(provider: Provider) -> GroundedClient | None:
    """Return a grounded client for the provider, or None if unsupported."""
    cls = _GROUNDED_CLIENTS.get(provider)
    return cls() if cls is not None else None
