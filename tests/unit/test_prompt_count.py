"""``with_prompt_count(n)`` / ``--prompts n`` must honour n (no silent cap at 10)."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from promptbeacon import Beacon
from promptbeacon.cli.main import app
from promptbeacon.core.exceptions import ConfigurationError
from promptbeacon.protocol import ScanProtocol, build_beacon


def test_prompt_count_above_template_count_is_honoured():
    prompts = Beacon("Nike").with_categories("running shoes").with_prompt_count(25)
    generated = prompts._get_prompts()
    assert len(generated) == 25
    assert len(set(generated)) == 25  # distinct, not repeats
    assert all("running shoes" in p for p in generated)


def test_prompt_count_is_deterministic():
    a = Beacon("Nike").with_categories("running shoes").with_prompt_count(40)
    b = Beacon("Nike").with_categories("running shoes").with_prompt_count(40)
    assert a._get_prompts() == b._get_prompts()


def test_small_prompt_count_still_takes_the_first_templates():
    generated = (
        Beacon("Nike").with_categories("shoes").with_prompt_count(3)._get_prompts()
    )
    assert generated == [
        "What are the best shoes?",
        "Which shoes would you recommend?",
        "What are the top options for shoes?",
    ]


def test_custom_prompts_are_all_used_without_explicit_count():
    custom = [f"Question {i} about {{category}}?" for i in range(15)]
    generated = (
        Beacon("Nike").with_categories("shoes").with_prompts(custom)._get_prompts()
    )
    assert len(generated) == 15


def test_pinned_protocol_prompts_are_not_truncated():
    pinned = [f"Pinned prompt number {i}?" for i in range(12)]
    beacon = build_beacon(ScanProtocol(brand="Nike", prompts=pinned))
    assert beacon._get_prompts() == pinned


def test_impossible_prompt_count_raises_clear_error():
    beacon = (
        Beacon("Nike")
        .with_categories("shoes")
        .with_prompts(["Best {category}?"])
        .with_prompt_count(500)
    )
    with pytest.raises(ConfigurationError, match="distinct prompts"):
        beacon._get_prompts()


def test_cli_prompts_option_above_ten(tmp_path, monkeypatch):
    monkeypatch.setenv("PROMPTBEACON_HOME", str(tmp_path))
    result = CliRunner().invoke(
        app,
        ["scan", "Nike", "--demo", "-t", "running shoes", "-n", "25", "-f", "json"],
    )
    assert result.exit_code == 0, result.output
    assert len(json.loads(result.stdout)["provider_results"]) == 25
