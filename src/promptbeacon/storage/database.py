"""DuckDB database operations for PromptBeacon."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb

from promptbeacon.core.exceptions import StorageError
from promptbeacon.core.schemas import (
    BrandMention,
    CompetitorScore,
    HistoricalDataPoint,
    HistoryReport,
    ProviderResult,
    Report,
    ScanComparison,
    SentimentBreakdown,
)
from promptbeacon.storage.models import (
    SCHEMA_SQL,
    BrandMentionRecord,
    CompetitorScoreRecord,
    ProviderResultRecord,
    ScanRecord,
)
from promptbeacon.storage.queries import (
    DELETE_OLD_SCANS_QUERY,
    GET_AVERAGE_VISIBILITY_QUERY,
    GET_BRAND_MENTIONS_QUERY,
    GET_COMPETITOR_SCORES_QUERY,
    GET_HISTORY_QUERY,
    GET_LATEST_SCAN_QUERY,
    GET_PREVIOUS_SCAN_QUERY,
    GET_PROVIDER_RESULTS_QUERY,
    GET_SCAN_COUNT_QUERY,
    GET_VISIBILITY_TREND_QUERY,
    GET_VOLATILITY_QUERY,
)

if TYPE_CHECKING:
    from duckdb import DuckDBPyConnection


class Database:
    """DuckDB database wrapper for PromptBeacon storage."""

    def __init__(self, db_path: str | Path | None = None):
        """Initialize the database connection.

        Args:
            db_path: Path to the DuckDB file. If None, uses in-memory database.
        """
        self.db_path = Path(db_path) if db_path else None
        self._conn: DuckDBPyConnection | None = None

    def _get_connection(self) -> DuckDBPyConnection:
        """Get or create a database connection."""
        if self._conn is None:
            try:
                if self.db_path:
                    self.db_path.parent.mkdir(parents=True, exist_ok=True)
                    self._conn = duckdb.connect(str(self.db_path))
                else:
                    self._conn = duckdb.connect(":memory:")
                self._initialize_schema()
            except Exception as e:
                raise StorageError(f"Failed to connect to database: {e}") from e
        return self._conn

    def _initialize_schema(self) -> None:
        """Initialize the database schema."""
        conn = self._conn
        if conn is None:
            return
        try:
            conn.execute(SCHEMA_SQL)
        except Exception as e:
            raise StorageError(f"Failed to initialize schema: {e}") from e

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> Database:
        self._get_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def save_report(self, report: Report) -> str:
        """Save a report to the database.

        Args:
            report: The Report to save.

        Returns:
            The scan ID.
        """
        conn = self._get_connection()
        scan_id = str(uuid.uuid4())

        try:
            # Insert scan record
            conn.execute(
                """
                INSERT INTO scans (
                    id, brand, timestamp, visibility_score, mention_count,
                    sentiment_positive, sentiment_neutral, sentiment_negative,
                    scan_duration_seconds, total_cost_usd, providers_used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    scan_id,
                    report.brand,
                    report.timestamp,
                    report.visibility_score,
                    report.mention_count,
                    report.sentiment_breakdown.positive,
                    report.sentiment_breakdown.neutral,
                    report.sentiment_breakdown.negative,
                    report.scan_duration_seconds,
                    report.total_cost_usd,
                    report.providers_used,
                ],
            )

            # Insert provider results and mentions
            for result in report.provider_results:
                result_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO provider_results (
                        id, scan_id, provider, model, prompt, response,
                        latency_ms, cost_usd, error, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        result_id,
                        scan_id,
                        result.provider,
                        result.model,
                        result.prompt,
                        result.response,
                        result.latency_ms,
                        result.cost_usd,
                        result.error,
                        result.timestamp,
                    ],
                )

                # Insert brand mentions
                for mention in result.mentions:
                    mention_id = str(uuid.uuid4())
                    conn.execute(
                        """
                        INSERT INTO brand_mentions (
                            id, result_id, scan_id, brand_name, sentiment,
                            position, context, confidence, is_recommendation
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            mention_id,
                            result_id,
                            scan_id,
                            mention.brand_name,
                            mention.sentiment,
                            mention.position,
                            mention.context,
                            mention.confidence,
                            mention.is_recommendation,
                        ],
                    )

            # Insert competitor scores
            for brand_name, comp_score in report.competitor_comparison.items():
                score_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO competitor_scores (
                        id, scan_id, brand_name, visibility_score, mention_count,
                        sentiment_positive, sentiment_neutral, sentiment_negative
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        score_id,
                        scan_id,
                        brand_name,
                        comp_score.visibility_score,
                        comp_score.mention_count,
                        comp_score.sentiment.positive,
                        comp_score.sentiment.neutral,
                        comp_score.sentiment.negative,
                    ],
                )

            return scan_id

        except Exception as e:
            raise StorageError(f"Failed to save report: {e}") from e

    def get_history(
        self, brand: str, days: int = 30
    ) -> HistoryReport:
        """Get historical data for a brand.

        Args:
            brand: The brand name.
            days: Number of days of history to retrieve.

        Returns:
            HistoryReport with historical data points.
        """
        conn = self._get_connection()
        start_date = datetime.utcnow() - timedelta(days=days)

        try:
            result = conn.execute(GET_HISTORY_QUERY, [brand, start_date]).fetchall()

            data_points = [
                HistoricalDataPoint(
                    timestamp=row[0],
                    visibility_score=row[1],
                    mention_count=row[2],
                    sentiment=SentimentBreakdown(
                        positive=row[3] or 0.0,
                        neutral=row[4] or 0.0,
                        negative=row[5] or 0.0,
                    ),
                )
                for row in result
            ]

            # Calculate trend direction
            trend_direction = None
            if len(data_points) >= 2:
                trend_result = conn.execute(
                    GET_VISIBILITY_TREND_QUERY, [brand]
                ).fetchone()
                if trend_result and trend_result[0] and trend_result[1]:
                    recent_avg, older_avg = trend_result
                    diff = recent_avg - older_avg
                    if diff > 2:
                        trend_direction = "up"
                    elif diff < -2:
                        trend_direction = "down"
                    else:
                        trend_direction = "stable"

            # Calculate average score
            avg_result = conn.execute(
                GET_AVERAGE_VISIBILITY_QUERY, [brand, start_date]
            ).fetchone()
            average_score = avg_result[0] if avg_result and avg_result[0] else None

            # Calculate volatility
            volatility = None
            vol_result = conn.execute(GET_VOLATILITY_QUERY, [brand, start_date]).fetchone()
            if vol_result and vol_result[1]:
                volatility = vol_result[1]

            return HistoryReport(
                brand=brand,
                data_points=data_points,
                trend_direction=trend_direction,
                average_score=average_score,
                volatility=volatility,
            )

        except Exception as e:
            raise StorageError(f"Failed to get history: {e}") from e

    def get_latest_scan(self, brand: str) -> ScanRecord | None:
        """Get the most recent scan for a brand.

        Args:
            brand: The brand name.

        Returns:
            ScanRecord or None if no scans exist.
        """
        conn = self._get_connection()

        try:
            result = conn.execute(GET_LATEST_SCAN_QUERY, [brand]).fetchone()
            if not result:
                return None

            return ScanRecord(
                id=result[0],
                brand=result[1],
                timestamp=result[2],
                visibility_score=result[3],
                mention_count=result[4],
                sentiment_positive=result[5] or 0.0,
                sentiment_neutral=result[6] or 0.0,
                sentiment_negative=result[7] or 0.0,
                scan_duration_seconds=result[8] or 0.0,
                total_cost_usd=result[9],
                providers_used=result[10] or [],
            )

        except Exception as e:
            raise StorageError(f"Failed to get latest scan: {e}") from e

    def get_previous_scan(self, brand: str) -> ScanRecord | None:
        """Get the second most recent scan for a brand.

        Args:
            brand: The brand name.

        Returns:
            ScanRecord or None if no previous scan exists.
        """
        conn = self._get_connection()

        try:
            result = conn.execute(GET_PREVIOUS_SCAN_QUERY, [brand]).fetchone()
            if not result:
                return None

            return ScanRecord(
                id=result[0],
                brand=result[1],
                timestamp=result[2],
                visibility_score=result[3],
                mention_count=result[4],
                sentiment_positive=result[5] or 0.0,
                sentiment_neutral=result[6] or 0.0,
                sentiment_negative=result[7] or 0.0,
                scan_duration_seconds=result[8] or 0.0,
                total_cost_usd=result[9],
                providers_used=result[10] or [],
            )

        except Exception as e:
            raise StorageError(f"Failed to get previous scan: {e}") from e

    def compare_with_previous(self, brand: str) -> ScanComparison | None:
        """Compare the latest scan with the previous one.

        Args:
            brand: The brand name.

        Returns:
            ScanComparison or None if not enough scans exist.
        """
        latest = self.get_latest_scan(brand)
        previous = self.get_previous_scan(brand)

        if not latest or not previous:
            return None

        return ScanComparison(
            brand=brand,
            current_score=latest.visibility_score,
            previous_score=previous.visibility_score,
            score_change=latest.visibility_score - previous.visibility_score,
            current_timestamp=latest.timestamp,
            previous_timestamp=previous.timestamp,
            changes=[],  # Will be populated by explainer module
        )

    def get_scan_count(self, brand: str) -> int:
        """Get the total number of scans for a brand.

        Args:
            brand: The brand name.

        Returns:
            Number of scans.
        """
        conn = self._get_connection()

        try:
            result = conn.execute(GET_SCAN_COUNT_QUERY, [brand]).fetchone()
            return result[0] if result else 0

        except Exception as e:
            raise StorageError(f"Failed to get scan count: {e}") from e

    def delete_old_scans(self, brand: str, older_than_days: int) -> int:
        """Delete scans older than a specified number of days.

        Args:
            brand: The brand name.
            older_than_days: Delete scans older than this many days.

        Returns:
            Number of scans deleted.
        """
        conn = self._get_connection()
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)

        try:
            # First delete related records
            scan_ids = conn.execute(
                "SELECT id FROM scans WHERE brand = ? AND timestamp < ?",
                [brand, cutoff_date],
            ).fetchall()

            if not scan_ids:
                return 0

            ids = [row[0] for row in scan_ids]

            for scan_id in ids:
                conn.execute(
                    "DELETE FROM brand_mentions WHERE scan_id = ?", [scan_id]
                )
                conn.execute(
                    "DELETE FROM provider_results WHERE scan_id = ?", [scan_id]
                )
                conn.execute(
                    "DELETE FROM competitor_scores WHERE scan_id = ?", [scan_id]
                )

            result = conn.execute(DELETE_OLD_SCANS_QUERY, [brand, cutoff_date]).fetchall()
            return len(result)

        except Exception as e:
            raise StorageError(f"Failed to delete old scans: {e}") from e
