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
import re
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.text import Text

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
DEMO_ARGS = ["httpx", "-t", "python http client", "-c", "requests", "-c", "aiohttp"]
WIDTH = 88


def _cli() -> list[str]:
    """The installed ``promptbeacon`` command, exactly what users run."""
    script = Path(sys.executable).with_name("promptbeacon")
    if script.exists():
        return [str(script)]
    # Same entry point as the console script, without runpy's re-import warning.
    return [sys.executable, "-c", "from promptbeacon.cli.main import app; app()"]


def _promptbeacon(*args: str) -> str:
    """Run the CLI with colours on and return what a terminal would show.

    stdout and stderr share one unbuffered pipe, so their lines arrive in the
    order a terminal prints them.
    """
    env = {
        **os.environ,
        "FORCE_COLOR": "1",
        "COLUMNS": str(WIDTH),
        "TERM": "xterm",
        "PYTHONUNBUFFERED": "1",
    }
    proc = subprocess.run(
        [*_cli(), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        check=True,
        cwd=ROOT,
    )
    # Decoded by hand: text mode would turn every carriage return into a
    # newline, which keeps each spinner frame as a line of its own.
    return _final_screen(proc.stdout.decode("utf-8"))


# Cursor controls Rich uses for live displays (spinners): erase line, cursor
# up, cursor show/hide. Colour codes (ending in "m") are kept.
_CONTROL = re.compile(r"\x1b\[(\d*)([AK])|\x1b\[\?25[lh]")


def _final_screen(stream: str) -> str:
    """Apply carriage returns and Rich's cursor controls like a terminal.

    A spinner redraws one line many times and erases it when done; replaying
    those controls keeps only what stays on screen.
    """
    lines: list[str] = [""]
    pos = 0
    while pos < len(stream):
        match = _CONTROL.search(stream, pos)
        end = match.start() if match else len(stream)
        for i, part in enumerate(stream[pos:end].split("\n")):
            if i:
                lines.append("")
            # A carriage return restarts the line; later text overwrites it.
            lines[-1] = part.rsplit("\r", 1)[-1] if "\r" in part else lines[-1] + part
        if not match:
            break
        if match.group(2) == "K":  # erase the current line
            lines[-1] = ""
        elif match.group(2) == "A":  # cursor up onto the line a spinner used
            for _ in range(int(match.group(1) or 1)):
                if len(lines) > 1 and not lines[-1]:
                    lines.pop()
        pos = match.end()
    return "\n".join(lines)


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
