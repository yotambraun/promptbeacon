"""Canned, realistic LLM responses for keyless demo mode.

These responses are generated deterministically from the prompt and a variation
seed, so:

* ``pip install promptbeacon`` users get an instant, believable scan with **no
  API keys**, and
* stability scans (which vary the seed per run) show realistic answer-to-answer
  flip-flopping instead of a fake-perfect 100.

The target brand and its competitors are woven in verbatim (so extraction finds
them), padded with obviously fictional filler brands so nothing here is mistaken
for a real recommendation.
"""

from __future__ import annotations

import hashlib

# Obviously fictional brands used as filler so the demo never appears to endorse
# (or disparage) a real company other than the ones the user supplied.
_FILLER_BRANDS = [
    "Globex",
    "Initech",
    "Umbra Labs",
    "Soylent Industries",
    "Hooli",
    "Vandelay",
    "Stark Goods",
    "Wayne & Co",
    "Acme United",
    "Cyberdyne",
]

_POSITIVE = [
    "{brand} is widely praised for its quality and reliability.",
    "Many reviewers recommend {brand} as a top, trusted choice.",
    "{brand} stands out for excellent value and strong customer satisfaction.",
]
_NEUTRAL = [
    "{brand} is a well-known option in this space.",
    "{brand} is frequently included in these comparisons.",
    "{brand} is one of several established names to consider.",
]
_NEGATIVE = [
    "Some users have reported concerns about {brand}'s pricing and support.",
    "{brand} has received mixed reviews lately and may not suit everyone.",
    "A few reviewers suggest looking beyond {brand} for better alternatives.",
]

# Realistic, varied sources so demo source-attribution mirrors the real GEO
# landscape (Reddit/Wikipedia/news/review dominate AI citations). These are
# illustrative URLs on real domains — no real page is fetched in demo mode.
_SOURCES = [
    ("Reddit", "https://www.reddit.com/r/BuyItForLife"),
    ("Wikipedia", "https://en.wikipedia.org/wiki/Comparison_of_brands"),
    ("Consumer Reports", "https://www.consumerreports.org/best"),
    ("The New York Times", "https://www.nytimes.com/wirecutter/reviews"),
    ("CNBC Select", "https://www.cnbc.com/select/best"),
]


def _seed(prompt: str, variation: int, salt: str) -> int:
    """Deterministic non-negative int from (prompt, variation, salt)."""
    raw = f"{prompt}|{variation}|{salt}".encode()
    return int(hashlib.sha256(raw).hexdigest()[:8], 16)


def _topic(prompt: str) -> str:
    """Best-effort topic phrase pulled from a templated prompt."""
    lowered = prompt.lower()
    for marker in (" best ", " top ", "recommend a good ", "leader in "):
        if marker in lowered:
            tail = lowered.split(marker, 1)[1]
            tail = tail.replace("brands", "").replace("brand", "")
            tail = tail.replace("company", "").replace("?", "").strip()
            if tail:
                return tail
    return "this category"


def build_demo_response(
    prompt: str,
    brand: str,
    competitors: list[str] | None = None,
    variation: int = 0,
) -> str:
    """Build a deterministic, realistic demo answer for a prompt.

    Args:
        prompt: The (category-substituted) prompt being "answered".
        brand: The target brand to (sometimes) weave in.
        competitors: Competitor brands to weave in.
        variation: Seed that changes the answer across stability runs.

    Returns:
        A plausible answer-engine response as plain text.
    """
    competitors = competitors or []
    topic = _topic(prompt)

    # ~72% of the time the brand appears at all (drives presence_rate + flips).
    brand_mentioned = _seed(prompt, variation, "mention") % 100 < 72

    # Assemble the ranked field: competitors + filler, plus the brand if present.
    filler_start = _seed(prompt, variation, "filler") % len(_FILLER_BRANDS)
    filler = [
        _FILLER_BRANDS[(filler_start + i) % len(_FILLER_BRANDS)] for i in range(2)
    ]
    field = list(competitors[:3]) + filler
    # Deterministic shuffle of the field.
    field.sort(key=lambda name: _seed(prompt, variation, "ord:" + name))

    if brand_mentioned:
        position = _seed(prompt, variation, "pos") % (len(field) + 1)
        field.insert(position, brand)

    numbered = "\n".join(f"{i + 1}. {name}" for i, name in enumerate(field))

    lines = [f"When it comes to {topic}, several options stand out:", "", numbered, ""]

    if brand_mentioned:
        bucket = _seed(prompt, variation, "sent") % 100
        if bucket < 58:
            sentence = _POSITIVE[_seed(prompt, variation, "p") % len(_POSITIVE)]
        elif bucket < 84:
            sentence = _NEUTRAL[_seed(prompt, variation, "n") % len(_NEUTRAL)]
        else:
            sentence = _NEGATIVE[_seed(prompt, variation, "g") % len(_NEGATIVE)]
        lines.append(sentence.format(brand=brand))

        if bucket < 58 and _seed(prompt, variation, "rec") % 100 < 45:
            lines.append(f"Overall, I'd recommend {brand} for most people.")
    else:
        leader = field[0] if field else "established brands"
        lines.append(f"Overall, {leader} is often considered a strong choice.")

    cite_roll = _seed(prompt, variation, "cite") % 100
    if cite_roll < 55:
        name, url = _SOURCES[_seed(prompt, variation, "src") % len(_SOURCES)]
        if brand_mentioned and cite_roll < 28:
            # Citation that names the brand -> source gets attributed to it.
            lines.append(
                f"According to {name}, {brand} ranks among the top "
                f"{topic} picks ({url})."
            )
        else:
            lines.append(
                f"According to {name}, these picks lead the {topic} market ({url})."
            )
        # ~35% of cited answers reference a second, distinct source.
        if _seed(prompt, variation, "cite2") % 100 < 35:
            name2, url2 = _SOURCES[_seed(prompt, variation, "src2") % len(_SOURCES)]
            if url2 != url:
                lines.append(f"{name2} reaches a similar conclusion ({url2}).")

    return "\n".join(lines)
