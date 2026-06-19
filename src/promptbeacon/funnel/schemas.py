"""Schemas for the observable agentic-search funnel."""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field


class RetrievedSource(BaseModel):
    """A single source returned by a search backend for a sub-query."""

    url: str | None = Field(default=None)
    title: str = Field(default="")
    snippet: str = Field(default="")
    mentions_target: bool = Field(
        default=False, description="The target brand appears in this source"
    )
    mentions_competitor: bool = Field(
        default=False, description="A competitor appears in this source"
    )


class SubQueryResult(BaseModel):
    """How the target brand fared for one fanned-out sub-query."""

    sub_query: str
    retrieved: list[RetrievedSource] = Field(default_factory=list)
    target_retrieved: bool = Field(
        default=False, description="Brand appeared in the retrieved set"
    )
    target_after_rerank: bool = Field(
        default=False, description="Brand survived into the top-K after reranking"
    )
    target_cited: bool = Field(
        default=False, description="Brand survived into the final cited set"
    )


class FunnelReport(BaseModel):
    """Where a brand survives or dies across the agentic-search funnel.

    Unlike citation tracking (which sees only the final answer), this reports
    the funnel itself: how much of the query fan-out retrieves the brand, how
    much survives reranking, and how much is ultimately cited.
    """

    brand: str
    prompt: str
    sub_queries: list[str] = Field(default_factory=list)
    sub_query_results: list[SubQueryResult] = Field(default_factory=list)

    sub_query_coverage: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of sub-queries whose retrieval set includes the brand",
    )
    rerank_survival_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Of sub-queries where the brand was retrieved, the fraction "
        "where it survived reranking",
    )
    retrieval_to_citation_ratio: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Of sub-queries where the brand was retrieved, the fraction "
        "where it survived to citation",
    )
    stage_failure: str = Field(
        default="none",
        description="Where the brand drops out most: retrieval, rerank, "
        "citation, or none",
    )
    measurement_tier: str = Field(
        default="funnel_model",
        description="A local model of agentic search — not a consumer product",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sub_query_count(self) -> int:
        """Number of fanned-out sub-queries."""
        return len(self.sub_queries)
