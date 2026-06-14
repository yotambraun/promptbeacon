#!/usr/bin/env python3
"""Stability scan — how much should you trust a single number?

Answer engines are probabilistic. A stability scan repeats each prompt N times
and reports a 0-100 trust score, a confidence interval, and which prompts
flip-flop. Shown here in keyless demo mode (no API keys).

NOTE: a real stability scan multiplies API calls by N and bypasses the cache.

Usage:
    python examples/stability_scan.py
"""

from promptbeacon import Beacon


def main():
    report = (
        Beacon("Nike")
        .demo()
        .with_competitors("Adidas")
        .with_categories("running shoes")
        .with_prompt_count(6)
        .with_stability(5)  # repeat every prompt 5 times
        .scan_stability()
    )

    s = report.stability
    print(
        f"Stability score:        {s.stability_score}/100 ({s.volatility.stability_rating})"
    )
    print(f"Score per run:          {s.score_per_run}")
    print(f"95% confidence interval:{s.score_confidence_interval}")
    print(f"Presence consistency:   {s.overall_presence_consistency:.0%}")
    print(f"Flip-flopping prompts:  {s.flip_flop_count}")

    print("\nPer-prompt stability:")
    for p in s.prompt_stability:
        flag = "  (flip-flops)" if p.flip_flopped else ""
        print(f"  {p.appearances}/{p.runs} runs  {p.prompt[:50]}...{flag}")


if __name__ == "__main__":
    main()
