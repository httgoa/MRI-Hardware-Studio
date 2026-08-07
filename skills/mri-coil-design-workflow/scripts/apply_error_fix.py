#!/usr/bin/env python3
"""L2 deterministic error-fix executor for the artifact-first pipeline.

This is the CODE that consumes `pitfalls/error-fixes.md`. Until now that file
was a lookup TABLE with no consumer; the "L2 known-fix (zero LLM)" rung of the
error ladder was documented but unimplemented. This module closes that gap:

    L1 batch_execute → reports {failed_index, error, bas_path}
    L2 apply_error_fix →  match error text/content against error-fixes.md
                          signatures → for the .bas-text-patchable kinds, rewrite
                          the .bas deterministically (ZERO LLM) → caller resumes
                          run_blocks(start_index=failed_index)
    L3 (no match / not patchable) → bounded main-agent repair

Honest scope — NOT every signature is a `.bas` text edit:
  * PATCHABLE here (pure text transform on the failing .bas):
      F1  rename_param          reserved/keyword param → name+"0" + rewrite refs
      F2  replace_store_param    StoreDoubleParameter → ReportInformationToWindow
      F4  trim_solver_setters    drop known newer-version setters in With <Solver>
      F10 offset_schematic_coord add 50000 to raw .Position coords
  * MATCH-ONLY (fix is a tool-arg / live-schematic / ordering change, not a file
    edit) — the executor returns applicable=True, patchable=False, and the
    `action` string so the caller (or L3 agent) applies it:
      F3 combine_filter · F5 split_net · F6 purge_zombie_nets ·
      F7 prepend_pick_edges · F8 fix_save_kwarg · F9 reorder_export_before_sar ·
      F11 route_to_python; F12 reload_history_payload

Usage (standalone, dry-run a match + patch preview):
  python apply_error_fix.py --bas path/to/solver.bas \
      --error-text "(10091) ActiveX Automation: no such property or method. (.SweepTolerance)"
  # add --write to patch the .bas in place

Usage (inside cst_run_python_tool, wired to batch_execute):
  exec(open(r"...apply_error_fix.py", encoding="utf-8").read())
  fix = try_l2_fix(result, blocks)        # result from run_blocks(...)
  # if fix["patched"]: rerun run_blocks(project, de, blocks, start_index=result["failed_index"])
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Reserved words (kept in sync with lint_vba.RESERVED_NAMES) for F1.
RESERVED_NAMES = {
    "lambda", "and", "or", "not", "is", "in", "if", "else", "elif", "for",
    "while", "def", "class", "return", "import", "from", "as", "with", "try",
    "except", "finally", "pass", "break", "continue", "global", "none", "true",
    "false", "del", "yield", "raise", "assert",
    "dim", "sub", "function", "then", "end", "set", "call", "next", "loop",
    "do", "wend", "each", "byval", "byref", "nothing", "empty", "new", "mod",
}

# F4: setters known to come from newer-version .mod exports that this CST
# version's API rejects ("no such property or method"). Dropping ONLY these is
# safe (CST keeps its defaults); this is deterministic, unlike guessing a
# "required" allowlist. Extend as new offenders are verified.
KNOWN_BAD_SOLVER_SETTERS = {
    "sweeptolerance", "sweeperrorchecks", "sweepminimumsamples",
    "sweepconsiderall", "setnumberofresultdatasamples", "autonormimpedance",
    "calcstatbfield", "calcpowerlosspercomponent",
}

_PARAM_DEF_RES = [
    re.compile(r'(MakeSureParameterExists\s*\(?\s*")([^"]+)(")', re.IGNORECASE),
    re.compile(r'(StoreParameter\s*\(?\s*")([^"]+)(")', re.IGNORECASE),
    re.compile(r'(StoreDoubleParameter\s*\(?\s*")([^"]+)(")', re.IGNORECASE),
]


def _default_error_fixes_md() -> Path:
    return Path(__file__).resolve().parent.parent / "pitfalls" / "error-fixes.md"


def load_signatures(md_path: Optional[str] = None) -> List[Dict]:
    """Parse the ```json … ``` machine-readable block from error-fixes.md."""
    p = Path(md_path) if md_path else _default_error_fixes_md()
    text = p.read_text(encoding="utf-8")
    m = re.search(r"```json\s*(.+?)```", text, re.DOTALL)
    if not m:
        raise ValueError(f"no ```json``` signature block found in {p}")
    return json.loads(m.group(1))


def match_error(error_text: str, bas_content: str,
                signatures: List[Dict]) -> Optional[Dict]:
    """Return the first signature whose match/content_match both hold, else None."""
    et = error_text or ""
    bc = bas_content or ""
    for sig in signatures:
        pat = sig.get("match")
        ok = True
        if pat:
            if sig.get("regex"):
                ok = re.search(pat, et, re.IGNORECASE) is not None
            else:
                ok = pat.lower() in et.lower()
        elif sig.get("content_match") is None:
            ok = False  # no match rule at all → never auto-fire
        if not ok:
            continue
        cm = sig.get("content_match")
        if cm and re.search(cm, bc, re.IGNORECASE) is None:
            continue
        return sig
    return None


# --------------------------------------------------------------------------- #
# Deterministic .bas text patchers (the PATCHABLE kinds).
# Each returns (new_content, note). Raise if it cannot patch safely.
# --------------------------------------------------------------------------- #
def _patch_rename_param(bas: str, error_text: str) -> Tuple[str, str]:
    """F1: rename any reserved-word param to name+'0' and rewrite bare refs."""
    renamed = []
    lines = bas.splitlines()
    # find reserved param names actually defined in this block
    targets = set()
    for ln in lines:
        for rx in _PARAM_DEF_RES:
            for mm in rx.finditer(ln):
                nm = mm.group(2)
                if nm.lower() in RESERVED_NAMES:
                    targets.add(nm)
    if not targets:
        raise ValueError("F1 matched but no reserved param name found in block")
    out = bas
    for nm in targets:
        new = nm + "0"
        # rewrite every whole-word occurrence (definition + references)
        out = re.sub(rf'\b{re.escape(nm)}\b', new, out)
        renamed.append(f"{nm}->{new}")
    return out, f"renamed reserved params: {', '.join(renamed)}"


def _patch_replace_store_param(bas: str, error_text: str) -> Tuple[str, str]:
    """F2: StoreDoubleParameter "K", v  →  ReportInformationToWindow("K=" & CStr(v))."""
    rx = re.compile(
        r'StoreDoubleParameter\s*\(?\s*"([^"]+)"\s*,\s*(.+?)\s*\)?\s*$',
        re.IGNORECASE)
    n = 0
    out_lines = []
    for ln in bas.splitlines():
        m = rx.search(ln.strip())
        if m:
            key, val = m.group(1), m.group(2).rstrip(")")
            indent = ln[:len(ln) - len(ln.lstrip())]
            out_lines.append(f'{indent}ReportInformationToWindow("{key}=" & CStr({val}))')
            n += 1
        else:
            out_lines.append(ln)
    if n == 0:
        raise ValueError("F2 matched but no StoreDoubleParameter line found")
    return "\n".join(out_lines) + ("\n" if bas.endswith("\n") else ""), \
        f"replaced {n} StoreDoubleParameter call(s) with ReportInformationToWindow"


def _patch_trim_solver_setters(bas: str, error_text: str) -> Tuple[str, str]:
    """F4: drop known newer-version setters inside a With <Solver> block."""
    dropped = []
    out_lines = []
    in_solver = False
    solver_open = re.compile(r'^\s*With\s+(FDSolver|IESolver|Solver)\b', re.IGNORECASE)
    for ln in bas.splitlines():
        if solver_open.match(ln):
            in_solver = True
            out_lines.append(ln)
            continue
        if in_solver and re.match(r'^\s*End\s+With\b', ln, re.IGNORECASE):
            in_solver = False
            out_lines.append(ln)
            continue
        if in_solver:
            m = re.match(r'^\s*\.([A-Za-z_][A-Za-z0-9_]*)', ln)
            if m and m.group(1).lower() in KNOWN_BAD_SOLVER_SETTERS:
                dropped.append(m.group(1))
                continue  # drop it
        out_lines.append(ln)
    if not dropped:
        raise ValueError("F4 matched but no known-bad solver setter found to drop")
    return "\n".join(out_lines) + ("\n" if bas.endswith("\n") else ""), \
        f"dropped {len(dropped)} newer-version setter(s): {', '.join(dropped)}"


def _patch_offset_schematic_coord(bas: str, error_text: str) -> Tuple[str, str]:
    """F10: add 50000 to raw .Position(x, y) coords that were not offset."""
    rx = re.compile(r'(\.Position\s*\(?\s*)(-?\d+)(\s*,\s*)(-?\d+)', re.IGNORECASE)
    n = [0]

    def repl(m):
        x, y = int(m.group(2)), int(m.group(4))
        # only offset raw stored coords (|c| < 40000); skip already-offset ones
        nx = x + 50000 if abs(x) < 40000 else x
        ny = y + 50000 if abs(y) < 40000 else y
        if (nx, ny) != (x, y):
            n[0] += 1
        return f"{m.group(1)}{nx}{m.group(3)}{ny}"

    out = rx.sub(repl, bas)
    if n[0] == 0:
        raise ValueError("F10 matched but no raw (<40000) .Position coord found")
    return out, f"offset {n[0]} .Position coord pair(s) by +50000"


_PATCHERS = {
    "rename_param": _patch_rename_param,
    "replace_store_param": _patch_replace_store_param,
    "trim_solver_setters": _patch_trim_solver_setters,
    "offset_schematic_coord": _patch_offset_schematic_coord,
}


def apply_fix(sig: Dict, bas_content: str, error_text: str = "") -> Dict:
    """Apply a matched signature to the .bas content when it's a text transform.

    Returns:
      {matched_id, fix_kind, auto, patchable, patched, content, note}
    - patchable=False → the fix is not a .bas edit (tool-arg / live op / ordering);
      `note` carries the signature's `action` for the caller/L3 to apply.
    """
    fix_kind = sig.get("fix_kind")
    base = {"matched_id": sig.get("id"), "fix_kind": fix_kind,
            "auto": bool(sig.get("auto"))}
    patcher = _PATCHERS.get(fix_kind)
    if patcher is None:
        return {**base, "patchable": False, "patched": False, "content": None,
                "note": sig.get("action", "")}
    try:
        new_content, note = patcher(bas_content, error_text)
    except Exception as exc:  # noqa: BLE001 — report why the patch couldn't apply
        return {**base, "patchable": True, "patched": False, "content": None,
                "note": f"patch failed: {exc}"}
    return {**base, "patchable": True, "patched": True, "content": new_content,
            "note": note}


def try_l2_fix(batch_result: Dict, blocks, error_fixes_md: Optional[str] = None,
               write: bool = True) -> Dict:
    """Convenience for the in-CST loop: take a run_blocks() result, attempt L2.

    blocks: the same [(title, bas_path), ...] passed to run_blocks.
    On a patchable hit it rewrites the failing .bas in place (write=True) so a
    subsequent run_blocks(start_index=batch_result["failed_index"]) picks it up.
    Returns the apply_fix dict augmented with {failed_index, bas_path, resume_index}.
    """
    fi = batch_result.get("failed_index")
    if fi is None:
        return {"patched": False, "note": "no failed block", "failed_index": None}
    title, bas_path = blocks[fi]
    error_text = ""
    for e in batch_result.get("executed", []):
        if e.get("status") == "error":
            error_text = e.get("error") or ""
    bas_content = Path(bas_path).read_text(encoding="utf-8", errors="replace")
    sigs = load_signatures(error_fixes_md)
    sig = match_error(error_text, bas_content, sigs)
    if sig is None:
        return {"patched": False, "matched_id": None, "failed_index": fi,
                "bas_path": bas_path,
                "note": "no L2 signature matched — escalate to L3"}
    res = apply_fix(sig, bas_content, error_text)
    res.update({"failed_index": fi, "bas_path": bas_path,
                "resume_index": fi})
    if res.get("patched") and write:
        Path(bas_path).write_text(res["content"], encoding="utf-8")
        res["written"] = True
    return res


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="L2 deterministic error-fix executor.")
    ap.add_argument("--bas", required=True, help="the failing .bas file")
    ap.add_argument("--error-text", required=True, help="exact CST error text")
    ap.add_argument("--error-fixes", default=None, help="path to error-fixes.md")
    ap.add_argument("--write", action="store_true", help="patch the .bas in place")
    args = ap.parse_args(argv)

    bas_content = Path(args.bas).read_text(encoding="utf-8", errors="replace")
    sigs = load_signatures(args.error_fixes)
    sig = match_error(args.error_text, bas_content, sigs)
    if sig is None:
        print(json.dumps({"matched": None,
                          "note": "no signature matched — escalate to L3"}, indent=2))
        return 1
    res = apply_fix(sig, bas_content, args.error_text)
    if res.get("patched") and args.write:
        Path(args.bas).write_text(res["content"], encoding="utf-8")
        res["written"] = True
    printable = {k: v for k, v in res.items() if k != "content"}
    printable["content_preview"] = (res.get("content") or "")[:400] or None
    print(json.dumps(printable, ensure_ascii=False, indent=2))
    return 0 if res.get("patched") or not res.get("patchable") else 2


if __name__ == "__main__":
    sys.exit(main())
