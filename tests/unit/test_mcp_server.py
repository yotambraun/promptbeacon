"""MCP tools are thin, JSON-returning wrappers over the public API."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from promptbeacon import mcp_server
from promptbeacon.projects import HttpResponse

KEYS = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "MISTRAL_API_KEY",
    "COHERE_API_KEY",
    "PERPLEXITY_API_KEY",
    "TAVILY_API_KEY",
]
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "projects"


@pytest.fixture
def no_keys(monkeypatch):
    for key in KEYS:
        monkeypatch.delenv(key, raising=False)


@pytest.mark.usefixtures("no_keys")
def test_providers_reports_status_never_values(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-value")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")  # e.g. an unset ${VAR:-} mapping
    result = mcp_server.providers()
    assert result["providers"]["openai"] is True
    assert result["providers"]["anthropic"] is False
    assert result["default_mode"] == "live"
    assert "sk-secret-value" not in json.dumps(result)


@pytest.mark.usefixtures("no_keys")
def test_scan_defaults_to_demo_without_keys_and_says_so():
    result = asyncio.run(
        mcp_server.scan("Nike", category="running shoes", competitors=["Adidas"])
    )
    assert result["measurement_tier"] == "demo"
    assert "demo" in result["note"]
    assert result["categories"] == ["running shoes"]
    json.dumps(result)  # JSON-serialisable


@pytest.mark.usefixtures("no_keys")
def test_scan_live_without_keys_is_a_clear_error():
    with pytest.raises(ValueError, match="API key"):
        asyncio.run(mcp_server.scan("Nike", category="shoes", demo=False))


@pytest.mark.usefixtures("no_keys")
def test_scan_without_category_warns():
    result = asyncio.run(mcp_server.scan("Nike"))
    assert "category" in result["warning"]


@pytest.mark.usefixtures("no_keys")
def test_project_scan_uses_project_metadata():
    pypi = (FIXTURES / "pypi_httpx.json").read_text(encoding="utf-8")

    def http(url, _headers):
        return HttpResponse(200, pypi) if "pypi.org" in url else HttpResponse(404, "")

    with patch("promptbeacon.projects.sources.default_http_get", new=http):
        result = asyncio.run(mcp_server.project_scan("pypi:httpx"))
    assert result["brand"] == "httpx"
    assert result["categories"] == ["python http client"]
    assert result["project"]["category_basis"] == "description"


@pytest.mark.usefixtures("no_keys")
def test_sources_returns_domains():
    result = asyncio.run(mcp_server.sources("Nike", category="running shoes"))
    assert set(result) >= {"top_sources", "measurement_tier"}


@pytest.mark.usefixtures("no_keys")
def test_share_assets_writes_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = asyncio.run(
        mcp_server.share_assets(
            "Nike", category="running shoes", competitors=["Adidas"],
            output_dir=str(tmp_path / "pb"),
        )
    )  # fmt: skip
    for path in result["files"].values():
        assert Path(path).exists()
    assert (
        json.loads(Path(result["files"]["badge_json"]).read_text())["schemaVersion"]
        == 1
    )
    assert "prefers-color-scheme: dark" in result["readme_card"]
    assert "demo" in result["note"].lower()


def test_server_registers_the_tools():
    pytest.importorskip("mcp")
    server = mcp_server.create_server()
    tools = asyncio.run(server.list_tools())
    names = {t.name for t in tools}
    assert names == {"providers", "scan", "project_scan", "sources", "share_assets"}


@pytest.mark.integration
def test_stdio_round_trip(tmp_path):
    """initialize + tools/list + one demo tool call over real stdio."""
    pytest.importorskip("mcp")
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    env = {k: v for k, v in os.environ.items() if k not in KEYS}
    env["PROMPTBEACON_HOME"] = str(tmp_path)
    params = StdioServerParameters(
        command=sys.executable,
        args=["-c", "from promptbeacon.cli.main import app; app()", "mcp"],
        env=env,
    )

    async def run():
        async with Client(params) as client:
            tools = await client.list_tools()
            result = await client.call_tool(
                "scan", {"brand": "Nike", "category": "running shoes", "demo": True}
            )
            return [t.name for t in tools.tools], result

    names, result = asyncio.run(run())
    assert "scan" in names and "project_scan" in names
    assert not result.is_error
    assert result.structured_content["measurement_tier"] == "demo"
