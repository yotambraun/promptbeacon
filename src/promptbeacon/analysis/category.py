"""Category handling: the topic every visibility prompt is asked about.

A visibility scan only means something when the prompts are about the brand's
real category ("What are the best running shoes?"). This module holds the
helpers used to resolve that category:

* the competitor-anchored prompt set used when no category is given but
  competitors are (category-free, and never names the target brand), and
* the opt-in, single-call LLM category inference
  (``Beacon.with_category_inference()`` / ``--infer-category``).
"""

from __future__ import annotations

import math
import re

from promptbeacon.prompts.templates import expand_prompt_templates

# Buyer-intent prompts anchored on a competitor. They need no category, they
# never name the target brand (so the target is not handed a free mention),
# and "alternatives to X" is one of the most common real buyer questions.
COMPETITOR_ALTERNATIVE_TEMPLATES: list[str] = [
    "What are the best alternatives to {competitor}?",
    "What should I use instead of {competitor}?",
    "Which brands compete with {competitor}?",
    "Is there anything better than {competitor}?",
    "Who are the main competitors of {competitor}?",
    "What do people switch to from {competitor}?",
    "Which {competitor} alternative would you recommend?",
    "Compare {competitor} with its top competitors.",
    "What are cheaper alternatives to {competitor}?",
    "What is the most popular alternative to {competitor}?",
]

_MAX_CATEGORY_WORDS = 6
_PREFIX = re.compile(r"^(?:the\s+)?(?:product\s+)?category\s*(?:is)?\s*[:\-]\s*", re.I)


def competitor_alternative_prompts(competitors: list[str], n: int) -> list[str]:
    """Build ``n`` distinct competitor-anchored prompts, round-robin over rivals.

    Args:
        competitors: Competitor names (at least one).
        n: Number of prompts wanted.

    Returns:
        ``n`` distinct prompts, deterministic for the same inputs.

    Raises:
        ValueError: If no competitors are given or ``n`` cannot be reached.
    """
    names = [c for c in competitors if c.strip()]
    if not names:
        raise ValueError("competitor-anchored prompts need at least one competitor")
    templates = expand_prompt_templates(
        COMPETITOR_ALTERNATIVE_TEMPLATES, math.ceil(n / len(names))
    )
    prompts = [t.format(competitor=c) for t in templates for c in names]
    return prompts[:n]


def build_category_prompt(
    brand: str,
    competitors: list[str] | None = None,
    hints: list[str] | None = None,
    want_competitors: bool = False,
) -> str:
    """Prompt asking a model to name the brand's product/service category.

    With ``want_competitors`` the model is asked for a small JSON object that
    also lists the main competitors.
    """
    lines = [f'What product category does "{brand}" compete in?']
    if want_competitors:
        lines.append(
            'Reply with JSON only: {"category": "...", "competitors": ["...", '
            '"..."]}. The category is 2 to 5 lowercase words, the way a buyer '
            "would phrase it (for example: running shoes, crm software, python "
            "http client), without brand names. List up to 4 direct competitors "
            "by their usual names."
        )
    else:
        lines.append(
            "Answer with the category only: 2 to 5 lowercase words, the way a "
            "buyer would phrase it (for example: running shoes, crm software, "
            "python http client). Do not include any brand names. No punctuation, "
            "no explanation."
        )
    if competitors:
        lines.append("Known competitors: " + ", ".join(competitors) + ".")
    if hints:
        lines.append("Context: " + " ".join(hints)[:600])
    return "\n".join(lines)


def parse_profile(text: str, brand: str) -> tuple[str | None, list[str]]:
    """Parse a category answer that may be JSON with competitors, or plain text."""
    import json

    match = re.search(r"\{.*\}", text or "", re.S)
    if match:
        try:
            data = json.loads(match.group(0))
        except ValueError:
            data = None
        if isinstance(data, dict):
            category = parse_category(str(data.get("category") or ""), brand)
            raw = data.get("competitors") or []
            competitors = []
            if isinstance(raw, list):
                for name in raw[:6]:
                    name = str(name).strip()
                    if name and name.lower() != brand.lower() and len(name) <= 60:
                        competitors.append(name)
            return category, competitors[:4]
    return parse_category(text, brand), []


def parse_category(text: str, brand: str) -> str | None:
    """Clean a model's category answer; ``None`` if it is not a usable category."""
    if not text:
        return None
    line = text.strip().splitlines()[0] if text.strip() else ""
    line = _PREFIX.sub("", line.strip())
    line = line.strip().strip("\"'`*.").strip().lower()
    line = re.sub(r"\s+", " ", line)
    if not line or len(line.split()) > _MAX_CATEGORY_WORDS or len(line) > 60:
        return None
    if brand.lower() in line:
        return None
    if any(ch in line for ch in '{}[]<>|"`'):
        return None
    return line
