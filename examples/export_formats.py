#!/usr/bin/env python3
"""
Export Formats Example

This example demonstrates the various export formats available
in PromptBeacon for reports.

Prerequisites:
    - Set OPENAI_API_KEY environment variable or use a .env file
    - pip install promptbeacon[pandas] (for DataFrame export)

Usage:
    python examples/export_formats.py
"""

import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from promptbeacon import Beacon, Provider, to_json, to_csv, to_markdown

def main():
    print("=" * 60)
    print("PromptBeacon - Export Formats Demo")
    print("=" * 60)
    print()

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set!")
        return

    # Quick scan
    beacon = (
        Beacon("Nike")
        .with_providers(Provider.OPENAI)
        .with_categories("sports")
        .with_prompt_count(2)
    )

    print("Running scan...")
    report = beacon.scan()
    print(f"Scan complete! Score: {report.visibility_score:.1f}/100\n")

    # Create output directory
    output_dir = Path("examples/output")
    output_dir.mkdir(exist_ok=True)

    # JSON Export
    print("📄 JSON Export:")
    json_output = to_json(report)
    json_file = output_dir / "report.json"
    json_file.write_text(json_output)
    print(f"   Saved to: {json_file}")
    print(f"   Preview: {json_output[:100]}...\n")

    # CSV Export
    print("📊 CSV Export:")
    csv_output = to_csv(report)
    csv_file = output_dir / "report.csv"
    csv_file.write_text(csv_output)
    print(f"   Saved to: {csv_file}")
    print(f"   Content:\n{csv_output}\n")

    # Markdown Export
    print("📝 Markdown Export:")
    md_output = to_markdown(report)
    md_file = output_dir / "report.md"
    md_file.write_text(md_output)
    print(f"   Saved to: {md_file}")
    print(f"   Preview (first 500 chars):\n{md_output[:500]}...\n")

    # DataFrame Export (if pandas available)
    try:
        from promptbeacon import to_dataframe
        print("📈 DataFrame Export:")
        df = to_dataframe(report)
        print(f"   Shape: {df.shape}")
        print(f"   Columns: {list(df.columns)}")
        print(f"   Data:\n{df.to_string()}\n")
    except ImportError:
        print("📈 DataFrame Export: (skipped - pandas not installed)")

    print("=" * 60)
    print(f"All exports saved to: {output_dir.absolute()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
