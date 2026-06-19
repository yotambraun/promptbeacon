"""Tests for the observable agentic-search funnel."""

from __future__ import annotations

import asyncio

import pytest

from promptbeacon.funnel import (
    MockSearchBackend,
    generate_sub_queries,
    run_funnel,
)
from promptbeacon.funnel.reranker import lexical_rerank
from promptbeacon.funnel.schemas import RetrievedSource


def test_generate_sub_queries():
    queries = generate_sub_queries("What are the best running shoes?", 8)
    assert len(queries) == 8
    assert len(set(queries)) == 8  # distinct
    assert all("running shoes" in q for q in queries)


def test_generate_sub_queries_rejects_bad_n():
    with pytest.raises(ValueError):
        generate_sub_queries("x", 0)


def test_lexical_rerank_orders_by_overlap():
    query = "best running shoes"
    sources = [
        RetrievedSource(title="cooking recipes", snippet="food and drink"),
        RetrievedSource(title="best running shoes review", snippet="running shoes"),
        RetrievedSource(title="best shoes", snippet="shoes guide"),
    ]
    ranked = lexical_rerank(query, sources, top_k=2)
    assert ranked[0].title == "best running shoes review"  # highest overlap
    assert len(ranked) == 2


def test_run_funnel_mock_is_deterministic_and_in_range():
    report = asyncio.run(
        run_funnel(
            "Nike",
            "What are the best running shoes?",
            backend=MockSearchBackend("Nike", competitors=["Adidas"]),
            competitors=["Adidas"],
            n_sub_queries=8,
        )
    )
    assert report.brand == "Nike"
    assert report.sub_query_count == 8
    assert report.sub_query_coverage > 0.0  # mock weaves the brand in
    assert 0.0 <= report.sub_query_coverage <= 1.0
    assert 0.0 <= report.rerank_survival_rate <= 1.0
    assert 0.0 <= report.retrieval_to_citation_ratio <= 1.0
    assert report.stage_failure in {"retrieval", "rerank", "citation", "none"}

    # Same inputs -> same metrics (reproducible).
    report2 = asyncio.run(
        run_funnel(
            "Nike",
            "What are the best running shoes?",
            backend=MockSearchBackend("Nike", competitors=["Adidas"]),
            n_sub_queries=8,
        )
    )
    assert report.sub_query_coverage == report2.sub_query_coverage
    assert report.stage_failure == report2.stage_failure


def test_run_funnel_brand_never_retrieved_is_retrieval_failure():
    # The backend only ever weaves in "Adidas", so "Nike" is never retrieved.
    report = asyncio.run(
        run_funnel(
            "Nike",
            "What are the best running shoes?",
            backend=MockSearchBackend("Adidas"),
            n_sub_queries=8,
        )
    )
    assert report.sub_query_coverage == 0.0
    assert report.retrieval_to_citation_ratio == 0.0
    assert report.stage_failure == "retrieval"


def test_funnel_marks_source_presence():
    report = asyncio.run(
        run_funnel(
            "Nike",
            "What are the best running shoes?",
            backend=MockSearchBackend("Nike", competitors=["Adidas"]),
            competitors=["Adidas"],
            n_sub_queries=4,
        )
    )
    # At least one retrieved source somewhere should mention the target brand.
    assert any(
        src.mentions_target for sq in report.sub_query_results for src in sq.retrieved
    )
