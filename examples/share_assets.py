#!/usr/bin/env python3
"""Badge and share card from one scan — keyless.

Writes, into ./promptbeacon-share/:
  badge.svg       README badge
  badge.json      shields.io endpoint JSON
  card.svg        1200x630 share card (light)
  card-dark.svg   the same card for dark mode
  card.png        PNG for social networks (only if Pillow is installed:
                  pip install 'promptbeacon[share]')

Demo output is labelled as demo on the badge and the card.

    python examples/share_assets.py
"""

from __future__ import annotations

import json
from pathlib import Path

from promptbeacon import Beacon
from promptbeacon.share import (
    badge_endpoint,
    render_badge_svg,
    render_card_png,
    render_card_svg,
)


def main() -> None:
    report = (
        Beacon("Nike")
        .demo()  # drop this and set an API key for a real measurement
        .with_category("running shoes")
        .with_competitors("Adidas", "New Balance", "Hoka")
        .scan()
    )

    out = Path("promptbeacon-share")
    out.mkdir(exist_ok=True)
    (out / "badge.svg").write_text(render_badge_svg(report), encoding="utf-8")
    (out / "badge.json").write_text(
        json.dumps(badge_endpoint(report), indent=2), encoding="utf-8"
    )
    (out / "card.svg").write_text(render_card_svg(report, "light"), encoding="utf-8")
    (out / "card-dark.svg").write_text(
        render_card_svg(report, "dark"), encoding="utf-8"
    )
    try:
        (out / "card.png").write_bytes(render_card_png(report))
    except ImportError:
        print("Skipping card.png (pip install 'promptbeacon[share]' for PNG export)")

    print(f"Wrote {', '.join(sorted(p.name for p in out.iterdir()))} to {out}/")
    print("README snippet:")
    print("[![AI visibility](promptbeacon-share/badge.svg)]"
          "(https://github.com/yotambraun/promptbeacon)")  # fmt: skip


if __name__ == "__main__":
    main()
