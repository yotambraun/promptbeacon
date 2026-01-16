"""Tests for storage module."""

import pytest
from datetime import datetime

from promptbeacon.storage.database import Database
from promptbeacon.core.schemas import (
    BrandMention,
    ProviderResult,
    Report,
    SentimentBreakdown,
    VisibilityMetrics,
)


@pytest.fixture
def db():
    """Create an in-memory database for testing."""
    database = Database()
    yield database
    database.close()


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
        timestamp=datetime.utcnow(),
        scan_duration_seconds=5.0,
        total_cost_usd=0.01,
    )


class TestDatabase:
    """Tests for Database class."""

    def test_create_database(self, db):
        assert db is not None

    def test_save_and_retrieve_report(self, db, sample_report):
        scan_id = db.save_report(sample_report)

        assert scan_id is not None

        # Retrieve the latest scan
        latest = db.get_latest_scan(sample_report.brand)

        assert latest is not None
        assert latest.brand == sample_report.brand
        assert latest.visibility_score == sample_report.visibility_score

    def test_get_history(self, db, sample_report):
        # Save multiple reports
        db.save_report(sample_report)
        db.save_report(sample_report)

        history = db.get_history(sample_report.brand, days=30)

        assert history.brand == sample_report.brand
        assert len(history.data_points) >= 2

    def test_get_latest_scan_not_found(self, db):
        result = db.get_latest_scan("NonExistentBrand")

        assert result is None

    def test_get_scan_count(self, db, sample_report):
        db.save_report(sample_report)
        db.save_report(sample_report)

        count = db.get_scan_count(sample_report.brand)

        assert count >= 2

    def test_compare_with_previous(self, db, sample_report):
        from datetime import timedelta

        # Save first report (older)
        db.save_report(sample_report)

        # Modify score and timestamp for second report (newer)
        modified_report = sample_report.model_copy(
            update={
                "visibility_score": 80.0,
                "timestamp": sample_report.timestamp + timedelta(hours=1),
            }
        )
        db.save_report(modified_report)

        comparison = db.compare_with_previous(sample_report.brand)

        assert comparison is not None
        assert comparison.current_score == 80.0
        assert comparison.previous_score == 75.0
        assert comparison.score_change == 5.0

    def test_context_manager(self):
        with Database() as db:
            assert db is not None

    def test_empty_history(self, db):
        history = db.get_history("NonExistentBrand", days=30)

        assert history.brand == "NonExistentBrand"
        assert len(history.data_points) == 0
