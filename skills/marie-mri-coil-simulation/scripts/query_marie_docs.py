#!/usr/bin/env python3
"""Search the MARIE documentation snapshot bundled with this skill."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
DOC_ROOT = SKILL_ROOT / "references" / "workspace-docs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", default="", help="Text or regex to find")
    parser.add_argument("--regex", action="store_true", help="Interpret query as regex")
    parser.add_argument("--headings", action="store_true", help="Search Markdown headings only")
    parser.add_argument("--files", action="store_true", help="List bundled documents")
    parser.add_argument("--context", type=int, default=2, help="Context lines around a match")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON")
    return parser.parse_args()


def documents() -> list[Path]:
    if not DOC_ROOT.is_dir():
        raise FileNotFoundError(f"Bundled documentation is missing: {DOC_ROOT}")
    return sorted(DOC_ROOT.glob("*.md"), key=lambda path: path.name.casefold())


def matcher(query: str, regex: bool):
    if regex:
        pattern = re.compile(query, re.IGNORECASE)
        return lambda text: pattern.search(text) is not None
    needle = query.casefold()
    return lambda text: needle in text.casefold()


def main() -> int:
    args = parse_args()
    docs = documents()

    if args.files or not args.query:
        rows = [{"file": path.name, "bytes": path.stat().st_size} for path in docs]
        if args.as_json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            for row in rows:
                print(f"{row['file']}\t{row['bytes']} bytes")
        return 0

    try:
        matches = matcher(args.query, args.regex)
    except re.error as exc:
        print(f"Invalid regular expression: {exc}", file=sys.stderr)
        return 2

    results: list[dict[str, object]] = []
    for path in docs:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        for index, line in enumerate(lines):
            if args.headings and not re.match(r"^#{1,6}\s", line):
                continue
            if not matches(line):
                continue
            start = max(0, index - max(args.context, 0))
            end = min(len(lines), index + max(args.context, 0) + 1)
            results.append(
                {
                    "file": path.name,
                    "line": index + 1,
                    "text": line,
                    "context": lines[start:end],
                }
            )

    if args.as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for result in results:
            print(f"{result['file']}:{result['line']}: {result['text']}")
            if args.context:
                for context_line in result["context"]:
                    print(f"    {context_line}")
        if not results:
            print(f"No matches for: {args.query}", file=sys.stderr)

    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main())
