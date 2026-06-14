"""Tests for the PromptBeacon pytest plugin."""

from __future__ import annotations

import pytest

from promptbeacon.beacon import Beacon
from promptbeacon.pytest_plugin import _build_beacon, _resolve_demo


def test_resolve_demo_explicit_wins(monkeypatch):
    monkeypatch.delenv("PROMPTBEACON_DEMO", raising=False)
    assert _resolve_demo(True) is True
    assert _resolve_demo(False) is False


def test_resolve_demo_env_flag(monkeypatch):
    monkeypatch.setenv("PROMPTBEACON_DEMO", "1")
    assert _resolve_demo(None) is True
    monkeypatch.setenv("PROMPTBEACON_DEMO", "no")
    assert _resolve_demo(None) is False


def test_build_beacon_demo_mode():
    beacon = _build_beacon("Nike", {"competitors": ["Adidas"]}, demo=True)
    assert isinstance(beacon, Beacon)
    assert beacon._demo_mode is True
    assert beacon.config.competitors == ["Adidas"]


def test_marker_registered(request):
    markers = request.config.getini("markers")
    assert any(m.startswith("visibility") for m in markers)


# This marker runs the plugin's call-phase hook end-to-end in demo mode.
@pytest.mark.visibility(brand="Nike", competitors=["Adidas"], min_score=0, demo=True)
def test_visibility_marker_passes_in_demo_mode():
    pass
