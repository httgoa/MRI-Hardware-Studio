#!/usr/bin/env python3
"""Append one structured MARIE architecture update to the skill registry."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--title", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--paths", required=True)
    parser.add_argument("--interfaces", required=True)
    parser.add_argument("--compatibility", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "references"
        / "architecture-interfaces.md",
    )
    args = parser.parse_args()

    if not args.registry.is_file():
        parser.error(f"registry not found: {args.registry}")

    entry = (
        f"\n### {args.date} — {args.title}\n\n"
        f"- Summary: {args.summary}\n"
        f"- Paths: {args.paths}.\n"
        f"- Interfaces: {args.interfaces}.\n"
        f"- Compatibility: {args.compatibility}.\n"
        f"- Evidence: {args.evidence}.\n"
    )
    with args.registry.open("a", encoding="utf-8") as handle:
        handle.write(entry)
    print(args.registry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
