#!/usr/bin/env python3
r"""Tier-B few-shot generation scaffold for the artifact-first pipeline.

Tier B is the middle generation tier: when a modeling step is a NOVEL topology
that no `templates/*.vba.j2` (Tier A) covers, it is produced by ONE few-shot LLM
call seeded with the relevant `vba-knowledge/*.md` reference blocks — the model
picks canonical CST VBA and fills in parameters, it does NOT invent API.

Until now Tier B was only PROSE in artifact-pipeline.md — there was no code for
"which references to feed, how to bundle the spec, where the .bas lands, how it
rejoins lint→batch". This scaffold makes the DETERMINISTIC parts real, leaving
ONLY the single generation call to the LLM (the main agent). It is the twin of
`prepare_l3_repair.py` (L3 repair) — same shape, but PROACTIVE generation of a
new step instead of REACTIVE repair of a failed one.

Flow (inside the recipe, for a step Tier A can't express):
  exec(open(r"...\prepare_tierb_gen.py", encoding="utf-8").read())
  ctx = prepare_tierb_context(
      project="birdcage_hp", step="geometry", topology="birdcage",
      spec={"radius_mm": 130, "length_mm": 200, "num_rungs": 16, ...},
      outroot="results")
  # ↓ the ONLY LLM step: the agent writes a RAW history block for `ctx["spec"]`
  #   using ctx["knowledge"] as canonical form, obeying ctx["constraints"]
  generated_vba = <agent output>
  fin = finalize_tierb_block(ctx, generated_vba)   # strip fences/Sub Main + lint + write
  # fin["bas_path"] now sits in artifacts/<step>/ alongside Tier-A blocks;
  # add it to BLOCKS and run the normal lint→batch_execute→L2/L3 path.

Design parity with the rest of the pipeline:
- A .bas produced here is a RAW history block (no Sub Main) unless kind=macro.
- It lands in results/<project>/artifacts/<step>/<name>.bas — identical layout
  to Tier A — so batch_execute + L0/L2/L3 treat A and B output the same.
- Generation is bounded to ONE call per step; if the block fails at execute
  time it goes through the SAME L2→L3 ladder as any block (no special path).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional


def _skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


# Deterministic reference selection. A Tier-B step declares a `step` category and
# optionally a `topology`; both route to canonical vba-knowledge files. Union of
# matches, order-preserved. Mirrors prepare_l3_repair's routing intent but keyed
# on the GENERATION request (step/topology), not on an error.
STEP_KNOWLEDGE_MAP = {
    "setup": ["mri-setup.md"],
    "materials": ["mri-setup.md"],
    "geometry": ["geometry-primitives.md", "boolean-transform.md"],
    "ports": ["ports-monitors-mesh.md"],
    "monitors": ["ports-monitors-mesh.md"],
    "mesh": ["ports-monitors-mesh.md"],
    "solver": ["solvers.md"],
    "schematic": ["schematic-match.md"],
    "export": ["field-export.md"],
}

# Topology adds the composition-pattern reference on top of the step files.
TOPOLOGY_KNOWLEDGE = {
    "birdcage": ["coil-geometry.md", "geometry-primitives.md", "boolean-transform.md"],
    "surface_loop": ["coil-geometry.md", "geometry-primitives.md"],
    "loop": ["coil-geometry.md", "geometry-primitives.md"],
    "saddle": ["coil-geometry.md", "geometry-primitives.md"],
    "phased_array": ["coil-geometry.md", "boolean-transform.md"],
    "array": ["coil-geometry.md", "boolean-transform.md"],
    "dipole": ["geometry-primitives.md", "boolean-transform.md"],
    "circular_patch": ["geometry-primitives.md", "boolean-transform.md"],
    "circular_resonator": ["geometry-primitives.md", "boolean-transform.md"],
}

# DECISION knowledge from notes/ (distilled official manuals + case
# logs). These are NOT canonical-VBA snippet libraries like vba-knowledge/ — they
# carry the "which solver / boundary / port / topology approach to pick" reasoning
# that a NEW coil needs. Routed by step (and topology) so a Tier-B generation for
# a solver/geometry step actually SEES the decision table instead of guessing.
STEP_NOTES_MAP = {
    "setup": ["cst-hf-fundamentals.md"],       # boundary/units/frequency rules
    "solver": ["cst-hf-fundamentals.md"],      # §2 solver-selection table + §3 mesh
    "geometry": ["cst-hf-fundamentals.md"],    # §4 port + §5 antenna/coil build notes
    "ports": ["cst-hf-fundamentals.md"],       # §4 port-type selection
    "schematic": ["cst-circuit-sam.md"],       # EM/circuit co-sim mental model
}
# Topology → the per-case reproduction log that already built something similar
# (verified VBA + the exact traps hit). Read before building the same family.
TOPOLOGY_NOTES = {
    "birdcage": ["repro-03-mri-coil.md"],          # body coil: LumpedFaceElement pick-edge, rotating B1
    "surface_loop": ["repro-05-single-coil.md"],
    "loop": ["repro-05-single-coil.md"],
    "phased_array": ["repro-02-dipole-array.md"],
    "array": ["repro-02-dipole-array.md"],
    "dipole": ["repro-01-dipole-antenna.md", "repro-06-fractionated-dipole.md"],
    "circular_patch": ["repro-07-circular-patch-td.md", "repro-09-circular-patch-multilayer.md"],
    "circular_resonator": ["repro-08-circular-resonator.md"],
}

API_DOC_POINTERS = [
    r"external/CST-MCP/vendor/cst-runtime-cli/devkit/references/vba-official-reference.md",
    r"external/CST-MCP/vendor/cst-runtime-cli/devkit/references/cst-official-api-reference.md",
    r"CST Online Help: D:\ght\softwares\MRI_agent_softwares\Online Help\mergedProjects\**\*.htm",
]

# Constraints every generated block MUST obey — these encode the pitfalls we've
# already paid for, so Tier-B output doesn't re-introduce them (they mirror what
# L0 lint + L2 fixes enforce, stated up-front so the FIRST generation is clean).
DEFAULT_CONSTRAINTS = [
    "Emit a RAW CST history block (NO `Sub Main`) unless kind=macro; it goes through add_to_history.",
    "One statement per line for schematic VBA (no ':' multi-statement — the MCP VBA parser rejects it).",
    "Frequency/units come from the manifest globals; do NOT hardcode a unit that disagrees with them "
    "(MHz vs GHz mismatch is a silent 1000x bug).",
    "Boundary values are API tokens ('expanded open', 'electric', ...), NOT GUI labels ('open (add space)').",
    "Solver blocks: only setters this CST version exposes — do NOT paste a full With FDSolver from a .mod "
    "(SweepTolerance/SweepErrorChecks/... raise 'no such property or method').",
    "DiscretePort/LumpedElement free coords: SetP1/SetP2 first arg 'False' (NOT 'True', which needs a picked point).",
    "Array N copies with ONE Transform (MultipleObjects True + Repetitions), never model N copies by hand.",
    "Do NOT invent API signatures — if a call is not in the provided vba-knowledge, consult api_doc_pointers.",
    "Parameter names must not be VBA/Python keywords (e.g. 'lambda' -> 'lambda0').",
]


def _dedup(seq: List[str]) -> List[str]:
    seen, out = set(), []
    for f in seq:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def select_knowledge(step: str, topology: Optional[str]) -> List[str]:
    """Canonical-VBA snippet files (vba-knowledge/) for this step/topology."""
    picks: List[str] = []
    picks.extend(STEP_KNOWLEDGE_MAP.get((step or "").lower(), []))
    if topology:
        picks.extend(TOPOLOGY_KNOWLEDGE.get(topology.lower(), []))
    if not picks:
        picks = ["geometry-primitives.md", "boolean-transform.md"]
    return _dedup(picks)


def select_notes(step: str, topology: Optional[str]) -> List[str]:
    """Decision knowledge (notes/) for this step/topology — the
    solver/boundary/port selection tables + matching per-case reproduction log."""
    picks: List[str] = []
    picks.extend(STEP_NOTES_MAP.get((step or "").lower(), []))
    if topology:
        picks.extend(TOPOLOGY_NOTES.get(topology.lower(), []))
    return _dedup(picks)


def _read_from(subdir: str, files: List[str]) -> List[Dict]:
    if subdir == "vba-knowledge":
        root = _skill_root() / "building-blocks" / "vba-knowledge"
    elif subdir == "notes":
        root = _skill_root() / "notes"
    else:
        root = _skill_root() / subdir
    out = []
    for f in files:
        p = root / f
        if p.exists():
            out.append({"file": f, "path": str(p),
                        "content": p.read_text(encoding="utf-8", errors="replace")})
        else:
            out.append({"file": f, "path": str(p), "content": None,
                        "note": "reference file missing"})
    return out


def _read_knowledge(files: List[str]) -> List[Dict]:
    return _read_from("vba-knowledge", files)


def _read_notes(files: List[str]) -> List[Dict]:
    return _read_from("notes", files)


def _bas_path(outroot: str, project: str, step: str, out: str) -> Path:
    return Path(outroot) / project / "artifacts" / step / out


def prepare_tierb_context(project: str, step: str, spec, topology: Optional[str] = None,
                          outroot: str = "results", out: Optional[str] = None,
                          kind: str = "history", globals_: Optional[Dict] = None,
                          include_content: bool = True) -> Dict:
    """Assemble the few-shot bundle for the ONE generation call (step 1).

    spec: the design description (a dict of dimensions/params, or a text string)
          — WHAT to build. topology: optional coil family for extra references.
    Returns the context the agent consumes; `bas_path` is where finalize writes.
    """
    kfiles = select_knowledge(step, topology)
    knowledge = _read_knowledge(kfiles) if include_content else \
        [{"file": f} for f in kfiles]
    nfiles = select_notes(step, topology)
    notes = _read_notes(nfiles) if include_content else [{"file": f} for f in nfiles]
    out_name = out or f"{step}.bas"
    bas_path = _bas_path(outroot, project, step, out_name)
    return {
        "project": project,
        "step": step,
        "topology": topology,
        "kind": kind,
        "spec": spec,
        "globals": globals_ or {},
        "bas_path": str(bas_path),
        "knowledge_files": kfiles,
        "knowledge": knowledge,
        "decision_notes_files": nfiles,
        "decision_notes": notes,
        "api_doc_pointers": API_DOC_POINTERS,
        "constraints": DEFAULT_CONSTRAINTS,
        "instructions": (
            f"Generate the CST VBA for step '{step}'"
            + (f" (topology: {topology})" if topology else "")
            + ". Use the provided `knowledge` (vba-knowledge canonical snippets) as "
            "the VBA form and fill in the spec's parameters. Consult `decision_notes` "
            "for solver/boundary/port choices and topology-specific traps. "
            "Obey every item in `constraints`. "
            "Return ONLY the VBA for this one step — no prose, no code fences."
        ),
    }


def finalize_tierb_block(ctx: Dict, generated_vba: str, run_lint: bool = True) -> Dict:
    """Write the generated block, strip fences/Sub Main, lint it (step 3).

    Returns {ok, bas_path, kind, lint, note}. On lint ERROR the file is still
    written (so it can be inspected/regenerated) but ok=False.
    """
    bas_path = ctx["bas_path"]
    if not generated_vba or not generated_vba.strip():
        return {"ok": False, "bas_path": bas_path, "note": "empty generated block"}
    text = generated_vba.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text).strip()
    if not text.endswith("\n"):
        text += "\n"
    Path(bas_path).parent.mkdir(parents=True, exist_ok=True)
    Path(bas_path).write_text(text, encoding="utf-8")

    lint_report = None
    ok = True
    if run_lint:
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "lint_vba", str(Path(__file__).with_name("lint_vba.py")))
            lint = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(lint)
            kind = ctx.get("kind", "history")
            fixed = lint.fix_text(text, kind)
            if fixed != text:
                Path(bas_path).write_text(fixed, encoding="utf-8")
                text = fixed
            lint_report = lint.lint_text(text, kind)
            ok = lint_report.get("ok", True)
        except Exception as exc:  # noqa: BLE001
            lint_report = {"error": f"lint failed: {exc}"}

    return {"ok": ok, "bas_path": bas_path, "kind": ctx.get("kind", "history"),
            "lint": lint_report,
            "note": "clean -- add to BLOCKS and batch_execute" if ok else
                    "lint ERROR -- regenerate before executing"}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Tier-B few-shot generation scaffold (context selection).")
    ap.add_argument("--project", required=True)
    ap.add_argument("--step", required=True)
    ap.add_argument("--topology", default=None)
    ap.add_argument("--spec", default="{}", help="JSON spec dict or text")
    ap.add_argument("--outroot", default="results")
    ap.add_argument("--out", default=None)
    ap.add_argument("--kind", choices=["history", "macro"], default="history")
    ap.add_argument("--no-content", action="store_true",
                    help="list knowledge files without inlining their content")
    args = ap.parse_args(argv)

    try:
        spec = json.loads(args.spec)
    except json.JSONDecodeError:
        spec = args.spec  # allow free-text spec
    ctx = prepare_tierb_context(
        project=args.project, step=args.step, spec=spec, topology=args.topology,
        outroot=args.outroot, out=args.out, kind=args.kind,
        include_content=not args.no_content)
    view = dict(ctx)
    if not args.no_content:
        view["knowledge"] = [{"file": k["file"], "chars": len(k.get("content") or "")}
                             for k in ctx.get("knowledge", [])]
        view["decision_notes"] = [{"file": k["file"], "chars": len(k.get("content") or "")}
                                  for k in ctx.get("decision_notes", [])]
    print(json.dumps(view, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
