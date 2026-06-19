"""Query fan-out: expand one prompt into the sub-queries an agentic engine runs.

Agentic search decomposes a single prompt into ~8-12 parallel sub-queries
capturing different intents, retrieves for each, then synthesises. This module
produces a deterministic, dependency-free fan-out so the funnel runs keyless;
an LLM-based planner can be layered on later for higher fidelity.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable

# Fan-out variants applied to the prompt's core topic, mirroring the intents
# real engines expand into (best / top / reviews / comparison / alternatives).
_FANOUT_TEMPLATES: list[str] = [
    "best {topic}",
    "top {topic} brands",
    "{topic} reviews",
    "{topic} comparison",
    "most recommended {topic}",
    "best {topic} 2026",
    "{topic} for beginners",
    "{topic} alternatives",
    "which {topic} is best",
    "{topic} buying guide",
    "{topic} pros and cons",
    "affordable {topic}",
]

_STOPWORDS = re.compile(
    r"\b(what|which|who|are|is|the|best|top|a|an|of|for|me|i|you|can|recommend|"
    r"good|should|choose|most|popular|company|brand|brands|options?)\b",
    re.IGNORECASE,
)


def _topic(prompt: str) -> str:
    """Best-effort core topic phrase extracted from a templated prompt."""
    text = prompt.strip().rstrip("?.!").lower()
    text = _STOPWORDS.sub(" ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    topic = " ".join(text.split())
    return topic or "this category"


def generate_sub_queries(prompt: str, n: int = 8) -> list[str]:
    """Expand a prompt into ``n`` distinct sub-queries (deterministic fan-out).

    Args:
        prompt: The buyer-intent prompt to fan out.
        n: Number of sub-queries to produce (1-12).

    Returns:
        Up to ``n`` distinct sub-queries.

    Raises:
        ValueError: If ``n`` is less than 1.
    """
    if n < 1:
        raise ValueError("n must be >= 1")

    topic = _topic(prompt)
    sub_queries: list[str] = []
    seen: set[str] = set()
    for template in _FANOUT_TEMPLATES:
        query = template.format(topic=topic)
        if query not in seen:
            seen.add(query)
            sub_queries.append(query)
            if len(sub_queries) >= n:
                break
    return sub_queries


async def llm_generate_sub_queries(
    prompt: str,
    n: int,
    complete: Callable[[str], Awaitable[str]],
) -> list[str]:
    """LLM-powered fan-out: ask a model for the sub-queries an engine would run.

    Higher fidelity than the deterministic templates. ``complete`` is any async
    ``prompt -> text`` callable (e.g. a provider client). Falls back to
    :func:`generate_sub_queries` on any error or empty/garbled output.
    """
    instruction = (
        f'A user asked an AI assistant: "{prompt}".\n'
        f"List the {n} distinct web search sub-queries an agentic AI search "
        "engine would run to answer it well. Output ONE sub-query per line, "
        "no numbering, no commentary."
    )
    try:
        text = await complete(instruction)
        queries: list[str] = []
        for line in text.splitlines():
            cleaned = line.strip().lstrip("-*0123456789.) ").strip()
            if cleaned and cleaned not in queries:
                queries.append(cleaned)
        if queries:
            return queries[:n]
    except Exception:  # noqa: BLE001 — any failure falls back to deterministic
        pass
    return generate_sub_queries(prompt, n)
