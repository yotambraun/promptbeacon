"""SQL queries for trend analysis and historical data."""

from __future__ import annotations

# Query to get historical visibility scores for a brand
GET_HISTORY_QUERY = """
SELECT
    timestamp,
    visibility_score,
    mention_count,
    sentiment_positive,
    sentiment_neutral,
    sentiment_negative
FROM scans
WHERE brand = ?
    AND timestamp >= ?
ORDER BY timestamp ASC
"""

# Query to get the most recent scan for a brand
GET_LATEST_SCAN_QUERY = """
SELECT
    id,
    brand,
    timestamp,
    visibility_score,
    mention_count,
    sentiment_positive,
    sentiment_neutral,
    sentiment_negative,
    scan_duration_seconds,
    total_cost_usd,
    providers_used
FROM scans
WHERE brand = ?
ORDER BY timestamp DESC
LIMIT 1
"""

# Query to get the previous scan (second most recent)
GET_PREVIOUS_SCAN_QUERY = """
SELECT
    id,
    brand,
    timestamp,
    visibility_score,
    mention_count,
    sentiment_positive,
    sentiment_neutral,
    sentiment_negative,
    scan_duration_seconds,
    total_cost_usd,
    providers_used
FROM scans
WHERE brand = ?
ORDER BY timestamp DESC
LIMIT 1 OFFSET 1
"""

# Query to get average visibility score over a period
GET_AVERAGE_VISIBILITY_QUERY = """
SELECT
    AVG(visibility_score) as avg_score,
    MIN(visibility_score) as min_score,
    MAX(visibility_score) as max_score,
    STDDEV(visibility_score) as std_score,
    COUNT(*) as scan_count
FROM scans
WHERE brand = ?
    AND timestamp >= ?
"""

# Query to get visibility trend (direction)
GET_VISIBILITY_TREND_QUERY = """
WITH recent_scans AS (
    SELECT
        visibility_score,
        timestamp,
        ROW_NUMBER() OVER (ORDER BY timestamp DESC) as rn
    FROM scans
    WHERE brand = ?
    ORDER BY timestamp DESC
    LIMIT 5
)
SELECT
    AVG(CASE WHEN rn <= 2 THEN visibility_score END) as recent_avg,
    AVG(CASE WHEN rn > 2 THEN visibility_score END) as older_avg
FROM recent_scans
"""

# Query to get provider results for a scan
GET_PROVIDER_RESULTS_QUERY = """
SELECT
    id,
    scan_id,
    provider,
    model,
    prompt,
    response,
    latency_ms,
    cost_usd,
    error,
    timestamp
FROM provider_results
WHERE scan_id = ?
ORDER BY timestamp ASC
"""

# Query to get brand mentions for a scan
GET_BRAND_MENTIONS_QUERY = """
SELECT
    id,
    result_id,
    scan_id,
    brand_name,
    sentiment,
    position,
    context,
    confidence,
    is_recommendation
FROM brand_mentions
WHERE scan_id = ?
ORDER BY position ASC
"""

# Query to get competitor scores for a scan
GET_COMPETITOR_SCORES_QUERY = """
SELECT
    id,
    scan_id,
    brand_name,
    visibility_score,
    mention_count,
    sentiment_positive,
    sentiment_neutral,
    sentiment_negative
FROM competitor_scores
WHERE scan_id = ?
"""

# Query to get all scans count for a brand
GET_SCAN_COUNT_QUERY = """
SELECT COUNT(*) as count
FROM scans
WHERE brand = ?
"""

# Query to delete old scans (for cleanup)
DELETE_OLD_SCANS_QUERY = """
DELETE FROM scans
WHERE brand = ?
    AND timestamp < ?
RETURNING id
"""

# Query to get sentiment trend over time
GET_SENTIMENT_TREND_QUERY = """
SELECT
    DATE_TRUNC('day', timestamp) as date,
    AVG(sentiment_positive) as avg_positive,
    AVG(sentiment_neutral) as avg_neutral,
    AVG(sentiment_negative) as avg_negative
FROM scans
WHERE brand = ?
    AND timestamp >= ?
GROUP BY DATE_TRUNC('day', timestamp)
ORDER BY date ASC
"""

# Query to get brand mention frequency by provider
GET_MENTIONS_BY_PROVIDER_QUERY = """
SELECT
    pr.provider,
    COUNT(bm.id) as mention_count,
    AVG(bm.confidence) as avg_confidence,
    SUM(CASE WHEN bm.sentiment = 'positive' THEN 1 ELSE 0 END) as positive_count,
    SUM(CASE WHEN bm.sentiment = 'neutral' THEN 1 ELSE 0 END) as neutral_count,
    SUM(CASE WHEN bm.sentiment = 'negative' THEN 1 ELSE 0 END) as negative_count
FROM provider_results pr
LEFT JOIN brand_mentions bm ON bm.result_id = pr.id
WHERE pr.scan_id IN (
    SELECT id FROM scans WHERE brand = ? AND timestamp >= ?
)
AND bm.brand_name = ?
GROUP BY pr.provider
"""

# Query to calculate volatility score
GET_VOLATILITY_QUERY = """
WITH score_changes AS (
    SELECT
        visibility_score,
        LAG(visibility_score) OVER (ORDER BY timestamp) as prev_score
    FROM scans
    WHERE brand = ?
        AND timestamp >= ?
    ORDER BY timestamp
)
SELECT
    AVG(ABS(visibility_score - prev_score)) as avg_change,
    STDDEV(visibility_score - prev_score) as volatility
FROM score_changes
WHERE prev_score IS NOT NULL
"""
