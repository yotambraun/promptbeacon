"""Scan error handling: provider failures vs. bugs, and warnings as errors."""

from __future__ import annotations

import subprocess
import sys
import warnings
from unittest.mock import patch

import pytest

from promptbeacon import Beacon, Provider
from promptbeacon.core.clock import utc_now
from promptbeacon.core.exceptions import ScanError
from promptbeacon.providers.mock_client import MockLLMClient


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


def test_internal_errors_are_not_reported_as_provider_failures():
    with (
        patch(
            "promptbeacon.beacon.extract_citations",
            side_effect=RuntimeError("bug in our code"),
        ),
        pytest.raises(RuntimeError, match="bug in our code"),
    ):
        Beacon("Nike").demo().with_category("running shoes").scan()


def test_all_provider_failures_name_the_exception_type():
    async def failing(*_args, **_kwargs):
        raise ConnectionError("connection refused")

    with (
        patch.object(MockLLMClient, "complete", new=failing),
        pytest.raises(ScanError) as excinfo,
    ):
        Beacon("Nike").demo().with_category("running shoes").scan()
    message = str(excinfo.value)
    assert "ConnectionError: connection refused" in message
    assert "provider queries failed" in message


def test_partial_provider_failure_keeps_the_report():
    original = MockLLMClient.complete

    async def flaky(self, prompt, **kwargs):
        if self.provider == Provider.ANTHROPIC:
            raise TimeoutError("slow")
        return await original(self, prompt, **kwargs)

    with patch.object(MockLLMClient, "complete", new=flaky):
        report = (
            Beacon("Nike")
            .demo()
            .with_category("running shoes")
            .with_providers(Provider.OPENAI, Provider.ANTHROPIC)
            .scan()
        )
    failed = [r for r in report.provider_results if not r.success]
    assert failed and all(r.provider == "anthropic" for r in failed)
    assert all(r.error == "TimeoutError: slow" for r in failed)
    assert any(r.success for r in report.provider_results)
