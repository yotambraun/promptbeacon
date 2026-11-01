"""Score trends for share cards: from local history or a small JSON file.

A card shows a sparkline of the visibility score when at least
:data:`MIN_POINTS` real scans exist that were measured the same way as the
card's report (same measurement tier and categories). Demo scans never count.

Two sources:

* the local history database (``~/.promptbeacon/data.db``), which real CLI
  scans write to by default, and
* a trend file (``--trend .promptbeacon/trend.json``), a small JSON list that a
  CI job commits next to its badge, because CI runners keep no local history.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from promptbeacon.core.schemas import Report

MIN_POINTS = 3
MAX_POINTS = 12
# Points kept in a trend file (two years of weekly scans).
FILE_LIMIT = 104
TREND_FILE_VERSION = 1


@dataclass
class TrendPoint:
    """One real scan in a trend."""

    timestamp: datetime
    score: float
    tier: str
    categories: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "score": round(self.score, 2),
            "tier": self.tier,
            "categories": list(self.categories),
            "models": list(self.models),
        }


def point_from_report(report: Report) -> TrendPoint | None:
    """The report as a trend point, or ``None`` for demo data."""
    if report.measurement_tier == "demo":
        return None
    models = sorted({f"{r.provider}/{r.model}" for r in report.provider_results})
    return TrendPoint(
        report.timestamp,
        float(report.visibility_score),
        report.measurement_tier,
        list(report.categories),
        models,
    )


def _same_measurement(point: TrendPoint, report: Report) -> bool:
    return (
        point.tier == report.measurement_tier
        and point.tier != "demo"
        and list(point.categories) == list(report.categories)
    )


def _same_time(a: datetime, b: datetime) -> bool:
    return abs((a - b).total_seconds()) < 1


def merge_report(points: list[TrendPoint], report: Report) -> list[TrendPoint]:
    """``points`` plus this report (if real and not already present), by time."""
    point = point_from_report(report)
    merged = list(points)
    if point is not None and not any(
        _same_time(p.timestamp, point.timestamp) for p in merged
    ):
        merged.append(point)
    merged.sort(key=lambda p: p.timestamp)
    return merged


def comparable(points: list[TrendPoint], report: Report) -> list[TrendPoint]:
    """Points measured like ``report`` (same tier and categories), with it."""
    if report.measurement_tier == "demo":
        return []
    return [p for p in merge_report(points, report) if _same_measurement(p, report)]


def trend_values(
    points: list[TrendPoint], report: Report, limit: int = MAX_POINTS
) -> list[float] | None:
    """The last ``limit`` comparable scores, or ``None`` with fewer than 3."""
    values = [p.score for p in comparable(points, report)][-limit:]
    return values if len(values) >= MIN_POINTS else None


def load_trend_file(path: Path) -> list[TrendPoint]:
    """Read a trend file (a missing file is an empty trend).

    Raises:
        ValueError: If the file exists but is not a PromptBeacon trend file.
    """
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [
            TrendPoint(
                datetime.fromisoformat(str(item["timestamp"])),
                float(item["score"]),
                str(item["tier"]),
                [str(c) for c in item.get("categories") or []],
                [str(m) for m in item.get("models") or []],
            )
            for item in data.get("points", [])
        ]
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        raise ValueError(
            f"{path} is not a PromptBeacon trend file ({e}). Delete it or pass "
            "another --trend path."
        ) from e


def save_trend_file(path: Path, brand: str, points: list[TrendPoint]) -> None:
    """Write a trend file, keeping the most recent :data:`FILE_LIMIT` points."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": TREND_FILE_VERSION,
        "brand": brand,
        "note": "Visibility scores of real PromptBeacon scans (demo scans are "
        "never added). Written by `promptbeacon card --trend`.",
        "points": [p.as_dict() for p in points[-FILE_LIMIT:]],
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def update_trend_file(path: Path, report: Report) -> list[TrendPoint]:
    """Add a real report to a trend file (demo reports leave it untouched)."""
    points = load_trend_file(path)
    if report.measurement_tier == "demo":
        return points
    merged = merge_report(points, report)
    if len(merged) != len(points):
        save_trend_file(path, report.brand, merged)
    return merged


def history_points(db_path: Path, report: Report) -> list[TrendPoint]:
    """Comparable real scans from a history database (read only if it exists)."""
    if report.measurement_tier == "demo" or not db_path.exists():
        return []
    from promptbeacon.storage.database import Database

    db = Database(db_path)
    try:
        rows = db.get_trend(
            report.brand, report.measurement_tier, report.categories, FILE_LIMIT
        )
    finally:
        db.close()
    return [
        TrendPoint(ts, score, report.measurement_tier, list(report.categories))
        for ts, score in rows
    ]


__all__ = [
    "MIN_POINTS",
    "TrendPoint",
    "comparable",
    "history_points",
    "load_trend_file",
    "merge_report",
    "point_from_report",
    "save_trend_file",
    "trend_values",
    "update_trend_file",
]
