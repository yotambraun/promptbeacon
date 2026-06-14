#!/usr/bin/env python3
"""Keyless demo quickstart — the fastest way to see PromptBeacon.

Demo mode runs against a realistic offline mock, so this works the moment you
``pip install promptbeacon`` — no API keys, no cost.

Usage:
    python examples/demo_quickstart.py
"""

from promptbeacon import Beacon


def main():
    report = (
        Beacon("Nike")
        .demo()  # <- keyless: realistic canned data, no API calls
        .with_competitors("Adidas", "Puma")
        .with_categories("running shoes")
        .with_prompt_count(8)
        .scan()
    )

    print(f"Visibility score: {report.visibility_score}/100")
    print(f"Mentions:         {report.mention_count}")

    sov = report.share_of_voice
    print(f"Share of Voice:   {sov.target_share:.0%} (rank {sov.target_rank})")
    print(f"Presence rate:    {sov.target_presence_rate:.0%} of prompts")

    print("\nShare of Voice by brand:")
    for entry in sorted(
        sov.aggregate.values(), key=lambda e: e.appearances, reverse=True
    ):
        print(
            f"  {entry.brand_name:<8} {entry.share_of_voice:>4.0%}  "
            f"({entry.appearances}/{entry.total_prompts} prompts)"
        )

    print("\nWhen you're ready for a real scan: set an API key and drop .demo().")


if __name__ == "__main__":
    main()
