"""LLM-based brand mention extraction (opt-in "smart mode").

Regex extraction is fast and offline but heuristic. Smart mode asks a cheap LLM
to read each response and report which tracked brands are mentioned, with
sentiment and recommendation — catching paraphrases and nuance regex misses.

The prompt-building and parsing are pure functions (no network), so they're
fully testable without API keys; ``Beacon`` orchestrates the actual LLM call and
falls back to regex on any error.
"""

from __future__ import annotations

import json

from promptbeacon.core.schemas import BrandMention
from promptbeacon.extraction.mentions import MentionExtractionResult

# LLM extraction is far more reliable than a regex match, so mentions it returns
# carry a high (but not certain) confidence.
_LLM_CONFIDENCE = 0.9

_VALID_SENTIMENTS = {"positive", "neutral", "negative"}


def build_extraction_prompt(
    response_text: str,
    target_brand: str,
    competitors: list[str] | None = None,
    aliases: list[str] | None = None,
) -> str:
    """Build a strict JSON-extraction prompt for an LLM."""
    tracked = [target_brand] + (aliases or []) + (competitors or [])
    tracked_list = ", ".join(f'"{b}"' for b in tracked)
    return (
        "You are a precise information-extraction tool. Read the TEXT below and "
        "report which of these tracked brands are actually mentioned (including "
        "clear paraphrases or possessive/plural forms):\n"
        f"Tracked brands: [{tracked_list}]\n\n"
        "For each tracked brand that appears, output its sentiment in the text "
        "(positive, neutral, or negative) and whether the text explicitly "
        "recommends or endorses it.\n\n"
        "Return ONLY a JSON object, no prose, in exactly this shape:\n"
        '{"mentions": [{"brand": "<one of the tracked brands, verbatim>", '
        '"sentiment": "positive|neutral|negative", "recommended": true|false}]}\n'
        "Only include brands genuinely mentioned. If none are, return "
        '{"mentions": []}.\n\n'
        f"TEXT:\n{response_text}"
    )


def _strip_code_fences(raw: str) -> str:
    """Remove ```json ... ``` fences if the model wrapped its output."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


def parse_llm_extraction(
    raw: str,
    response_text: str,
    target_brand: str,
    competitors: list[str] | None = None,
    aliases: list[str] | None = None,
) -> MentionExtractionResult:
    """Parse an LLM's JSON extraction into a MentionExtractionResult.

    Raises:
        ValueError: If the output cannot be parsed into the expected shape, so
            the caller can fall back to regex extraction.
    """
    try:
        data = json.loads(_strip_code_fences(raw))
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM extraction was not valid JSON: {e}") from e

    if not isinstance(data, dict) or "mentions" not in data:
        raise ValueError("LLM extraction missing 'mentions' key")

    # Canonicalise: aliases credit the target brand; only accept tracked brands.
    alias_lower = {a.lower(): target_brand for a in (aliases or [])}
    tracked_lower = {b.lower(): b for b in ([target_brand] + (competitors or []))}
    tracked_lower.update({a.lower(): target_brand for a in (aliases or [])})

    mentions: list[BrandMention] = []
    brands_found: set[str] = set()
    position = 0
    for item in data.get("mentions", []):
        if not isinstance(item, dict):
            continue
        raw_brand = str(item.get("brand", "")).strip()
        key = raw_brand.lower()
        if key not in tracked_lower:
            continue  # ignore brands we didn't ask about
        canonical = alias_lower.get(key, tracked_lower[key])

        sentiment = str(item.get("sentiment", "neutral")).lower()
        if sentiment not in _VALID_SENTIMENTS:
            sentiment = "neutral"

        mentions.append(
            BrandMention(
                brand_name=canonical,
                sentiment=sentiment,  # type: ignore[arg-type]
                position=position,
                context=_context_for(response_text, raw_brand),
                confidence=_LLM_CONFIDENCE,
                is_recommendation=bool(item.get("recommended", False)),
            )
        )
        brands_found.add(canonical)
        position += 1

    return MentionExtractionResult(
        mentions=mentions,
        total_mentions=len(mentions),
        brands_found=list(brands_found),
    )


def _context_for(response_text: str, brand: str, window: int = 100) -> str:
    """Find a context snippet around the brand's first occurrence, if present."""
    if not brand:
        return ""
    idx = response_text.lower().find(brand.lower())
    if idx == -1:
        return ""
    start = max(0, idx - window)
    end = min(len(response_text), idx + len(brand) + window)
    snippet = response_text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(response_text):
        snippet = snippet + "..."
    return snippet
