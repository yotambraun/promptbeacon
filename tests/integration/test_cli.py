"""CLI smoke tests using typer's CliRunner.

These tests verify the CLI doesn't crash and produces expected output
structure, using mocked LLM responses to avoid real API calls.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from promptbeacon.cli.main import app
from promptbeacon.core.config import Provider
from promptbeacon.providers.base import LLMResponse

runner = CliRunner()


def _make_response(content: str) -> LLMResponse:
    return LLMResponse(
        content=content,
        model="mock-model",
        provider="openai",
        latency_ms=100.0,
        cost_usd=0.001,
    )


MOCK_RESPONSE = (
    "Nike is a leading brand in running shoes. I recommend Nike for their "
    "excellent quality and innovative designs."
)


@pytest.fixture
def _mock_providers_and_llm():
    """Mock provider availability and LLM responses."""
    with (
        patch(
            "promptbeacon.beacon.get_available_providers",
            return_value=[Provider.OPENAI],
        ),
        patch(
            "promptbeacon.beacon.LiteLLMClient.complete",
            new_callable=AsyncMock,
            return_value=_make_response(MOCK_RESPONSE),
        ),
    ):
        yield


@pytest.mark.integration
class TestCLI:
    """CLI smoke tests."""

    @pytest.mark.usefixtures("_mock_providers_and_llm")
    def test_scan_doesnt_crash(self):
        result = runner.invoke(app, ["scan", "Nike"])
        assert result.exit_code == 0

    @pytest.mark.usefixtures("_mock_providers_and_llm")
    def test_scan_output_contains_brand_and_score(self):
        result = runner.invoke(app, ["scan", "Nike"])
        assert result.exit_code == 0
        assert "Nike" in result.output
        # The score panel should be present
        assert "Visibility Score" in result.output or "100" in result.output

    @pytest.mark.usefixtures("_mock_providers_and_llm")
    def test_scan_json_format(self):
        result = runner.invoke(app, ["scan", "Nike", "--format", "json"])
        assert result.exit_code == 0
        assert "visibility_score" in result.output

    @pytest.mark.usefixtures("_mock_providers_and_llm")
    def test_scan_markdown_format(self):
        result = runner.invoke(app, ["scan", "Nike", "--format", "markdown"])
        assert result.exit_code == 0
        assert "Brand Visibility Report" in result.output

    def test_providers_command(self):
        result = runner.invoke(app, ["providers"])
        assert result.exit_code == 0
        assert "openai" in result.output.lower()

    def test_scan_demo_shows_measurement_tier_banner(self):
        result = runner.invoke(app, ["scan", "Nike", "--demo"])
        assert result.exit_code == 0
        assert "measurement: demo" in result.output

    def test_sources_command_demo(self):
        result = runner.invoke(
            app, ["sources", "Nike", "--demo", "--competitor", "Adidas", "-n", "12"]
        )
        assert result.exit_code == 0
        assert "measurement: demo" in result.output
        # Either a populated source table or the explicit empty-state message.
        assert "Source Domains" in result.output or "No citations" in result.output

    def test_scan_with_protocol_demo(self, tmp_path):
        proto = tmp_path / "protocol.json"
        proto.write_text(
            json.dumps({"brand": "Nike", "competitors": ["Adidas"], "prompt_count": 4}),
            encoding="utf-8",
        )
        result = runner.invoke(app, ["scan", "--protocol", str(proto), "--demo"])
        assert result.exit_code == 0
        assert "Nike" in result.output

    def test_scan_without_brand_or_protocol_errors(self):
        result = runner.invoke(app, ["scan"])
        assert result.exit_code == 1

    def test_funnel_command_demo(self):
        result = runner.invoke(
            app, ["funnel", "Nike", "--category", "running shoes", "--demo"]
        )
        assert result.exit_code == 0
        assert "Agentic Funnel" in result.output
        assert "funnel_model" in result.output

    def test_no_args_shows_help(self):
        result = runner.invoke(app, [])
        # Typer returns exit code 0 or 2 when showing help with no_args_is_help
        assert result.exit_code in (0, 2)
        assert "Usage" in result.output or "help" in result.output.lower()
