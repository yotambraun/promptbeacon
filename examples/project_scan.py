#!/usr/bin/env python3
"""Does AI recommend this open-source package? — keyless demo.

Reads public PyPI metadata (no key needed, one HTTP request), guesses the
category and competitors, and runs a demo scan. Drop .demo() and set an API key
for a real measurement.

    python examples/project_scan.py            # httpx
    python examples/project_scan.py pypi:rich  # any github:, pypi: or npm: ref
"""

from __future__ import annotations

import sys

from promptbeacon import Beacon
from promptbeacon.projects import ProjectMetadataError


def main(ref: str) -> None:
    try:
        beacon = Beacon.from_project(ref)
    except ProjectMetadataError as e:
        sys.exit(f"Could not read {ref}: {e}")

    profile = beacon.project
    guess = profile.category
    print(f"Project:     {profile.metadata.name} — {profile.metadata.description}")
    print(f"Category:    {guess.category!r} ({guess.basis}, {guess.confidence})")
    print(f"Competitors: {', '.join(profile.competitors) or '(none found)'}")

    report = beacon.demo().scan()
    sov = report.share_of_voice
    print(f"\nVisibility {report.visibility_score:.0f}/100 · share of voice "
          f"{sov.target_share:.0%} · {report.measurement_tier}")  # fmt: skip
    for entry in sov.aggregate.values():
        print(f"  {entry.brand_name:<20} in {entry.appearances}/{entry.total_prompts}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "pypi:httpx")
