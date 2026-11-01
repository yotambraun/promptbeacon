#!/usr/bin/env python3
"""Regenerate the README/docs images from real, keyless PromptBeacon runs.

Every image is produced by running PromptBeacon itself in demo mode, so what
the README shows is exactly what the commands print and write:

    assets/cli-demo.svg      terminal capture of the README's demo command
    assets/badge-example.svg `promptbeacon badge` output for the same scan
    assets/card-light.svg    `promptbeacon card` output (light, dark, PNG)
    assets/card-dark.svg
    assets/card-light.png    (needs 'promptbeacon[share]' for Pillow)

Run from the repository root:

    python scripts/render_assets.py
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.text import Text

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
DEMO_ARGS = ["httpx", "-t", "python http client", "-c", "requests", "-c", "aiohttp"]
WIDTH = 88


def _promptbeacon(*args: str) -> str:
    """Run the installed CLI with colours on and return stderr + stdout."""
    env = {**os.environ, "FORCE_COLOR": "1", "COLUMNS": str(WIDTH), "TERM": "xterm"}
    proc = subprocess.run(
        [sys.executable, "-m", "promptbeacon.cli.main", *args],
        capture_output=True,
        text=True,
        env=env,
        check=True,
        cwd=ROOT,
    )
    return proc.stderr + proc.stdout


def render_cli_demo() -> None:
    output = _promptbeacon("demo", *DEMO_ARGS)
    console = Console(record=True, width=WIDTH, file=io.StringIO())
    console.print(f"$ promptbeacon demo {' '.join(_quote(a) for a in DEMO_ARGS)}")
    console.print(Text.from_ansi(output.rstrip()))
    svg = console.export_svg(title="promptbeacon demo (keyless, demo data)")
    (ASSETS / "cli-demo.svg").write_text(svg, encoding="utf-8")


def render_share_assets() -> None:
    common = ["--demo", *DEMO_ARGS]
    _promptbeacon("badge", *common, "--output", str(ASSETS / "badge-example.svg"))
    _promptbeacon(
        "card",
        *common,
        "--output",
        str(ASSETS / "card-light.svg"),
        "--theme",
        "both",
        "--png",
        str(ASSETS / "card-light.png"),
    )
    # --theme both writes card-light-dark.*; keep the established file names.
    (ASSETS / "card-light-dark.svg").replace(ASSETS / "card-dark.svg")
    dark_png = ASSETS / "card-light-dark.png"
    if dark_png.exists():
        dark_png.unlink()


def _quote(arg: str) -> str:
    return f'"{arg}"' if " " in arg else arg


if __name__ == "__main__":
    render_cli_demo()
    render_share_assets()
    print(
        "Wrote", ", ".join(sorted(p.name for p in ASSETS.glob("*demo*"))), "and cards"
    )
