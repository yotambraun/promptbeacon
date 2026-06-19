"""Tests for pinned scan protocols (reproducible runs)."""

from __future__ import annotations

import json

import pytest

from promptbeacon.core.config import Provider
from promptbeacon.protocol import ScanProtocol, build_beacon, load_protocol


def test_load_protocol(tmp_path):
    path = tmp_path / "proto.json"
    path.write_text(
        json.dumps(
            {
                "brand": "Nike",
                "competitors": ["Adidas"],
                "providers": ["openai"],
                "runs": 3,
                "grounded": True,
            }
        ),
        encoding="utf-8",
    )
    proto = load_protocol(path)
    assert proto.brand == "Nike"
    assert proto.competitors == ["Adidas"]
    assert proto.runs == 3
    assert proto.grounded is True


def test_build_beacon_applies_protocol():
    proto = ScanProtocol(
        brand="Nike",
        competitors=["Adidas", "Puma"],
        providers=["openai", "anthropic"],
        prompts=["What are the best running shoes?"],
        runs=4,
        grounded=True,
    )
    beacon = build_beacon(proto)
    assert beacon.brand == "Nike"
    assert beacon.config.competitors == ["Adidas", "Puma"]
    assert Provider.OPENAI in beacon.config.providers
    assert Provider.ANTHROPIC in beacon.config.providers
    assert beacon._stability_runs == 4
    assert beacon._grounded is True
    assert beacon._custom_prompts == ["What are the best running shoes?"]


def test_build_beacon_rejects_unknown_provider():
    with pytest.raises(ValueError):
        build_beacon(ScanProtocol(brand="Nike", providers=["notaprovider"]))
