"""Lightweight, dependency-free lexical reranker for the funnel.

Scores each source by how many query tokens appear in its title+snippet and
keeps the top K (stable sort, so ties preserve retrieval order). This is the
zero-dependency default; an LLM-judge or cross-encoder reranker can replace it
for higher fidelity without changing the pipeline.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable

from promptbeacon.funnel.schemas import RetrievedSource

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall(text.lower()))


def lexical_rerank(
    query: str, sources: list[RetrievedSource], top_k: int = 5
) -> list[RetrievedSource]:
    """Return the top ``top_k`` sources by query-token overlap (stable)."""
    query_tokens = _tokens(query)

    def overlap(source: RetrievedSource) -> int:
        return len(query_tokens & _tokens(f"{source.title} {source.snippet}"))

    ranked = sorted(sources, key=overlap, reverse=True)
    return ranked[:top_k]


async def llm_rerank(
    query: str,
    sources: list[RetrievedSource],
    top_k: int,
    complete: Callable[[str], Awaitable[str]],
) -> list[RetrievedSource]:
    """LLM-judge reranker: ask a model to order sources by relevance.

    ``complete`` is any async ``prompt -> text`` callable. Falls back to
    :func:`lexical_rerank` on any error or unparseable output.
    """
    if not sources:
        return []
    listing = "\n".join(
        f"{i}: {s.title} — {s.snippet[:120]}" for i, s in enumerate(sources)
    )
    instruction = (
        f'Query: "{query}"\n'
        "Rank these sources by relevance to the query, most relevant first.\n"
        f"{listing}\n\n"
        f"Return ONLY the top {top_k} source numbers as a comma-separated list "
        "(e.g. 3,0,5)."
    )
    try:
        text = await complete(instruction)
        ordered: list[RetrievedSource] = []
        seen: set[int] = set()
        for token in re.findall(r"\d+", text):
            idx = int(token)
            if 0 <= idx < len(sources) and idx not in seen:
                seen.add(idx)
                ordered.append(sources[idx])
            if len(ordered) >= top_k:
                break
        if ordered:
            return ordered
    except Exception:  # noqa: BLE001 — any failure falls back to lexical
        pass
    return lexical_rerank(query, sources, top_k)
