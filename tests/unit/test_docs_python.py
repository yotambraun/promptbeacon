"""Every snippet on docs/python.md runs offline and prints what the page shows."""

from __future__ import annotations

import contextlib
import io
import re
from pathlib import Path

import pytest

DOC = Path(__file__).resolve().parents[2] / "docs" / "python.md"
FENCE = re.compile(r"^```(?P<lang>\w+)\n(?P<body>.*?)^```", re.M | re.S)


def _examples() -> list[tuple[str, str | None]]:
    """(python code, the text block right after it, if any)."""
    blocks = [(m["lang"], m["body"]) for m in FENCE.finditer(DOC.read_text("utf-8"))]
    examples = []
    for i, (lang, body) in enumerate(blocks):
        if lang != "python":
            continue
        after = blocks[i + 1] if i + 1 < len(blocks) else None
        examples.append((body, after[1] if after and after[0] == "text" else None))
    return examples


EXAMPLES = _examples()


def test_the_page_has_examples():
    assert len(EXAMPLES) >= 6


@pytest.mark.parametrize(("code", "expected"), EXAMPLES)
def test_example_runs_and_prints_what_the_page_shows(
    code, expected, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(code, str(DOC), "exec"), {"__name__": "__main__"})
    if expected is not None:
        assert out.getvalue() == expected
