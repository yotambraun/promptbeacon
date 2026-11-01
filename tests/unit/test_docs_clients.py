"""The client setup snippets in docs/mcp.md parse and all start the same server."""

from __future__ import annotations

import base64
import json
import re
import sys
import textwrap
import urllib.parse
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python 3.10
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[2]
MCP_DOC = ROOT / "docs" / "mcp.md"
COMMAND = "uvx"
ARGS = ["--from", "promptbeacon[mcp]>=1.4.0", "promptbeacon", "mcp"]
SHELL_COMMAND = 'uvx --from "promptbeacon[mcp]>=1.4.0" promptbeacon mcp'

FENCE = re.compile(
    r"^(?P<indent> *)```(?P<lang>\w+)\n(?P<body>.*?)^(?P=indent)```", re.M | re.S
)


def _blocks(lang: str) -> list[str]:
    text = MCP_DOC.read_text(encoding="utf-8")
    return [
        textwrap.dedent(m["body"]) for m in FENCE.finditer(text) if m["lang"] == lang
    ]


def _server(config: dict) -> dict:
    for key in ("mcpServers", "servers", "mcp_servers"):
        if key in config:
            return config[key]["promptbeacon"]
    raise AssertionError(f"no promptbeacon server in {config}")


def test_every_json_snippet_parses_and_runs_the_same_command():
    blocks = _blocks("json")
    assert len(blocks) >= 7
    for block in blocks:
        server = _server(json.loads(block))
        assert server["command"] == COMMAND
        assert server["args"] == ARGS


def test_the_toml_snippet_parses_and_runs_the_same_command():
    (block,) = _blocks("toml")
    server = _server(tomllib.loads(block))
    assert server["command"] == COMMAND
    assert server["args"] == ARGS
    assert server["startup_timeout_sec"] >= 30


def test_every_shell_setup_command_uses_the_same_server_command():
    lines = [
        line
        for block in _blocks("bash")
        for line in block.splitlines()
        if "promptbeacon" in line
    ]
    assert len(lines) >= 5
    for line in lines:
        if line.startswith("code --add-mcp"):
            payload = json.loads(line.split(" ", 2)[2].strip("'"))
            assert payload["name"] == "promptbeacon"
            assert (payload["command"], payload["args"]) == (COMMAND, ARGS)
        else:
            assert line.endswith(SHELL_COMMAND), line


def _links(scheme: str) -> list[str]:
    text = MCP_DOC.read_text(encoding="utf-8")
    return re.findall(rf"\(({re.escape(scheme)}[^)\s]+)\)", text)


def test_cursor_install_link_encodes_the_server():
    (link,) = _links("cursor://")
    parsed = urllib.parse.urlsplit(link)
    assert parsed.netloc == "anysphere.cursor-deeplink"
    assert parsed.path == "/mcp/install"
    query = urllib.parse.parse_qs(parsed.query)
    assert query["name"] == ["promptbeacon"]
    raw = link.split("config=", 1)[1]
    assert "+" not in raw and "/" not in raw  # safe in a query string as is
    assert json.loads(base64.b64decode(raw)) == {"command": COMMAND, "args": ARGS}


@pytest.mark.parametrize(
    "scheme", ["vscode:mcp/install?", "vscode-insiders:mcp/install?"]
)
def test_vscode_install_links_encode_the_server(scheme):
    (link,) = _links(scheme)
    payload = json.loads(urllib.parse.unquote(link[len(scheme) :]))
    assert payload == {
        "name": "promptbeacon",
        "type": "stdio",
        "command": COMMAND,
        "args": ARGS,
    }


def test_the_plugin_starts_the_same_server():
    config = json.loads(
        (ROOT / "plugins" / "promptbeacon" / ".mcp.json").read_text(encoding="utf-8")
    )
    server = _server(config)
    assert (server["command"], server["args"]) == (COMMAND, ARGS)
