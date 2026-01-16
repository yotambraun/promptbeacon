#!/usr/bin/env python3
"""
Basic Brand Visibility Scan Example

This example demonstrates how to use PromptBeacon to analyze
how a brand appears in AI-generated responses.

Prerequisites:
    - Set OPENAI_API_KEY environment variable or use a .env file
    - pip install promptbeacon (or uv add promptbeacon)

Usage:
    python examples/basic_scan.py
"""

import os

# Load environment variables from .env file if it exists
from dotenv import load_dotenv

load_dotenv()

from promptbeacon import Beacon, Provider  # noqa: E402


def main():
    print("=" * 60)
    print("PromptBeacon - Basic Brand Visibility Scan")
    print("=" * 60)
    print()

    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set!")
        print("Please set it in your environment or .env file")
        return

    print(f"API Key found: {api_key[:10]}...{api_key[-4:]}")

    # Create a Beacon for Nike brand
    brand = "Nike"
    print(f"Scanning visibility for: {brand}")
    print("-" * 40)

    # Configure the beacon
    beacon = (
        Beacon(brand)
        .with_providers(Provider.OPENAI)
        .with_categories("running shoes", "athletic wear")
        .with_prompt_count(3)  # Small number for demo
    )

    # Run the scan
    print("\nQuerying LLM providers...")
    report = beacon.scan()

    # Display results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    print(f"\n📊 Visibility Score: {report.visibility_score:.1f}/100")
    print(f"📝 Total Mentions: {report.mention_count}")
    print(f"⏱️  Scan Duration: {report.scan_duration_seconds:.1f}s")

    if report.total_cost_usd:
        print(f"💰 Estimated Cost: ${report.total_cost_usd:.4f}")

    # Sentiment breakdown
    print("\n📈 Sentiment Breakdown:")
    print(f"   ✅ Positive: {report.sentiment_breakdown.positive:.1%}")
    print(f"   ➖ Neutral:  {report.sentiment_breakdown.neutral:.1%}")
    print(f"   ❌ Negative: {report.sentiment_breakdown.negative:.1%}")

    # Show any errors
    errors = [r for r in report.provider_results if r.error]
    if errors:
        print(f"\n⚠️  Errors encountered: {len(errors)}")
        for r in errors[:3]:
            print(f"   - {r.error[:100]}...")

    # Show explanations
    if report.explanations:
        print("\n💡 Key Insights:")
        for exp in report.explanations[:3]:
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(exp.impact, "⚪")
            print(f"   {icon} [{exp.category}] {exp.message}")

    # Show recommendations
    if report.recommendations:
        print("\n🎯 Recommendations:")
        for rec in report.recommendations[:3]:
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec.priority, "⚪")
            print(f"   {icon} [{rec.priority.upper()}] {rec.action}")

    # Show sample responses
    successful = [r for r in report.provider_results if r.success and r.response]
    if successful:
        print("\n📄 Sample LLM Responses:")
        for i, result in enumerate(successful[:2], 1):
            print(f"\n   --- Response {i} ({result.provider}/{result.model}) ---")
            print(f"   Prompt: {result.prompt[:60]}...")
            response_preview = result.response[:200].replace('\n', ' ')
            print(f"   Response: {response_preview}...")
            if result.mentions:
                print(f"   Mentions found: {len(result.mentions)}")
    else:
        print("\n📄 No successful responses received.")

    print("\n" + "=" * 60)
    print("Scan complete!")
    print("=" * 60)

    return report


if __name__ == "__main__":
    main()
