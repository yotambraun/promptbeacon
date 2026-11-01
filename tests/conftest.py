"""Pytest configuration and fixtures."""

from datetime import datetime

import pytest

from promptbeacon.core.clock import utc_now
from promptbeacon.core.config import Provider, model_env_var
from promptbeacon.core.schemas import (
    BrandMention,
    CompetitorScore,
    ProviderResult,
    Report,
    SentimentBreakdown,
    VisibilityMetrics,
)
from promptbeacon.storage.database import Database

_PROVIDER_ENV_VARS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "MISTRAL_API_KEY",
    "COHERE_API_KEY",
    "PERPLEXITY_API_KEY",
    "TAVILY_API_KEY",
    "PROMPTBEACON_DEMO",
)


@pytest.fixture(autouse=True)
def _no_real_provider_credentials(monkeypatch):
    """Tests never use real keys, even if a developer's .env defines them.

    PromptBeacon loads .env on import, so without this a test that forgot to
    mock the provider could make a real, billed request. Tests that need a key
    set a fake one with monkeypatch.
    """
    for var in _PROVIDER_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    for provider in Provider:
        monkeypatch.delenv(model_env_var(provider), raising=False)


@pytest.fixture(autouse=True)
def _isolated_promptbeacon_home(tmp_path_factory, monkeypatch):
    """Keep CLI history writes out of the real ~/.promptbeacon during tests."""
    monkeypatch.setenv(
        "PROMPTBEACON_HOME", str(tmp_path_factory.mktemp("promptbeacon-home"))
    )


@pytest.fixture
def sample_mention():
    """Create a sample brand mention."""
    return BrandMention(
        brand_name="TestBrand",
        sentiment="positive",
        position=0,
        context="TestBrand is a great company with excellent products.",
        confidence=0.95,
        is_recommendation=True,
    )


@pytest.fixture
def sample_provider_result(sample_mention):
    """Create a sample provider result."""
    return ProviderResult(
        provider="openai",
        model="gpt-6-luna",
        prompt="What are the best brands?",
        response="I recommend TestBrand for their excellent products.",
        mentions=[sample_mention],
        latency_ms=150.0,
        cost_usd=0.001,
        timestamp=utc_now(),
    )


@pytest.fixture
def sample_sentiment():
    """Create a sample sentiment breakdown."""
    return SentimentBreakdown(
        positive=0.6,
        neutral=0.3,
        negative=0.1,
    )


@pytest.fixture
def sample_metrics(sample_sentiment):
    """Create sample visibility metrics."""
    return VisibilityMetrics(
        visibility_score=75.0,
        mention_count=10,
        recommendation_rate=0.3,
        average_position=1.5,
        sentiment=sample_sentiment,
    )


@pytest.fixture
def sample_competitor_score(sample_sentiment):
    """Create a sample competitor score."""
    return CompetitorScore(
        brand_name="CompetitorA",
        visibility_score=65.0,
        mention_count=8,
        sentiment=sample_sentiment,
    )


@pytest.fixture
def sample_report(
    sample_provider_result, sample_sentiment, sample_metrics, sample_competitor_score
):
    """Create a sample report."""
    return Report(
        brand="TestBrand",
        visibility_score=75.0,
        mention_count=10,
        sentiment_breakdown=sample_sentiment,
        competitor_comparison={"CompetitorA": sample_competitor_score},
        provider_results=[sample_provider_result],
        metrics=sample_metrics,
        timestamp=datetime(2024, 1, 15, 12, 0, 0),
        scan_duration_seconds=5.0,
        total_cost_usd=0.01,
    )


@pytest.fixture
def in_memory_db():
    """Create an in-memory database for testing."""
    db = Database()
    yield db
    db.close()


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary file-based database for testing."""
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    yield db
    db.close()
