#!/usr/bin/env python3
"""L0 deterministic VBA lint/repair for the artifact-first pipeline.

Runs BEFORE any CST execution, with ZERO LLM. Catches the errors that are
statically detectable in a generated `.bas` history block so they never reach
CST: markdown fences, stray prose, unbalanced blocks, duplicate/keyword
parameter names. Mirrors the intent of LEAM's `_clean_vba` / `_ensure_sub_main`
but scoped to CST history blocks.

Usage:
  # lint one file, print JSON report, exit non-zero if errors remain
  python lint_vba.py path/to/model_3d.bas

  # lint + auto-fix in place (strips fences/prose, normalizes), then re-report
  python lint_vba.py --fix path/to/model_3d.bas

  # lint every .bas under a folder
  python lint_vba.py results/dipole_scratch/artifacts

  # macro kind (for schematic execute_vba_code): also enforce a Sub Main wrapper
  python lint_vba.py --kind macro path/to/parameter_update.bas

Exit code: 0 if no ERROR-severity issues remain, 1 otherwise. WARNING issues
never fail the run.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# VBA / Python reserved words that must NOT be used as CST parameter names
# (pitfall #1: MakeSureParameterExists "lambda" is rejected through the MCP bridge).
RESERVED_NAMES = {
    # Python keywords commonly collided with
    "lambda", "and", "or", "not", "is", "in", "if", "else", "elif", "for",
    "while", "def", "class", "return", "import", "from", "as", "with", "try",
    "except", "finally", "pass", "break", "continue", "global", "none", "true",
    "false", "del", "yield", "raise", "assert",
    # VBA keywords
    "dim", "sub", "function", "then", "end", "set", "call", "next", "loop",
    "do", "wend", "each", "byval", "byref", "nothing", "empty", "new", "mod",
}

FENCE_RE = re.compile(r"^\s*```")
PARAM_DEF_RES = [
    re.compile(r'MakeSureParameterExists\s*\(?\s*"([^"]+)"', re.IGNORECASE),
    re.compile(r'StoreParameter\s*\(?\s*"([^"]+)"', re.IGNORECASE),
    re.compile(r'StoreDoubleParameter\s*\(?\s*"([^"]+)"', re.IGNORECASE),
]
# A line that looks like a real VBA statement (used to spot stray prose).
VBA_LINE_RE = re.compile(
    r'^\s*('
    r"'"  # comment
    r"|\.[A-Za-z_]"  # .Member call inside a With block
    r"|[A-Za-z_][A-Za-z0-9_]*\s*(\([^\n]*\))?\s*="  # assignment: x = / arr(i) = / arr(i,j) =
    r"|(Dim|With|Sub|Function|End|If|Then|Else|ElseIf|For|Next|Do|Loop|While|Wend|Set|Call|Let|"
    r"Open|Close|Print|Write|Input|Put|Get|Kill|Name|Exit|On|Error|Resume|GoTo|Return|Stop|"
    r"Select|Case|Erase|ReDim|Option|Const|Public|Private|Static|Randomize|Rem|"
    r"StoreParameter|StoreDoubleParameter|MakeSureParameterExists|Rebuild|Solver|ChangeSolverType|Component|"
    r"Material|Boundary|Background|Units|Pick|Transform|Brick|Cylinder|Sphere|Cone|Torus|"
    r"ECylinder|Extrude|AnalyticalFace|Polygon|Polygon3D|WCS|Port|DiscretePort|DiscreteFacePort|"
    r"LumpedFaceElement|Monitor|Mesh|MeshSettings|SelectTreeItem|ASCIIExport|Group|Solid|"
    r"AddToHistory|Plot|FarfieldPlot|Result3D|SAR|Net|Block|ExternalPort)\b"
    r"|[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_]"  # object.Method(...)
    r")",
    re.IGNORECASE,
)

# Balanced-block openers → closers (case-insensitive, line-anchored where sensible).
BALANCE_PAIRS = [
    (re.compile(r'^\s*With\b', re.IGNORECASE), re.compile(r'^\s*End\s+With\b', re.IGNORECASE), "With / End With"),
    (re.compile(r'^\s*Sub\b', re.IGNORECASE), re.compile(r'^\s*End\s+Sub\b', re.IGNORECASE), "Sub / End Sub"),
    (re.compile(r'^\s*Function\b', re.IGNORECASE), re.compile(r'^\s*End\s+Function\b', re.IGNORECASE), "Function / End Function"),
    (re.compile(r'^\s*For\b', re.IGNORECASE), re.compile(r'^\s*Next\b', re.IGNORECASE), "For / Next"),
    (re.compile(r'^\s*Do\b', re.IGNORECASE), re.compile(r'^\s*Loop\b', re.IGNORECASE), "Do / Loop"),
]
# If ... Then (single-line "If x Then y" is self-closing; only multi-line block Ifs need End If)
IF_BLOCK_RE = re.compile(r'^\s*If\b.*\bThen\s*$', re.IGNORECASE)
END_IF_RE = re.compile(r'^\s*End\s+If\b', re.IGNORECASE)


def strip_fences(text: str) -> Tuple[str, int]:
    """Remove markdown code-fence lines. Returns (clean_text, num_removed)."""
    if text and text[0] == "\ufeff":  # defensive BOM strip
        text = text[1:]
    out, removed = [], 0
    for line in text.splitlines():
        if FENCE_RE.match(line):
            removed += 1
            continue
        out.append(line)
    return "\n".join(out), removed


def lint_text(text: str, kind: str = "history") -> Dict:
    """Analyze VBA text. Returns a report dict with issues (no mutation)."""
    issues: List[Dict] = []
    clean, fences = strip_fences(text)
    if fences:
        issues.append({"severity": "error", "code": "markdown_fence",
                       "msg": f"{fences} markdown code-fence line(s) found; strip with --fix"})

    lines = clean.splitlines()

    # Balanced blocks
    for opener, closer, label in BALANCE_PAIRS:
        opens = sum(1 for ln in lines if opener.match(ln))
        closes = sum(1 for ln in lines if closer.match(ln))
        if opens != closes:
            issues.append({"severity": "error", "code": "unbalanced_block",
                           "msg": f"{label}: {opens} open vs {closes} close"})
    n_if = sum(1 for ln in lines if IF_BLOCK_RE.match(ln))
    n_endif = sum(1 for ln in lines if END_IF_RE.match(ln))
    if n_if != n_endif:
        issues.append({"severity": "error", "code": "unbalanced_block",
                       "msg": f"If(block) / End If: {n_if} open vs {n_endif} close"})

    # Parameter names: duplicates + reserved words (pitfall #1)
    seen: Dict[str, int] = {}
    for ln in lines:
        for rx in PARAM_DEF_RES:
            for name in rx.findall(ln):
                seen[name] = seen.get(name, 0) + 1
                if name.lower() in RESERVED_NAMES:
                    issues.append({"severity": "error", "code": "reserved_param_name",
                                   "msg": f'parameter "{name}" is a VBA/Python keyword; rename (e.g. {name}0)'})
    for name, count in seen.items():
        if count > 1:
            issues.append({"severity": "warning", "code": "duplicate_param",
                           "msg": f'parameter "{name}" defined {count}x; keep one definition'})

    # Stray prose (non-VBA, non-blank, non-comment lines)
    for i, ln in enumerate(lines, 1):
        if not ln.strip():
            continue
        if not VBA_LINE_RE.match(ln):
            issues.append({"severity": "warning", "code": "suspect_line",
                           "msg": f"line {i} does not look like VBA: {ln.strip()[:60]!r}"})

    # Macro kind must be wrapped in Sub Main for execute_vba_code
    if kind == "macro":
        has_sub = any(re.match(r'^\s*(Sub|Function)\b', ln, re.IGNORECASE) for ln in lines)
        if not has_sub:
            issues.append({"severity": "warning", "code": "missing_sub_main",
                           "msg": "macro kind has no Sub/Function wrapper; --fix will add Sub Main"})
    # History kind (add_to_history) must be RAW — a wrapping Sub Main breaks it
    if kind == "history" and _has_wrapping_sub_main(lines):
        issues.append({"severity": "warning", "code": "history_has_sub_main",
                       "msg": "history block is wrapped in Sub Main; --fix will strip it (add_to_history needs raw commands)"})

    errors = [x for x in issues if x["severity"] == "error"]
    return {"kind": kind, "ok": len(errors) == 0, "issues": issues,
            "n_error": len(errors), "n_warning": len(issues) - len(errors)}


def _has_wrapping_sub_main(lines: List[str]) -> bool:
    """True if the block's first code line is `Sub Main` and last is `End Sub`."""
    code = [ln for ln in lines if ln.strip() and not ln.strip().startswith("'")]
    if len(code) < 2:
        return False
    first_ok = re.match(r'^\s*Sub\s+Main\s*(\(\s*\))?\s*$', code[0], re.IGNORECASE)
    last_ok = re.match(r'^\s*End\s+Sub\b', code[-1], re.IGNORECASE)
    return bool(first_ok and last_ok)


