r"""Whole-name brand matching, shared by every part of PromptBeacon that looks
for a brand in text.

A brand matches only as a whole name: "uv" is not found in "uvicorn", "React"
not in "Preact", "Ray" not in "array". Matching is case-insensitive and
Unicode-aware.

The rule: where a name starts (or ends) with a letter, digit or underscore, the
character before (or after) the match must not be one, nor a hyphen, because a
hyphenated compound is a different name ("pytest" is not found in
"pytest-asyncio"). Where a name starts or ends with punctuation, that side needs
no boundary, so "C++", ".NET", "Node.js" and "scikit-learn" match as written.
``\b`` is not used because it fails for names that begin or end with
punctuation (``\b.NET`` never matches ".NET" after a space). Spaces inside a
name match any run of whitespace, so "New Balance" is found across a line
break.

Known limits: a hyphenated use of the name is not counted ("uv-managed"), and a
name that ends in a letter still matches before other punctuation, so "C" is
found in "C++".
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from functools import lru_cache

__all__ = [
    "brand_pattern",
    "brand_regex",
    "find_brand",
    "first_brand_offset",
    "iter_brand_matches",
    "mentions_brand",
    "mentions_any",
]


def brand_regex(name: str) -> str:
    """The regular-expression source that matches ``name`` as a whole name.

    Use it to embed a brand in a larger pattern; compile with ``re.IGNORECASE``.
    An empty or blank name yields a pattern that never matches.
    """
    name = name.strip()
    if not name:
        return r"(?!)"
    core = r"\s+".join(re.escape(part) for part in name.split())
    before = r"(?<![\w-])" if _is_word_char(name[0]) else ""
    after = r"(?![\w-])" if _is_word_char(name[-1]) else ""
    return before + core + after


@lru_cache(maxsize=1024)
def brand_pattern(name: str) -> re.Pattern[str]:
    """A compiled, case-insensitive whole-name pattern for ``name``."""
    return re.compile(brand_regex(name), re.IGNORECASE)


def iter_brand_matches(text: str, name: str) -> Iterator[re.Match[str]]:
    """Every whole-name occurrence of ``name`` in ``text``, in order."""
    return brand_pattern(name).finditer(text or "")


def find_brand(text: str, name: str) -> re.Match[str] | None:
    """The first whole-name occurrence of ``name`` in ``text``, or ``None``."""
    return brand_pattern(name).search(text or "")


def first_brand_offset(text: str, name: str) -> int | None:
    """Character offset of the first occurrence of ``name``, or ``None``."""
    match = find_brand(text, name)
    return match.start() if match else None


def mentions_brand(text: str, name: str) -> bool:
    """Whether ``text`` names ``name`` as a whole name."""
    return find_brand(text, name) is not None


def mentions_any(text: str, names: Iterable[str]) -> bool:
    """Whether ``text`` names any of ``names`` as a whole name."""
    return any(mentions_brand(text, name) for name in names if name)


def _is_word_char(char: str) -> bool:
    return char.isalnum() or char == "_"
