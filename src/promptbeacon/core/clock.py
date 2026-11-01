"""Timestamps in one place.

PromptBeacon stores and compares naive UTC datetimes (reports, history rows in
DuckDB, saved JSON). ``datetime.utcnow()`` is deprecated since Python 3.12, so
this helper builds the same value from an aware ``datetime.now(timezone.utc)``
and drops the tzinfo. Keeping the values naive means new reports compare and
sort cleanly against reports saved by earlier versions.
"""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """The current time in UTC, as a naive ``datetime`` (no tzinfo)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
