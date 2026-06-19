"""Glass-box agentic funnel — see where your brand drops out.

Citation trackers only see the final answer. This models the agentic-search
funnel locally (fan-out -> retrieve -> rerank -> cite) and reports where the
brand survives or dies.

Keyless: runs with the mock search backend. For live web search, set
TAVILY_API_KEY and swap in TavilyBackend.

    python examples/funnel_demo.py
"""

from __future__ import annotations

import asyncio

from promptbeacon.funnel import MockSearchBackend, run_funnel


async def main() -> None:
    backend = MockSearchBackend("Nike", competitors=["Adidas", "Puma"])
    report = await run_funnel(
        "Nike",
        "What are the best running shoes?",
        backend=backend,
        competitors=["Adidas", "Puma"],
        n_sub_queries=8,
    )

    print(f"Prompt: {report.prompt}")
    print(f"Sub-queries: {report.sub_query_count}")
    print(f"Coverage (brand retrieved):  {report.sub_query_coverage:.0%}")
    print(f"Rerank survival:             {report.rerank_survival_rate:.0%}")
    print(f"Retrieval -> citation:       {report.retrieval_to_citation_ratio:.0%}")
    print(f"Dominant drop-off stage:     {report.stage_failure}\n")

    print(f"{'sub-query':<34} retrieved reranked cited")
    for sq in report.sub_query_results:

        def mark(flag: bool) -> str:
            return "yes" if flag else "-"

        print(
            f"{sq.sub_query:<34} "
            f"{mark(sq.target_retrieved):<9} "
            f"{mark(sq.target_after_rerank):<8} "
            f"{mark(sq.target_cited)}"
        )


if __name__ == "__main__":
    asyncio.run(main())
