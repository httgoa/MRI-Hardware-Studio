#!/usr/bin/env python3
"""Tier-A deterministic renderer for the artifact-first pipeline (step ①).

Turns `templates/*.vba.j2` (parameterized CST VBA) into concrete `.bas`
artifacts under `results/<project>/artifacts/<step>/`, filling a parameter dict
into the Jinja2 placeholders. This is the OFFLINE generate step — it NEVER
touches CST. The flow is:

    render_templates.py   →  .bas artifacts          (step ①, this file, offline)
    lint_vba.py --fix     →  resolve ERRORs           (step ②, offline)
    batch_execute.py      →  add_to_history in CST    (step ③, in the MCP process)

Every template carries a `kind` (history | macro):
  * history  → raw CST history block (NO Sub Main); executed via add_to_history.
  * macro    → wrapped in Sub Main; executed via cst_execute_vba_tool /
               cst_schematic_execute_vba_tool (field export, schematic wiring).
The renderer records the kind in its JSON report so downstream steps route the
`.bas` correctly (lint --kind, and which MCP tool runs it).

────────────────────────────────────────────────────────────────────────────
USAGE

  # Manifest mode (primary): render a whole build in one call.
  python render_templates.py --manifest build.json

  # Single-template mode: render one template with inline params.
  python render_templates.py --project dipole_scratch --outroot results \
      --step geometry --template dipole_build --kind history \
      --set L_line=300 --set W_line=5

Manifest schema (JSON):
{
  "project": "dipole_scratch",
  "outroot": "results",                     # optional, default "results"
  "templates_dir": "...",                   # optional, default: ../templates
  "steps": [
    {"step": "setup",     "template": "common_setup",  "kind": "history",
     "out": "setup.bas",     "params": {"freq_min": "150", "freq_max": "250"}},
    {"step": "materials", "template": "materials",     "kind": "history",
     "out": "materials.bas", "params": {}},
    {"step": "geometry",  "template": "dipole_build",  "kind": "history",
     "out": "geometry.bas",  "params": {"L_line": "300"}}
    ...
  ]
}

Output path for each step: <outroot>/<project>/artifacts/<step>/<out>
(<out> defaults to <template>.bas). Prints a JSON report of rendered files.

Exit code: 0 on success, 1 if any template failed to render / was not found.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound
except ImportError:  # pragma: no cover - clear message beats a stack trace
    print(json.dumps({"error": "jinja2 not installed in this env; "
                               "`pip install jinja2` into mri_agent"}))
    sys.exit(1)


# Default kind per shipped template — history blocks vs Sub Main macros.
# Anything not listed defaults to "history"; override per-step in the manifest.
TEMPLATE_KIND = {
    "common_setup": "history",
    "materials": "history",
    "dipole_build": "history",
    "ports": "history",
    "monitors": "history",
    "solver_fd": "history",
    "solver_eigen": "history",
    # "birdcage": DEPRECATED — do NOT render as Tier A (structurally incompatible
    # with the pipeline; see the banner in templates/birdcage.vba.j2). Use Tier B
    # (prepare_tierb_gen) for birdcage geometry. Verified 2026-07-20.
    "field_export": "macro",        # Sub Main → cst_execute_vba_tool
    "schematic_match": "macro",     # Sub Main → cst_schematic_execute_vba_tool
}


def merge_globals(globals_: Dict, step_params: Dict) -> Dict:
    """Merge manifest-level `globals` into a step's params (step wins).

    This is the single-source-of-truth mechanism: frequency, units, and any
    other quantity SHARED across templates (setup ↔ monitors ↔ solver) is
    defined ONCE at the manifest top and flows into every step, so it cannot
    drift between blocks. A step may still override a value locally. Case-
    agnostic: works for any coil/frequency, not just the dipole.
    """
    merged = dict(globals_ or {})
    merged.update(step_params or {})
    return merged


def _as_float(v) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None  # symbolic like "L_line+50" — skip numeric checks


def check_frequency_consistency(steps: List[Dict]) -> List[str]:
    """Cross-step semantic check: every working frequency sits in the sweep band.

    lint_vba.py is a per-FILE structural linter (block balance, reserved names)
    — it cannot see across blocks. Unit/frequency agreement is a per-MANIFEST
    semantic property, so it is checked HERE, where the whole build is in scope.
    Catches the 1000× MHz-vs-GHz class of bug (e.g. Units=MHz but MonitorValue
    "0.21" while sweep is "150".."250"): the monitor freq falls outside the
    band → error. Unit-agnostic: only compares numbers against the same band.
    Returns a list of human-readable error strings (empty = consistent).
    """
    fmins, fmaxs, working = [], [], []  # (label, value)
    for s in steps:
        p = s.get("_merged", s.get("params", {})) or {}
        label = s.get("step", s.get("template", "?"))
        fmn, fmx = _as_float(p.get("freq_min")), _as_float(p.get("freq_max"))
        if fmn is not None:
            fmins.append((label, fmn))
        if fmx is not None:
            fmaxs.append((label, fmx))
        f0 = _as_float(p.get("f0") or p.get("target_freq"))
        if f0 is not None:
            working.append((f"{label}:f0", f0))
        for mf in p.get("monitor_frequencies", []) or []:
            v = _as_float(mf)
            if v is not None:
                working.append((f"{label}:monitor", v))

    errors: List[str] = []
    if fmins and fmaxs:
        lo = min(v for _, v in fmins)
        hi = max(v for _, v in fmaxs)
        if lo >= hi:
            errors.append(f"sweep band inverted/empty: freq_min={lo} >= freq_max={hi}")
        for label, v in working:
            if not (lo <= v <= hi):
                errors.append(
                    f"frequency {v} ({label}) is outside sweep band [{lo}, {hi}] "
                    f"-- likely a unit mismatch (MHz vs GHz?) across steps")
    return errors


def _default_templates_dir() -> Path:
    """The skill's templates/ dir, resolved relative to this script."""
    return (Path(__file__).resolve().parent.parent / "templates")


