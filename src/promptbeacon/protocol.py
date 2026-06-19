"""Pinned scan protocols for reproducible GEO measurement.

The "don't measure once" principle requires a *stable* protocol re-run
identically over time — otherwise trends are noise. A protocol file pins the
brand, prompts, providers, run count, and mode so a scan is reproducible in CI
and comparable across dates.

Example ``protocol.json``::

    {
      "brand": "Nike",
      "competitors": ["Adidas", "Puma"],
      "providers": ["openai", "anthropic"],
      "prompts": ["What are the best running shoes?", "..."],
      "runs": 5,
      "grounded": true
    }
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from promptbeacon.beacon import Beacon
from promptbeacon.core.config import Provider


class ScanProtocol(BaseModel):
    """A pinned, reproducible scan configuration."""

    brand: str = Field(..., min_length=1)
    competitors: list[str] = Field(default_factory=list)
    providers: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    prompts: list[str] = Field(
        default_factory=list, description="Explicit, pinned prompt set"
    )
    prompt_count: int | None = None
    runs: int = Field(default=0, ge=0, description="Stability runs (0 = single scan)")
    grounded: bool = False
    smart: bool = False


def load_protocol(path: str | Path) -> ScanProtocol:
    """Load and validate a scan protocol from a JSON file."""
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    return ScanProtocol(**data)


def build_beacon(protocol: ScanProtocol) -> Beacon:
    """Build a configured :class:`Beacon` from a pinned protocol."""
    beacon = Beacon(protocol.brand)
    if protocol.competitors:
        beacon = beacon.with_competitors(*protocol.competitors)
    if protocol.providers:
        beacon = beacon.with_providers(
            *[Provider(p.lower()) for p in protocol.providers]
        )
    if protocol.categories:
        beacon = beacon.with_categories(*protocol.categories)
    if protocol.prompts:
        beacon = beacon.with_prompts(protocol.prompts)
    if protocol.prompt_count is not None:
        beacon = beacon.with_prompt_count(protocol.prompt_count)
    if protocol.grounded:
        beacon = beacon.with_grounding()
    if protocol.smart:
        beacon = beacon.with_smart_extraction().with_smart_recommendations()
    if protocol.runs > 0:
        beacon = beacon.with_stability(protocol.runs)
    return beacon
