"""``python -m pbindex``: validate, estimate, run and build the Index.

Run from the ``index`` directory (or with ``index`` on ``PYTHONPATH``).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

from pbindex.protocol import CATEGORIES_DIR, INDEX_DIR, load_protocols
from pbindex.runner import IndexBudgetError, estimate, missing_keys, run_index
from pbindex.site import build_site
from promptbeacon.budget import format_usd

DATA_DIR = INDEX_DIR / "data"
SITE_DIR = INDEX_DIR / "site"
DEMO_DIR = INDEX_DIR / "demo"


def _categories(value: str | None) -> list[str] | None:
    return [c.strip() for c in value.split(",") if c.strip()] if value else None


def cmd_validate(args: argparse.Namespace) -> int:
    protocols = load_protocols(args.protocols, _categories(args.categories))
    candidates = sum(len(p.candidates) for p in protocols)
    print(f"{len(protocols)} protocols, {candidates} candidate projects: valid.")
    return 0


def cmd_estimate(args: argparse.Namespace) -> int:
    protocols = load_protocols(args.protocols, _categories(args.categories))
    priced = estimate(protocols)
    width = max(len(p.id) for p, _ in priced)
    for proto, est in priced:
        print(
            f"{proto.id:<{width}}  {est.answers:>4} answers  "
            f"{format_usd(est.total_usd):>8}  (at most {format_usd(est.upper_usd)})"
        )
    total = sum(e.total_usd for _, e in priced)
    upper = sum(e.upper_usd for _, e in priced)
    answers = sum(e.answers for _, e in priced)
    print(
        f"\nTotal: {answers} answers, about {format_usd(total)} per run "
        f"(at most {format_usd(upper)}). {priced[0][1].assumptions}."
    )
    unpriced = sorted({m for _, e in priced for m in e.unpriced})
    if unpriced:
        print("Counted as $0 (no known price): " + ", ".join(unpriced))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    protocols = load_protocols(args.protocols, _categories(args.categories))
    data_dir = args.data or (DEMO_DIR / "data" if args.demo else DATA_DIR)
    if not args.demo:
        missing = missing_keys(protocols)
        if missing:
            print(
                "Missing API keys for: " + ", ".join(missing) + ". Set the keys "
                "(OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, ...) or use --demo.",
                file=sys.stderr,
            )
            return 2
    try:
        written = asyncio.run(
            run_index(
                protocols,
                data_dir,
                demo=args.demo,
                max_cost=args.max_cost,
                day=date.fromisoformat(args.date) if args.date else None,
                concurrency=args.concurrency,
            )
        )
    except IndexBudgetError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    label = "DEMO snapshots (not a measurement)" if args.demo else "snapshots"
    print(f"Wrote {len(written)} {label} to {data_dir}")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    data_dir = args.data or (DEMO_DIR / "data" if args.demo else DATA_DIR)
    out = args.out or (DEMO_DIR / "html" if args.demo else SITE_DIR)
    if not any(data_dir.glob("*/*.json")):
        print(
            f"No snapshots in {data_dir}. Run `python -m pbindex run` first.",
            file=sys.stderr,
        )
        return 1
    protocols = load_protocols(args.protocols)
    written = build_site(data_dir, out, protocols, base_url=args.base_url)
    print(f"Wrote {len(written)} files to {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pbindex",
        description="The AI Recommendation Index: run pinned protocols, rank "
        "projects by measured mention rate, and build the static site.",
    )
    parser.add_argument(
        "--protocols", type=Path, default=CATEGORIES_DIR, help="Protocol directory"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="Check every protocol file")
    p.add_argument("--categories", help="Comma-separated category ids")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("estimate", help="Estimated cost of a run (sends nothing)")
    p.add_argument("--categories", help="Comma-separated category ids")
    p.set_defaults(func=cmd_estimate)

    p = sub.add_parser("run", help="Ask the models and write snapshots")
    p.add_argument("--categories", help="Comma-separated category ids (default: all)")
    p.add_argument(
        "--max-cost", type=float, help="Spending cap in US dollars (required live)"
    )
    p.add_argument(
        "--demo", action="store_true", help="Offline mock answers, $0, labelled demo"
    )
    p.add_argument(
        "--data", type=Path, help="Data directory (default: data/ or demo/data/)"
    )
    p.add_argument("--date", help="Snapshot date, YYYY-MM-DD (default: today, UTC)")
    p.add_argument("--concurrency", type=int, default=4, help="Requests per provider")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("build", help="Render the static site from the latest snapshots")
    p.add_argument(
        "--demo", action="store_true", help="Build from demo/data into demo/html"
    )
    p.add_argument("--data", type=Path, help="Data directory")
    p.add_argument("--out", type=Path, help="Output directory (replaced)")
    p.add_argument("--base-url", help="Public URL of the site, for badge snippets")
    p.set_defaults(func=cmd_build)

    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
