"""Observable agentic-search funnel ("glass-box" GEO measurement).

Citation trackers only see the *survivors* of an agentic-search funnel
(plan -> fan-out -> retrieve -> rerank -> cite). This package models that funnel
locally and instruments every stage, so you can see *where* a brand drops out —
retrieved-but-not-reranked, reranked-but-not-cited, or never retrieved at all.

It is a deliberate *model* of agentic search, not a clone of any consumer
product; the honesty tier is ``funnel_model``.
"""

from __future__ import annotations

from promptbeacon.funnel.backends import (
    MockSearchBackend,
    SearchBackend,
    SearchResult,
    TavilyBackend,
)
from promptbeacon.funnel.pipeline import run_funnel
from promptbeacon.funnel.planner import generate_sub_queries, llm_generate_sub_queries
from promptbeacon.funnel.reranker import lexical_rerank, llm_rerank
from promptbeacon.funnel.schemas import FunnelReport, RetrievedSource, SubQueryResult

__all__ = [
    "FunnelReport",
    "MockSearchBackend",
    "RetrievedSource",
    "SearchBackend",
    "SearchResult",
    "SubQueryResult",
    "TavilyBackend",
    "generate_sub_queries",
    "lexical_rerank",
    "llm_generate_sub_queries",
    "llm_rerank",
    "run_funnel",
]
