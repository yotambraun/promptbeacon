"""Lightweight, dependency-free lexical reranker for the funnel.

Scores each source by how many query tokens appear in its title+snippet and
keeps the top K (stable sort, so ties preserve retrieval order). This is the
zero-dependency default; an LLM-judge or cross-encoder reranker can replace it
for higher fidelity without changing the pipeline.
"""

from __future__ import annotations

import re

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
