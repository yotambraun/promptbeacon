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


def parse_openai_grounded(
    output_items: list[Any], full_text: str, query: str
) -> list[Citation]:
    """Parse OpenAI Responses ``web_search`` output into Citations.

    Citations come from ``url_citation`` annotations on ``output_text`` content.
    OpenAI exposes only cited URLs (not the full retrieved set), so every
    citation here is ``retrieved_but_uncited=False``.
    """
    seen: dict[str, str] = {}
    order: list[str] = []
    for item in output_items:
        if _field(item, "type") != "message":
            continue
        for content in _field(item, "content") or []:
            if _field(content, "type") != "output_text":
                continue
            text = _field(content, "text") or full_text or ""
            for ann in _field(content, "annotations") or []:
                if _field(ann, "type") != "url_citation":
                    continue
                url = _field(ann, "url")
                if not url or url in seen:
                    continue
                start, end = _field(ann, "start_index"), _field(ann, "end_index")
                ctx = ""
                if (
                    isinstance(start, int)
                    and isinstance(end, int)
                    and 0 <= start < end <= len(text)
                ):
                    ctx = text[start:end]
                seen[url] = ctx
                order.append(url)

    citations: list[Citation] = []
    for rank, url in enumerate(order, start=1):
        domain = _extract_domain(url)
        citations.append(
            Citation(
                url=url,
                source_name=domain,
                context=(seen[url] or "")[:300],
                source_rank=rank,
                source_type=classify_source_type(domain),
                query=query,
                retrieved_but_uncited=False,
            )
        )
    return citations


def parse_gemini_grounded(candidate: Any, query: str) -> list[Citation]:
    """Parse Gemini ``grounding_metadata`` into Citations.

    ``grounding_chunks`` are the retrieved sources; chunk indices referenced by
    ``grounding_supports`` are the cited ones, so chunks never referenced are
    marked ``retrieved_but_uncited``.
    """
    gm = _field(candidate, "grounding_metadata")
    if gm is None:
        return []
    chunks = _field(gm, "grounding_chunks") or []
    supports = _field(gm, "grounding_supports") or []

    cited_indices: set[int] = set()
    for support in supports:
        for idx in _field(support, "grounding_chunk_indices") or []:
            cited_indices.add(idx)

    citations: list[Citation] = []
    for i, chunk in enumerate(chunks):
        web = _field(chunk, "web")
        url = _field(web, "uri") if web is not None else None
        if not url:
            continue
        domain = _extract_domain(url)
        citations.append(
            Citation(
                url=url,
                source_name=domain,
                context="",
                source_rank=i + 1,
                source_type=classify_source_type(domain),
                query=query,
                retrieved_but_uncited=i not in cited_indices,
            )
        )
    return citations


