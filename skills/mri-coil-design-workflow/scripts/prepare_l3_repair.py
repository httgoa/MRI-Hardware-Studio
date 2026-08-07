#!/usr/bin/env python3
r"""L3 bounded-repair scaffold for the artifact-first pipeline.

L3 is the rung AFTER L2 (deterministic known-fix) fails to match: the **main
agent** regenerates the ONE failing `.bas` block. That step inherently has an
LLM in the loop, so L3 can never be fully automated like L0–L2. But before this
scaffold existed, L3 was *pure improvisation* — the agent guessed which
reference to read, had no retry budget, and no structured handoff back to
`run_blocks`. That is the gap this closes.

This module makes the DETERMINISTIC parts of L3 real, leaving ONLY the actual
block-rewrite to the agent:

  1. context selection  — deterministically pick which `vba-knowledge/*.md`
                          reference(s) + official-doc pointers are relevant to
                          the failing block (by block-title category + error
                          keywords), and bundle them with the failing `.bas` +
                          exact error text.
  2. retry budget       — enforce ≤2 attempts via a tiny JSON state file next to
                          the artifacts; a 3rd failure → escalate to L4 (human).
  3. structured handoff — after the agent writes the regenerated block,
                          `finalize_l3_repair` validates + returns `resume_index`
                          so the caller re-runs run_blocks(start_index=...).

Flow (inside the recipe, after L2 returned no patch):
  exec(open(r"...\prepare_l3_repair.py", encoding="utf-8").read())
  ctx = prepare_l3_context(result, BLOCKS)          # 1: bundle for the agent
  if ctx["escalate_l4"]: ...surface to human...
  else:
     # 2: AGENT regenerates ctx["bas_path"] using ctx["knowledge"] + ctx["error"]
     #    (this is the ONLY LLM step; keep it to that one block)
     new_vba = <agent output>
     fin = finalize_l3_repair(ctx, new_vba)          # 3: write + lint + budget
     if fin["ok"]:
         result = run_blocks(project, de, BLOCKS, quiet=True, start_index=fin["resume_index"])

The agent is fed ONLY {failing block + exact error + selected knowledge}; it is
told to emit a raw history block (no Sub Main) for that one step and nothing
else. Retry budget and checkpoint keep the loop bounded.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional


def _skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


# Deterministic routing: a token found in the failing block's TITLE selects the
# canonical Tier-B reference(s) to feed the agent. Ordered; first-match-wins per
# token, all matching categories are unioned.
TITLE_KNOWLEDGE_MAP = [
    (r"\b(unit|background|boundary|setup)\b", ["mri-setup.md"]),
    (r"\b(material|mat)\b", ["mri-setup.md"]),
    (r"\b(geometr|dipole|brick|cylinder|structure|solid|coil|birdcage|loop|saddle)\b",
     ["geometry-primitives.md", "boolean-transform.md", "coil-geometry.md"]),
    (r"\b(port|feed|excitation)\b", ["ports-monitors-mesh.md"]),
    (r"\b(monitor|field)\b", ["ports-monitors-mesh.md"]),
    (r"\b(mesh)\b", ["ports-monitors-mesh.md"]),
    (r"\b(solver|solve|fdsolver|iesolver|eigenmode)\b", ["solvers.md"]),
    (r"\b(schematic|match|net|inductor|capacitor|tuning|wire)\b", ["schematic-match.md"]),
    (r"\b(export|ascii|hdf5|field.export)\b", ["field-export.md"]),
]

# Error-keyword → extra reference (augments title routing when the error itself
# names a subsystem the title didn't).
ERROR_KNOWLEDGE_HINTS = [
    (r"boolean|subtract|intersect|insert|imprint", ["boolean-transform.md"]),
    (r"discreteport|faceport|no points picked|no edge picked", ["ports-monitors-mesh.md"]),
    (r"solver|sweep|method|order", ["solvers.md"]),
    (r"net|electrical|pins", ["schematic-match.md"]),
    (r"asciiexport|selecttreeitem|current view", ["field-export.md"]),
]

# Official-doc pointers (SKILL iron rule: consult these before guessing a
# signature). Relative to the CST-MCP vendor devkit; surfaced as text pointers.
API_DOC_POINTERS = [
    r"external/CST-MCP/vendor/cst-runtime-cli/devkit/references/vba-official-reference.md",
    r"external/CST-MCP/vendor/cst-runtime-cli/devkit/references/cst-official-api-reference.md",
    r"CST Online Help: D:\ght\softwares\MRI_agent_softwares\Online Help\mergedProjects\**\*.htm",
]

MAX_L3_ATTEMPTS = 2


def _state_path(bas_path: str) -> Path:
    """Retry-budget state file, kept next to the failing artifact."""
    p = Path(bas_path)
    return p.parent / f".l3_{p.stem}.json"


def _load_state(bas_path: str) -> Dict:
    sp = _state_path(bas_path)
    if sp.exists():
        try:
            return json.loads(sp.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {"attempts": 0}


def _save_state(bas_path: str, state: Dict) -> None:
    _state_path(bas_path).write_text(json.dumps(state), encoding="utf-8")


def select_knowledge(block_title: str, error_text: str) -> List[str]:
    """Deterministically choose vba-knowledge files for this failure."""
    picks: List[str] = []
    t = (block_title or "").lower()
    for pat, files in TITLE_KNOWLEDGE_MAP:
        if re.search(pat, t, re.IGNORECASE):
            picks.extend(files)
    e = (error_text or "").lower()
    for pat, files in ERROR_KNOWLEDGE_HINTS:
        if re.search(pat, e, re.IGNORECASE):
            picks.extend(files)
    if not picks:
        # fallback: give the geometry+primitive core (most blocks are geometry)
        picks = ["geometry-primitives.md", "boolean-transform.md"]
    # de-dup, preserve order
    seen, out = set(), []
    for f in picks:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def _read_knowledge(files: List[str]) -> List[Dict]:
    kroot = _skill_root() / "building-blocks" / "vba-knowledge"
    out = []
    for f in files:
        p = kroot / f
        if p.exists():
            out.append({"file": f, "path": str(p),
                        "content": p.read_text(encoding="utf-8", errors="replace")})
        else:
            out.append({"file": f, "path": str(p), "content": None,
                        "note": "reference file missing"})
    return out


def prepare_l3_context(batch_result: Dict, blocks,
                       include_content: bool = True) -> Dict:
    """Assemble the bounded repair bundle for the main agent (step 1 of L3).

    Returns a dict the agent consumes to regenerate ONE block. Keys:
      escalate_l4 (bool), reason, failed_index, block_title, bas_path,
      bas_content, error, attempt, budget_left, knowledge (list),
      api_doc_pointers, instructions.
    """
    fi = batch_result.get("failed_index")
    if fi is None:
        return {"escalate_l4": False, "reason": "no failed block",
                "failed_index": None, "resume_index": None}
    title, bas_path = blocks[fi]
    error_text = ""
    for e in batch_result.get("executed", []):
        if e.get("status") == "error":
            error_text = e.get("error") or ""

    state = _load_state(bas_path)
    attempt = state.get("attempts", 0) + 1
    if attempt > MAX_L3_ATTEMPTS:
        return {"escalate_l4": True,
                "reason": f"L3 retry budget exhausted ({MAX_L3_ATTEMPTS} attempts)",
                "failed_index": fi, "block_title": title, "bas_path": bas_path,
                "error": error_text, "attempt": attempt,
                "budget_left": 0}

    kfiles = select_knowledge(title, error_text)
    knowledge = _read_knowledge(kfiles) if include_content else \
        [{"file": f} for f in kfiles]
    bas_content = Path(bas_path).read_text(encoding="utf-8", errors="replace") \
        if Path(bas_path).exists() else None

    return {
        "escalate_l4": False,
        "failed_index": fi,
        "block_title": title,
        "bas_path": bas_path,
        "bas_content": bas_content,
        "error": error_text,
        "attempt": attempt,
        "budget_left": MAX_L3_ATTEMPTS - attempt + 1,
        "knowledge_files": kfiles,
        "knowledge": knowledge,
        "api_doc_pointers": API_DOC_POINTERS,
        "instructions": (
            "Regenerate ONLY this one history block. Emit a RAW CST history "
            "block (no `Sub Main` wrapper -- it goes through add_to_history). "
            "Use the provided vba-knowledge as canonical form; do NOT invent "
            "API signatures -- if unsure, consult the api_doc_pointers first. "
            "Fix the exact error; change nothing else. Return just the VBA."
        ),
    }


def finalize_l3_repair(ctx: Dict, new_vba: str,
                       run_lint: bool = True) -> Dict:
    """Write the agent-regenerated block, lint it, bump the budget (step 3).

    Returns {ok, resume_index, bas_path, attempt, lint, note}. On lint ERROR the
    write still happens (so the agent can inspect) but ok=False and the caller
    should NOT resume until it's clean.
    """
    bas_path = ctx["bas_path"]
    if not new_vba or not new_vba.strip():
        return {"ok": False, "resume_index": ctx["failed_index"],
                "bas_path": bas_path, "note": "empty regenerated block"}
    # strip accidental markdown fences / Sub Main (history block must be raw)
    text = new_vba.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text).strip()
    if not text.endswith("\n"):
        text += "\n"
    Path(bas_path).write_text(text, encoding="utf-8")

    state = _load_state(bas_path)
    state["attempts"] = ctx.get("attempt", state.get("attempts", 0) + 1)
    _save_state(bas_path, state)

    lint_report = None
    ok = True
    if run_lint:
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "lint_vba", str(Path(__file__).with_name("lint_vba.py")))
            lint = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(lint)
            fixed = lint.fix_text(text, "history")
            if fixed != text:
                Path(bas_path).write_text(fixed, encoding="utf-8")
                text = fixed
            lint_report = lint.lint_text(text, "history")
            ok = lint_report.get("ok", True)
        except Exception as exc:  # noqa: BLE001
            lint_report = {"error": f"lint failed: {exc}"}

    return {"ok": ok, "resume_index": ctx["failed_index"], "bas_path": bas_path,
            "attempt": state["attempts"], "lint": lint_report,
            "note": "clean -- resume run_blocks" if ok else
                    "lint ERROR remains — do not resume; regenerate again"}


def clear_l3_state(bas_path: str) -> None:
    """Call after a successful resume to reset the budget for future runs."""
    sp = _state_path(bas_path)
    if sp.exists():
        sp.unlink()


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="L3 bounded-repair scaffold (context selection + budget).")
    ap.add_argument("--block-title", required=True)
    ap.add_argument("--bas", required=True, help="failing .bas path")
    ap.add_argument("--error-text", required=True)
    ap.add_argument("--no-content", action="store_true",
                    help="list knowledge files without inlining their content")
    args = ap.parse_args(argv)

    # simulate a batch_result for the standalone preview
    batch_result = {"failed_index": 0,
                    "executed": [{"title": args.block_title, "status": "error",
                                  "error": args.error_text}]}
    blocks = [(args.block_title, args.bas)]
    ctx = prepare_l3_context(batch_result, blocks,
                             include_content=not args.no_content)
    view = dict(ctx)
    if args.no_content:
        view.pop("bas_content", None)
    else:
        # trim big blobs for CLI readability
        view["bas_content"] = (ctx.get("bas_content") or "")[:200] or None
        view["knowledge"] = [{"file": k["file"],
                              "chars": len(k.get("content") or "")}
                             for k in ctx.get("knowledge", [])]
    print(json.dumps(view, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
