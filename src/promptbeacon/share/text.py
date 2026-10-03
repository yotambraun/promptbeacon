"""Text helpers for SVG rendering: width estimation, truncation, escaping.

SVGs embedded in READMEs are rendered as images (no scripts, no web fonts), so
layout must be decided without a browser. Widths are estimated from Helvetica/
Arial metrics, which are close to the system UI fonts used by the font stack;
wide East Asian characters count as a full em.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable
from xml.sax.saxutils import escape

FONT_STACK = (
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, "
    "'Noto Sans', 'Liberation Sans', sans-serif"
)

# Advance widths per 1000 units (Helvetica/Arial regular).
_WIDTHS: dict[str, int] = {
    " ": 278, "!": 278, '"': 355, "#": 556, "$": 556, "%": 889, "&": 667,
    "'": 191, "(": 333, ")": 333, "*": 389, "+": 584, ",": 278, "-": 333,
    ".": 278, "/": 278, ":": 278, ";": 278, "<": 584, "=": 584, ">": 584,
    "?": 556, "@": 1015, "[": 278, "\\": 278, "]": 278, "^": 469, "_": 556,
    "`": 333, "{": 334, "|": 260, "}": 334, "~": 584, "·": 278, "…": 1000,
    "A": 667, "B": 667, "C": 722, "D": 722, "E": 667, "F": 611, "G": 778,
    "H": 722, "I": 278, "J": 500, "K": 667, "L": 556, "M": 833, "N": 722,
    "O": 778, "P": 667, "Q": 778, "R": 722, "S": 667, "T": 611, "U": 722,
    "V": 667, "W": 944, "X": 667, "Y": 667, "Z": 611,
    "a": 556, "b": 556, "c": 500, "d": 556, "e": 556, "f": 278, "g": 556,
    "h": 556, "i": 222, "j": 222, "k": 500, "l": 222, "m": 833, "n": 556,
    "o": 556, "p": 556, "q": 556, "r": 333, "s": 500, "t": 278, "u": 556,
    "v": 500, "w": 722, "x": 500, "y": 500, "z": 500,
}  # fmt: skip
_DIGIT = 556
_DEFAULT = 600
# System UI fonts (Segoe UI, SF) run slightly wider than Arial; bold wider still.
_SAFETY = 1.06
_BOLD = 1.08


def text_width(
    text: str, size: float, bold: bool = False, *, safety: bool = True
) -> float:
    """Estimated rendered width of ``text`` in pixels at font ``size``.

    With ``safety`` (the default) the estimate errs wide so layouts never
    overflow; badges pass ``safety=False`` because their text is fitted
    exactly with ``textLength``.
    """
    units = 0
    for ch in text:
        if ch.isdigit() and ch.isascii():
            units += _DIGIT
        elif ch in _WIDTHS:
            units += _WIDTHS[ch]
        elif unicodedata.east_asian_width(ch) in ("W", "F"):
            units += 1000
        elif unicodedata.combining(ch):
            continue
        else:
            units += _DEFAULT
    width = units / 1000 * size * (_SAFETY if safety else 1.0)
    if bold:
        width *= _BOLD if safety else 1.04
    return width


Measure = Callable[..., float]  # (text, size, bold=False) -> width in px


def truncate(
    text: str,
    max_width: float,
    size: float,
    bold: bool = False,
    measure: Measure | None = None,
) -> str:
    """Shorten ``text`` with an ellipsis so it fits ``max_width`` pixels."""
    width = measure or text_width
    if width(text, size, bold) <= max_width:
        return text
    ellipsis = "…"
    out = text
    while out and width(out + ellipsis, size, bold) > max_width:
        out = out[:-1]
    return (out.rstrip() + ellipsis) if out else ellipsis


def xml(text: str) -> str:
    """Escape text for SVG element content and attribute values."""
    cleaned = "".join(
        ch for ch in text if ch in "\t\n" or unicodedata.category(ch) != "Cc"
    )
    return escape(cleaned, {'"': "&quot;"})