def parse_perplexity_grounded(citation_urls: Any, query: str) -> list[Citation]:
    """Parse Perplexity's top-level ``citations`` URL list into Citations."""
    citations: list[Citation] = []
    seen: set[str] = set()
    for rank, url in enumerate(citation_urls or [], start=1):
        if not isinstance(url, str) or url in seen:
            continue
        seen.add(url)
        domain = _extract_domain(url)
        citations.append(
            Citation(
                url=url,
                source_name=domain,
                source_rank=rank,
                source_type=classify_source_type(domain),
                query=query,
                retrieved_but_uncited=False,
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


class OpenAIGroundedClient(GroundedClient):
    """Web-grounded client using the official ``openai`` SDK (Responses API)."""

    provider = Provider.OPENAI

    def __init__(self, model: str | None = None, timeout: float = 60.0) -> None:
        self._model = model or "gpt-4o-mini"
        self.timeout = timeout

    def is_available(self) -> bool:
        if get_api_key(Provider.OPENAI) is None:
            return False
        try:
            import openai  # noqa: F401
        except ImportError:
            return False
        return True

    async def complete_grounded(
        self, prompt: str, *, model: str | None = None, max_tokens: int = 2048
    ) -> GroundedResponse:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(timeout=self.timeout)
        use_model = model or self._model
        start = time.time()
        response = await client.responses.create(
            model=use_model,
            tools=[{"type": "web_search"}],
            input=prompt,
            max_output_tokens=max_tokens,
        )
        latency_ms = (time.time() - start) * 1000

        output = list(getattr(response, "output", None) or [])
        content = getattr(response, "output_text", "") or ""
        citations = parse_openai_grounded(output, content, query=prompt)
        search_count = sum(
            1 for item in output if _field(item, "type") == "web_search_call"
        )
        return GroundedResponse(
            content=content,
            citations=citations,
            model=use_model,
            provider=Provider.OPENAI.value,
            latency_ms=latency_ms,
            cost_usd=None,
            search_count=search_count,
        )


class GeminiGroundedClient(GroundedClient):
    """Web-grounded client using the official ``google-genai`` SDK (grounding)."""

    provider = Provider.GOOGLE

    def __init__(self, model: str | None = None, timeout: float = 60.0) -> None:
        self._model = model or "gemini-2.0-flash"
        self.timeout = timeout

    def is_available(self) -> bool:
        if get_api_key(Provider.GOOGLE) is None:
            return False
        try:
            from google import genai  # noqa: F401
        except ImportError:
            return False
        return True

    async def complete_grounded(
        self, prompt: str, *, model: str | None = None, max_tokens: int = 2048
    ) -> GroundedResponse:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=get_api_key(Provider.GOOGLE))
        use_model = model or self._model
        start = time.time()
        response = await client.aio.models.generate_content(
            model=use_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                max_output_tokens=max_tokens,
            ),
        )
        latency_ms = (time.time() - start) * 1000

        content = getattr(response, "text", "") or ""
        candidates = getattr(response, "candidates", None) or []
        citations = (
            parse_gemini_grounded(candidates[0], query=prompt) if candidates else []
        )
        return GroundedResponse(
            content=content,
            citations=citations,
            model=use_model,
            provider=Provider.GOOGLE.value,
            latency_ms=latency_ms,
            cost_usd=None,
            search_count=1 if citations else 0,
        )


class PerplexityGroundedClient(GroundedClient):
    """Web-grounded client for Perplexity sonar (web-grounded by default).

    Perplexity is OpenAI-compatible and returns a top-level ``citations`` list,
    so we use the ``openai`` SDK pointed at the Perplexity endpoint.
    """

    provider = Provider.PERPLEXITY

    def __init__(self, model: str | None = None, timeout: float = 60.0) -> None:
        self._model = model or "sonar"
        self.timeout = timeout

    def is_available(self) -> bool:
        if get_api_key(Provider.PERPLEXITY) is None:
            return False
        try:
            import openai  # noqa: F401
        except ImportError:
            return False
        return True

    async def complete_grounded(
        self, prompt: str, *, model: str | None = None, max_tokens: int = 2048
    ) -> GroundedResponse:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=get_api_key(Provider.PERPLEXITY),
            base_url="https://api.perplexity.ai",
            timeout=self.timeout,
        )
        use_model = model or self._model
        start = time.time()
        response = await client.chat.completions.create(
            model=use_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        latency_ms = (time.time() - start) * 1000

        content = response.choices[0].message.content or ""
        # Perplexity returns `citations` (a list of URLs) at the top level — a
        # non-standard field, so read it defensively.
        citation_urls = getattr(response, "citations", None)
        if citation_urls is None:
            extra = getattr(response, "model_extra", None)
            if isinstance(extra, dict):
                citation_urls = extra.get("citations")
        citations = parse_perplexity_grounded(citation_urls, query=prompt)
        return GroundedResponse(
            content=content,
            citations=citations,
            model=use_model,
            provider=Provider.PERPLEXITY.value,
            latency_ms=latency_ms,
            cost_usd=None,
            search_count=1 if citations else 0,
        )


# Providers with a native grounded adapter. Others (Mistral, Cohere) fall back
# to base completion and the scan is honestly labelled base_model.
_GROUNDED_CLIENTS: dict[Provider, type[GroundedClient]] = {
    Provider.ANTHROPIC: AnthropicGroundedClient,
    Provider.OPENAI: OpenAIGroundedClient,
    Provider.GOOGLE: GeminiGroundedClient,
    Provider.PERPLEXITY: PerplexityGroundedClient,
}


def get_grounded_client(provider: Provider) -> GroundedClient | None:
    """Return a grounded client for the provider, or None if unsupported."""
    cls = _GROUNDED_CLIENTS.get(provider)
    return cls() if cls is not None else None
