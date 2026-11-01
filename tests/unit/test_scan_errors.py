"""Scans must work with warnings promoted to errors."""

from __future__ import annotations

import subprocess
import sys
import warnings

from promptbeacon import Beacon
from promptbeacon.core.clock import utc_now


def test_utc_now_is_naive_utc():
    now = utc_now()
    assert now.tzinfo is None


def test_demo_scan_succeeds_with_warnings_as_errors():
    # Regression: datetime.utcnow() raised DeprecationWarning inside every
    # provider query, which was swallowed and reported as "All provider
    # queries failed. Check API keys and network."
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        report = Beacon("Nike").demo().with_category("running shoes").scan()
    assert report.provider_results
    assert all(r.success for r in report.provider_results)


def test_demo_scan_succeeds_under_python_W_error():
    code = (
        "from promptbeacon import Beacon;"
        "r = Beacon('Nike').demo().with_category('running shoes').scan();"
        "print(len(r.provider_results))"
    )
    proc = subprocess.run(
        [sys.executable, "-W", "error", "-c", code],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert int(proc.stdout.strip()) > 0