def fix_text(text: str, kind: str = "history") -> str:
    """Deterministically repair: strip fences, trim, normalize Sub Main wrapper."""
    clean, _ = strip_fences(text)
    clean = clean.strip("\n")
    lines = clean.splitlines()
    if kind == "macro":
        has_sub = any(re.match(r'^\s*(Sub|Function)\b', ln, re.IGNORECASE)
                      for ln in lines)
        if not has_sub and clean.strip():
            clean = f"Sub Main\n{clean}\nEnd Sub"
    elif kind == "history" and _has_wrapping_sub_main(lines):
        # Strip the outer `Sub Main` / `End Sub` — add_to_history needs raw commands.
        out, removed_first = [], False
        code_seen = False
        for ln in lines:
            stripped = ln.strip()
            if not code_seen and not removed_first and re.match(
                    r'^\s*Sub\s+Main\s*(\(\s*\))?\s*$', ln, re.IGNORECASE):
                removed_first = True
                code_seen = True
                continue
            if stripped and not stripped.startswith("'"):
                code_seen = True
            out.append(ln)
        # drop the last `End Sub`
        while out and not out[-1].strip():
            out.pop()
        if out and re.match(r'^\s*End\s+Sub\b', out[-1], re.IGNORECASE):
            out.pop()
        clean = "\n".join(out).strip("\n")
    return clean + "\n"


