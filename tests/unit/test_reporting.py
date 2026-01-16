"""Tests for reporting module."""

import pytest
import json
from datetime import datetime

from promptbeacon.core.schemas import (
    Report,
    ProviderResult,
    SentimentBreakdown,
    VisibilityMetrics,
    BrandMention,
    CompetitorScore,
)
from promptbeacon.reporting.formats import (
    to_json,
    to_dict,
    to_csv,
    to_markdown,
    to_html,
)
from promptbeacon.reporting.report import (
    ReportBuilder,
    create_report_builder,
    merge_reports,
)


@pytest.fixture
def sample_report():
    """Create a sample report for testing."""
    return Report(
        brand="TestBrand",
        visibility_score=75.0,
        mention_count=10,
        sentiment_breakdown=SentimentBreakdown(
            positive=0.6,
            neutral=0.3,
            negative=0.1,
        ),
        competitor_comparison={
            "CompetitorA": CompetitorScore(
                brand_name="CompetitorA",
                visibility_score=65.0,
                mention_count=8,
                sentiment=SentimentBreakdown(
                    positive=0.5,
                    neutral=0.4,
                    negative=0.1,
                ),
            )
        },
        provider_results=[
            ProviderResult(
                provider="openai",
                model="gpt-4",
                prompt="test prompt",
                response="TestBrand is great.",
                mentions=[
                    BrandMention(
                        brand_name="TestBrand",
                        sentiment="positive",
                        position=0,
                        context="TestBrand is great.",
                    )
                ],
                latency_ms=100.0,
                cost_usd=0.001,
            )
        ],
        metrics=VisibilityMetrics(
            visibility_score=75.0,
            mention_count=10,
        ),
        timestamp=datetime(2024, 1, 15, 12, 0, 0),
        scan_duration_seconds=5.0,
        total_cost_usd=0.01,
    )


class TestReportFormats:
    """Tests for report export formats."""

    def test_to_json(self, sample_report):
        result = to_json(sample_report)

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["brand"] == "TestBrand"
        assert parsed["visibility_score"] == 75.0

    def test_to_dict(self, sample_report):
        result = to_dict(sample_report)

        assert isinstance(result, dict)
        assert result["brand"] == "TestBrand"
        assert result["visibility_score"] == 75.0

    def test_to_csv(self, sample_report):
        result = to_csv(sample_report)

        assert isinstance(result, str)
        assert "brand,TestBrand" in result
        assert "visibility_score,75.0" in result

    def test_to_markdown(self, sample_report):
        result = to_markdown(sample_report)

        assert isinstance(result, str)
        assert "# Brand Visibility Report: TestBrand" in result
        assert "75.0" in result
        assert "Competitor Comparison" in result

    def test_to_html(self, sample_report):
        result = to_html(sample_report)

        assert isinstance(result, str)
        assert "<!DOCTYPE html>" in result
        assert "TestBrand" in result
        assert "75.0" in result


class TestReportBuilder:
    """Tests for ReportBuilder."""

    def test_create_builder(self, sample_report):
        builder = ReportBuilder(sample_report)

        assert builder.report == sample_report

    def test_summary(self, sample_report):
        builder = create_report_builder(sample_report)
        summary = builder.summary()

        assert isinstance(summary, str)
        assert "TestBrand" in summary
        assert "75.0" in summary

    def test_executive_summary(self, sample_report):
        builder = create_report_builder(sample_report)
        summary = builder.executive_summary()

        assert isinstance(summary, str)
        assert "TestBrand" in summary
        assert "strong" in summary.lower()  # 75.0 is strong visibility


class TestMergeReports:
    """Tests for merging reports."""

    def test_merge_single_report(self, sample_report):
        result = merge_reports([sample_report])

        assert result == sample_report

    def test_merge_empty(self):
        result = merge_reports([])

        assert result is None

    def test_merge_multiple_reports(self, sample_report):
        report2 = sample_report.model_copy(
            update={
                "visibility_score": 80.0,
                "timestamp": datetime(2024, 1, 16, 12, 0, 0),
            }
        )

        result = merge_reports([sample_report, report2])

        assert result is not None
        # Average of 75.0 and 80.0
        assert result.visibility_score == 77.5