def _make_env(templates_dir: Path) -> Environment:
    # keep_trailing_newline so rendered .bas ends with one newline (matches
    # what the other artifacts look like); trim/lstrip keep {% %} lines clean.
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        undefined=StrictUndefined,     # every var in our templates has a default,
        trim_blocks=True,              # so a missing one is a real bug → error out
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def _resolve_template_name(name: str) -> str:
    """Accept 'dipole_build' or 'dipole_build.vba.j2'."""
    return name if name.endswith(".vba.j2") else f"{name}.vba.j2"


def render_one(env: Environment, template: str, params: Dict) -> str:
    tmpl = env.get_template(_resolve_template_name(template))
    text = tmpl.render(**(params or {}))
    if not text.endswith("\n"):
        text += "\n"
    return text


def _out_path(outroot: Path, project: str, step: str, out: str) -> Path:
    return outroot / project / "artifacts" / step / out


def _render_step(env: Environment, outroot: Path, project: str, step: Dict) -> Dict:
    template = step["template"]
    stepname = step.get("step", template)
    kind = step.get("kind") or TEMPLATE_KIND.get(template, "history")
    out = step.get("out") or f"{template}.bas"
    params = step.get("params", {})
    rec = {"step": stepname, "template": template, "kind": kind}
    try:
        text = render_one(env, template, params)
    except TemplateNotFound:
        rec.update({"ok": False, "error": f"template not found: {template}"})
        return rec
    except Exception as exc:  # noqa: BLE001 — surface undefined-var etc. as data
        rec.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        return rec
    dest = _out_path(outroot, project, stepname, out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    rec.update({"ok": True, "path": str(dest), "bytes": len(text.encode("utf-8"))})
    return rec


def _parse_set(pairs: Optional[List[str]]) -> Dict:
    """--set key=value (repeatable) → dict. Values stay strings (VBA is text)."""
    out: Dict[str, str] = {}
    for p in pairs or []:
        if "=" not in p:
            raise ValueError(f"--set expects key=value, got: {p!r}")
        k, v = p.split("=", 1)
        out[k.strip()] = v
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Tier-A Jinja2 renderer (offline, no CST).")
    ap.add_argument("--manifest", help="JSON manifest describing a whole build")
    ap.add_argument("--templates-dir", default=None,
                    help="templates/ dir (default: the skill's templates/)")
    # single-template mode
    ap.add_argument("--project", help="stable per-project id (single-template mode)")
    ap.add_argument("--outroot", default="results", help="results root (default: results)")
    ap.add_argument("--step", help="step folder name (single-template mode)")
    ap.add_argument("--template", help="template name, with or without .vba.j2")
    ap.add_argument("--kind", choices=["history", "macro"], default=None,
                    help="override the template's default kind")
    ap.add_argument("--out", help="output .bas filename (default: <template>.bas)")
    ap.add_argument("--set", action="append", metavar="KEY=VALUE",
                    help="a parameter (repeatable), single-template mode")
    ap.add_argument("--params-json", help="JSON dict of params, single-template mode")
    ap.add_argument("--no-freq-check", action="store_true",
                    help="skip the cross-step frequency-band consistency check")
    args = ap.parse_args(argv)

    if args.manifest:
        man = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        project = man["project"]
        outroot = Path(man.get("outroot", "results"))
        tdir = Path(man.get("templates_dir") or args.templates_dir
                    or _default_templates_dir())
        globals_ = man.get("globals", {})
        steps = man["steps"]
        # single source of truth: fold manifest globals into every step's params
        for s in steps:
            s["_merged"] = merge_globals(globals_, s.get("params", {}))
            s["params"] = s["_merged"]
    else:
        if not (args.project and args.template):
            print(json.dumps({"error": "single-template mode needs --project and --template"}))
            return 1
        project = args.project
        outroot = Path(args.outroot)
        tdir = Path(args.templates_dir or _default_templates_dir())
        params = {}
        if args.params_json:
            params.update(json.loads(args.params_json))
        params.update(_parse_set(args.set))
        steps = [{
            "step": args.step or args.template,
            "template": args.template,
            "kind": args.kind,
            "out": args.out,
            "params": params,
        }]

    if not tdir.is_dir():
        print(json.dumps({"error": f"templates dir not found: {tdir}"}))
        return 1

    # Cross-step semantic gate (unit/frequency agreement) — refuse to emit a
    # self-inconsistent build. This is the check lint_vba.py structurally can't do.
    if not args.no_freq_check:
        freq_errors = check_frequency_consistency(steps)
        if freq_errors:
            print(json.dumps({
                "error": "frequency consistency check failed (use --no-freq-check to override)",
                "details": freq_errors,
                "hint": "define units_frequency/freq_min/freq_max/monitor_frequencies "
                        "in ONE place (manifest `globals`) so they can't drift across steps",
            }, ensure_ascii=False, indent=2))
            return 1

    env = _make_env(tdir)
    reports = [_render_step(env, outroot, project, s) for s in steps]
    worst = 0 if all(r.get("ok") for r in reports) else 1
    print(json.dumps({
        "project": project,
        "outroot": str(outroot),
        "templates_dir": str(tdir),
        "rendered": reports,
    }, ensure_ascii=False, indent=2))
    return worst


if __name__ == "__main__":
    sys.exit(main())
