#!/usr/bin/env python3
"""
Competitor Analysis Example

This example demonstrates how to compare your brand's visibility
against competitors using PromptBeacon.

Prerequisites:
    - Set OPENAI_API_KEY environment variable or use a .env file
    - pip install promptbeacon (or uv add promptbeacon)

Usage:
    python examples/competitor_analysis.py
"""

import os
from dotenv import load_dotenv
load_dotenv()

from promptbeacon import Beacon, Provider

def main():
    print("=" * 60)
    print("PromptBeacon - Competitor Analysis")
    print("=" * 60)
    print()

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set!")
        return

    # Define brand and competitors
    brand = "Nike"
    competitors = ["Adidas", "Puma"]

    print(f"Brand: {brand}")
    print(f"Competitors: {', '.join(competitors)}")
    print("-" * 40)

    # Configure beacon with competitors
    beacon = (
        Beacon(brand)
        .with_competitors(*competitors)
        .with_providers(Provider.OPENAI)
        .with_categories("running shoes", "sports brand")
        .with_prompt_count(3)
    )

    print("\nRunning competitive analysis...")
    report = beacon.scan()

    # Results
    print("\n" + "=" * 60)
    print("COMPETITIVE ANALYSIS RESULTS")
    print("=" * 60)

    # Brand visibility
    print(f"\n🏆 {brand} Visibility Score: {report.visibility_score:.1f}/100")

    # Competitor comparison
    if report.competitor_comparison:
        print("\n📊 Competitor Scores:")
        print("-" * 40)
        print(f"{'Brand':<20} {'Score':<10} {'Mentions':<10}")
        print("-" * 40)
        print(f"{brand:<20} {report.visibility_score:<10.1f} {report.mention_count:<10}")

        for name, score in report.competitor_comparison.items():
            print(f"{name:<20} {score.visibility_score:<10.1f} {score.mention_count:<10}")

        # Determine leader
        all_scores = [(brand, report.visibility_score)]
        all_scores.extend([(n, s.visibility_score) for n, s in report.competitor_comparison.items()])
        leader = max(all_scores, key=lambda x: x[1])

        print("-" * 40)
        print(f"\n🥇 Market Leader: {leader[0]} ({leader[1]:.1f})")

        # Gap analysis
        if leader[0] != brand:
            gap = leader[1] - report.visibility_score
            print(f"📉 Gap to Leader: {gap:.1f} points")
        else:
            print(f"✅ {brand} is the visibility leader!")

    print("\n" + "=" * 60)
    print("Analysis complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
