"""Source attribution — which sites AI engines cite for your brand.

Web-grounded AI answers cite their sources. PromptBeacon aggregates those
citations by domain so you can see which sites feed your AI visibility — the
actionable GEO lever ("get cited on these sites").

Keyless: runs in demo mode, no API keys required.

    python examples/source_attribution.py
"""

from __future__ import annotations

from promptbeacon import Beacon


def main() -> None:
    report = (
        Beacon("Nike")
        .with_competitors("Adidas", "Puma")
        .with_categories("running shoes")
        .with_prompt_count(12)
        .demo()  # keyless; drop this and set an API key for a real scan
        .scan()
    )

    # Honest label of how this scan was measured.
    print(f"Measurement tier: {report.measurement_tier}")

    sa = report.source_attribution
    if not sa or not sa.entries:
        print("No citations found in this scan.")
        return

    print(f"\nTop source domains ({sa.total_citations} citations):")
    print(f"{'Domain':<28} {'Type':<12} {'Cit':>4} {'Share':>6}  Cites Nike?")
    print("-" * 66)
    for entry in sa.entries[:10]:
        cites = "yes" if entry.cites_target else "no"
        print(
            f"{entry.domain:<28} {entry.source_type:<12} "
            f"{entry.citations:>4} {entry.share:>5.0%}  {cites}"
        )

    print(f"\nCitation mix by source type: {sa.by_type}")
    if sa.target_cited_domains:
        print(f"Domains that cite Nike: {', '.join(sa.target_cited_domains)}")
    else:
        print("No cited source was associated with Nike in this scan.")


if __name__ == "__main__":
    main()