def _iter_bas(path: Path) -> List[Path]:
    if path.is_dir():
        return sorted(path.rglob("*.bas"))
    return [path]


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Deterministic VBA lint/repair (L0).")
    ap.add_argument("path", help="a .bas file or a directory to scan")
    ap.add_argument("--fix", action="store_true", help="repair in place, then re-lint")
    ap.add_argument("--kind", choices=["history", "macro"], default="history",
                    help="history = raw CST history block (default); macro = execute_vba_code (needs Sub Main)")
    args = ap.parse_args(argv)

    root = Path(args.path)
    if not root.exists():
        print(json.dumps({"error": f"path not found: {root}"}))
        return 1

    reports = []
    worst = 0
    for f in _iter_bas(root):
        text = f.read_text(encoding="utf-8-sig", errors="replace")
        if args.fix:
            fixed = fix_text(text, args.kind)
            if fixed != text:
                f.write_text(fixed, encoding="utf-8")
            text = fixed
        rep = lint_text(text, args.kind)
        rep["file"] = str(f)
        reports.append(rep)
        if rep["n_error"]:
            worst = 1

    print(json.dumps({"fixed": args.fix, "reports": reports}, ensure_ascii=False, indent=2))
    return worst


if __name__ == "__main__":
    sys.exit(main())
