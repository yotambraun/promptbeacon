"""Run and instrument the observable agentic-search funnel."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from promptbeacon.funnel.backends import SearchBackend
from promptbeacon.funnel.planner import generate_sub_queries, llm_generate_sub_queries
from promptbeacon.funnel.reranker import lexical_rerank, llm_rerank
from promptbeacon.funnel.schemas import FunnelReport, RetrievedSource, SubQueryResult


def _text_has_any(text: str, terms: list[str]) -> bool:
    low = text.lower()
    return any(term.lower() in low for term in terms if term)


def _build_report(
    brand: str,
    prompt: str,
    sub_queries: list[str],
    results: list[SubQueryResult],
) -> FunnelReport:
    n = len(results)
    retrieved = sum(1 for r in results if r.target_retrieved)
    after_rerank = sum(1 for r in results if r.target_after_rerank)
    cited = sum(1 for r in results if r.target_cited)

    coverage = retrieved / n if n else 0.0
    rerank_survival = after_rerank / retrieved if retrieved else 0.0
    cite_ratio = cited / retrieved if retrieved else 0.0

    # Where does the brand drop out most across the funnel?
    drops = {
        "retrieval": n - retrieved,
        "rerank": retrieved - after_rerank,
        "citation": after_rerank - cited,
    }
    stage_failure = (
        max(drops, key=lambda k: drops[k]) if any(drops.values()) else "none"
    )

    return FunnelReport(
        brand=brand,
        prompt=prompt,
        sub_queries=sub_queries,
        sub_query_results=results,
        sub_query_coverage=round(coverage, 4),
        rerank_survival_rate=round(rerank_survival, 4),
        retrieval_to_citation_ratio=round(cite_ratio, 4),
        stage_failure=stage_failure,
    )


async def run_funnel(
    brand: str,
    prompt: str,
    *,
    backend: SearchBackend,
    competitors: list[str] | None = None,
    n_sub_queries: int = 8,
    retrieve_k: int = 8,
    top_k: int = 5,
    cite_k: int = 3,
    complete: Callable[[str], Awaitable[str]] | None = None,
) -> FunnelReport:
    """Run the funnel for one prompt and report where the brand survives or dies.

    Stages: fan out the prompt into sub-queries, retrieve per sub-query (the
    backend), rerank to the top ``top_k``, and "cite" the top ``cite_k``. The
    brand's presence is tracked at each stage to compute coverage, rerank
    survival, retrieval-to-citation, and the dominant stage failure.

    Args:
        brand: Target brand.
        prompt: Buyer-intent prompt to fan out.
        backend: Search backend (mock for demo, Tavily for live).
        competitors: Competitor brands (tracked for context).
        n_sub_queries: Fan-out width.
        retrieve_k: Results retrieved per sub-query.
        top_k: Sources kept after reranking.
        cite_k: Sources that survive to citation.
        complete: Optional async ``prompt -> text`` LLM callable. When provided,
            the funnel uses an LLM planner (fan-out) and an LLM-judge reranker
            instead of the deterministic defaults; both fall back gracefully.

    Returns:
        A FunnelReport.
    """
    competitors = competitors or []
    brand_terms = [brand]
    if complete is not None:
        sub_queries = await llm_generate_sub_queries(prompt, n_sub_queries, complete)
    else:
        sub_queries = generate_sub_queries(prompt, n_sub_queries)

    async def run_one(sub_query: str) -> SubQueryResult:
        raw = await backend.search(sub_query, max_results=retrieve_k)
        retrieved = [
            RetrievedSource(
                url=item.url,
                title=item.title,
                snippet=item.snippet,
                mentions_target=_text_has_any(
                    f"{item.title} {item.snippet}", brand_terms
                ),
                mentions_competitor=_text_has_any(
                    f"{item.title} {item.snippet}", competitors
                ),
            )
            for item in raw
        ]
        target_retrieved = any(s.mentions_target for s in retrieved)
        if complete is not None:
            ranked = await llm_rerank(sub_query, retrieved, top_k, complete)
        else:
            ranked = lexical_rerank(sub_query, retrieved, top_k=top_k)
        target_after_rerank = any(s.mentions_target for s in ranked)
        cited = ranked[:cite_k]
        target_cited = any(s.mentions_target for s in cited)
        return SubQueryResult(
            sub_query=sub_query,
            retrieved=retrieved,
            target_retrieved=target_retrieved,
            target_after_rerank=target_after_rerank,
            target_cited=target_cited,
        )

    results = list(await asyncio.gather(*[run_one(sq) for sq in sub_queries]))
    return _build_report(brand, prompt, sub_queries, results)
