"""Storage schema definitions for DuckDB."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# SQL schema for DuckDB tables
SCHEMA_SQL = """
-- Scans table: stores metadata about each scan
CREATE TABLE IF NOT EXISTS scans (
    id VARCHAR PRIMARY KEY,
    brand VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    visibility_score DOUBLE NOT NULL,
    mention_count INTEGER NOT NULL,
    sentiment_positive DOUBLE DEFAULT 0.0,
    sentiment_neutral DOUBLE DEFAULT 0.0,
    sentiment_negative DOUBLE DEFAULT 0.0,
    scan_duration_seconds DOUBLE DEFAULT 0.0,
    total_cost_usd DOUBLE,
    providers_used VARCHAR[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Provider results table: stores individual LLM query results
CREATE TABLE IF NOT EXISTS provider_results (
    id VARCHAR PRIMARY KEY,
    scan_id VARCHAR NOT NULL REFERENCES scans(id),
    provider VARCHAR NOT NULL,
    model VARCHAR NOT NULL,
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    latency_ms DOUBLE NOT NULL,
    cost_usd DOUBLE,
    error VARCHAR,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Brand mentions table: stores extracted brand mentions
CREATE TABLE IF NOT EXISTS brand_mentions (
    id VARCHAR PRIMARY KEY,
    result_id VARCHAR NOT NULL REFERENCES provider_results(id),
    scan_id VARCHAR NOT NULL REFERENCES scans(id),
    brand_name VARCHAR NOT NULL,
    sentiment VARCHAR NOT NULL,
    position INTEGER NOT NULL,
    context TEXT NOT NULL,
    confidence DOUBLE DEFAULT 1.0,
    is_recommendation BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Competitor scores table: stores competitor comparison data
CREATE TABLE IF NOT EXISTS competitor_scores (
    id VARCHAR PRIMARY KEY,
    scan_id VARCHAR NOT NULL REFERENCES scans(id),
    brand_name VARCHAR NOT NULL,
    visibility_score DOUBLE NOT NULL,
    mention_count INTEGER NOT NULL,
    sentiment_positive DOUBLE DEFAULT 0.0,
    sentiment_neutral DOUBLE DEFAULT 0.0,
    sentiment_negative DOUBLE DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_scans_brand ON scans(brand);
CREATE INDEX IF NOT EXISTS idx_scans_timestamp ON scans(timestamp);
CREATE INDEX IF NOT EXISTS idx_scans_brand_timestamp ON scans(brand, timestamp);
CREATE INDEX IF NOT EXISTS idx_provider_results_scan_id ON provider_results(scan_id);
CREATE INDEX IF NOT EXISTS idx_brand_mentions_scan_id ON brand_mentions(scan_id);
CREATE INDEX IF NOT EXISTS idx_brand_mentions_brand_name ON brand_mentions(brand_name);
CREATE INDEX IF NOT EXISTS idx_competitor_scores_scan_id ON competitor_scores(scan_id);
"""


class ScanRecord(BaseModel):
    """Record for a stored scan."""

    id: str
    brand: str
    timestamp: datetime
    visibility_score: float = Field(ge=0.0, le=100.0)
    mention_count: int = Field(ge=0)
    sentiment_positive: float = Field(default=0.0, ge=0.0, le=1.0)
    sentiment_neutral: float = Field(default=0.0, ge=0.0, le=1.0)
    sentiment_negative: float = Field(default=0.0, ge=0.0, le=1.0)
    scan_duration_seconds: float = Field(default=0.0, ge=0)
    total_cost_usd: float | None = None
    providers_used: list[str] = Field(default_factory=list)


class ProviderResultRecord(BaseModel):
    """Record for a stored provider result."""

    id: str
    scan_id: str
    provider: str
    model: str
    prompt: str
    response: str
    latency_ms: float = Field(ge=0)
    cost_usd: float | None = None
    error: str | None = None
    timestamp: datetime


class BrandMentionRecord(BaseModel):
    """Record for a stored brand mention."""

    id: str
    result_id: str
    scan_id: str
    brand_name: str
    sentiment: str
    position: int = Field(ge=0)
    context: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_recommendation: bool = False


class CompetitorScoreRecord(BaseModel):
    """Record for a stored competitor score."""

    id: str
    scan_id: str
    brand_name: str
    visibility_score: float = Field(ge=0.0, le=100.0)
    mention_count: int = Field(ge=0)
    sentiment_positive: float = Field(default=0.0, ge=0.0, le=1.0)
    sentiment_neutral: float = Field(default=0.0, ge=0.0, le=1.0)
    sentiment_negative: float = Field(default=0.0, ge=0.0, le=1.0)
