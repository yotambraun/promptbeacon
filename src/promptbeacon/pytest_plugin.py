"""Pytest plugin for PromptBeacon — GEO regression testing in CI.

Treat your brand's AI visibility like any other test. Mark a test and the plugin
runs a scan and asserts thresholds, failing the build when AI stops recommending
you:

    import pytest

    @pytest.mark.visibility(brand="Nike", competitors=["Adidas"], min_score=50)
    def test_nike_is_visible():
        ...

By default it runs against real providers when API keys are present, and skips
when they are not — unless ``PROMPTBEACON_DEMO=1`` (or ``demo=True`` on the
marker) forces keyless demo mode, which is perfect for example/CI smoke runs.

Registered automatically via the ``pytest11`` entry point — no conftest needed.
"""

from __future__ import annotations

import os
from typing import Any

import pytest

from promptbeacon.beacon import Beacon
from promptbeacon.core.config import Provider, has_api_key


def _env_demo() -> bool:
    """Whether PROMPTBEACON_DEMO requests keyless demo mode."""
    return os.environ.get("PROMPTBEACON_DEMO", "").lower() in {"1", "true", "yes", "on"}


def _any_keys() -> bool:
    """Whether any provider API key is configured."""
    return any(has_api_key(p) for p in Provider)


def _resolve_demo(explicit: bool | None) -> bool:
    """Decide whether to use demo mode for a marked test."""
    if explicit is not None:
        return explicit
    # No explicit choice: demo only if PROMPTBEACON_DEMO is set. Otherwise real
    # providers are used (and tests skip when no keys are configured).
    return _env_demo()


def _build_beacon(brand: str, kwargs: dict[str, Any], demo: bool) -> Beacon:
    beacon = Beacon(brand)
    competitors = kwargs.get("competitors")
    if competitors:
        beacon = beacon.with_competitors(*competitors)
    categories = kwargs.get("categories")
    if categories:
        beacon = beacon.with_categories(*categories)
    providers = kwargs.get("providers")
    if providers:
        enums = [p if isinstance(p, Provider) else Provider(str(p)) for p in providers]
        beacon = beacon.with_providers(*enums)
    prompt_count = kwargs.get("prompt_count")
    if prompt_count:
        beacon = beacon.with_prompt_count(prompt_count)
    if demo:
        beacon = beacon.demo()
    return beacon


def pytest_configure(config: pytest.Config) -> None:
    """Register the ``visibility`` marker."""
    config.addinivalue_line(
        "markers",
        "visibility(brand, min_score=, min_share_of_voice=, min_stability_score=, "
        "max_rank=, competitors=[], providers=[], categories=[], prompt_count=, "
        "stability=, demo=): run a PromptBeacon scan and assert AI visibility "
        "thresholds.",
    )


@pytest.fixture
def beacon():
    """Factory fixture that builds a Beacon, honouring PROMPTBEACON_DEMO.

    Example:
        def test_visible(beacon):
            report = beacon("Nike", competitors=["Adidas"]).scan()
            report.assert_visibility(min_score=40)
    """

    def _make(brand: str, *, demo: bool | None = None, **opts: Any) -> Beacon:
        return _build_beacon(brand, opts, _resolve_demo(demo))

    return _make


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_call(item: pytest.Item) -> None:
    """Run the scan + assertion for ``@pytest.mark.visibility(...)`` tests.

    Runs during the call phase so a threshold miss is reported as a normal test
    FAILURE (not a setup error), and missing keys cleanly SKIP.
    """
    marker = item.get_closest_marker("visibility")
    if marker is None:
        return

    kwargs = dict(marker.kwargs)
    brand = marker.args[0] if marker.args else kwargs.get("brand")
    if not brand:
        raise pytest.UsageError(
            "@pytest.mark.visibility requires a brand (positional or brand=...)"
        )

    demo = _resolve_demo(kwargs.get("demo"))
    if not demo and not _any_keys():
        pytest.skip(
            "No provider API keys configured. Set one (e.g. OPENAI_API_KEY) or "
            "PROMPTBEACON_DEMO=1 to run @pytest.mark.visibility tests."
        )

    beacon = _build_beacon(brand, kwargs, demo)
    stability = kwargs.get("stability")
    if stability:
        beacon = beacon.with_stability(int(stability))
        report = beacon.scan_stability()
    else:
        report = beacon.scan()

    report.assert_visibility(
        min_score=kwargs.get("min_score"),
        min_share_of_voice=kwargs.get("min_share_of_voice"),
        min_presence_rate=kwargs.get("min_presence_rate"),
        min_stability_score=kwargs.get("min_stability_score"),
        max_rank=kwargs.get("max_rank"),
    )
