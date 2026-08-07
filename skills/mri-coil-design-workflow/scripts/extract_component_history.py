#!/usr/bin/env python3
"""Extract CST Component Library ModelHistory.json into replay artifacts.

The output follows the artifact-first layout used by this skill:

    results/<project_id>/artifacts/<step>/<NN>_<caption>.bas
    results/<project_id>/artifacts/blocks.json
    results/<project_id>/artifacts/blocks_safe.json
    results/<project_id>/log/source_inventory.md
    results/<project_id>/log/history_digest.md

`blocks.json` contains every official history block. `blocks_safe.json` is a
first-pass replay manifest that skips full solver/mesh dump blocks likely to
contain version-specific setters. A generated minimal solver block is added when
the source metadata contains enough information.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SKIP_SAFE_RE = re.compile(
    r"(for backward compatibility|special time domain solver|"
    r"define frequency domain solver parameters|set 3d mesh adaptation|"
    r"set mesh properties|set pba mesh type|set surface mesh type|"
    r"Activate default mesh|farfield plot options)",
    re.IGNORECASE,
)


def slugify(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "_", text.strip().lower())
    return re.sub(r"_+", "_", text).strip("_") or "block"


def classify(caption: str) -> str:
    c = caption.lower()
    if "template" in c or "background" in c or "boundar" in c or "frequency range" in c or "units" in c:
        return "setup"
    if "material" in c or "layer" in c:
        return "materials"
    if "port" in c:
        return "ports"
    if "monitor" in c or "farfield" in c:
        return "monitors"
    if "mesh" in c:
        return "mesh"
    if "solver" in c or "pba" in c:
        return "solver"
    if (
        "cylinder" in c
        or "brick" in c
        or "pick" in c
        or "boolean" in c
        or "transform" in c
        or "workplane" in c
        or "coordinates" in c
        or "wcs" in c
        or "shape" in c
        or "delete" in c
        or "move" in c
        or "snap" in c
    ):
        return "geometry"
    return "misc"


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def param_rows(params: Dict[str, Any]) -> List[Dict[str, str]]:
    rows = params.get("parameters") or []
    out: List[Dict[str, str]] = []
    for row in rows:
        out.append(
            {
                "name": str(row.get("name", "")),
                "expr": str(row.get("expr", row.get("value", ""))),
                "value": str(row.get("value", "")),
            }
        )
    return out


def parameter_block(params: Dict[str, Any]) -> Optional[str]:
    rows = param_rows(params)
    if not rows:
        return None
    lines = ["' Parameters extracted from Model/Parameters.json"]
    for row in rows:
        name = row["name"].strip()
        expr = (row["expr"] or row["value"]).strip()
        if not name or not expr:
            continue
        # StoreParameter keeps expressions editable in CST and prevents modal
        # "New Parameter" prompts when later history uses e.g. k*h.
        lines.append(f'StoreParameter "{name}", "{expr}"')
    if len(lines) == 1:
        return None
    return "\n".join(lines) + "\n"


def active_solver(simprops: Dict[str, Any]) -> str:
    run_options = simprops.get("run_options") or {}
    single = run_options.get("single_solver_run") or {}
    return str(single.get("active_solver", "")).strip()


def frequency(simprops: Dict[str, Any], history: Dict[str, Any]) -> Dict[str, str]:
    src = simprops.get("frequency") or (history.get("general") or {}).get("frequency") or {}
    return {
        "minimum": str(src.get("minimum_expr", src.get("minimum", ""))),
        "maximum": str(src.get("maximum_expr", src.get("maximum", ""))),
        "unit": str(src.get("unit", "")),
    }


def first_regex(codes: Iterable[str], pattern: str) -> Optional[str]:
    rx = re.compile(pattern, re.IGNORECASE)
    for text in codes:
        m = rx.search(text)
        if m:
            return m.group(1)
    return None


def minimal_solver_block(
    solver: str, freq: Dict[str, str], all_code: Iterable[str], port_count: int
) -> Optional[str]:
    fmin, fmax = freq.get("minimum", ""), freq.get("maximum", "")
    if not fmin or not fmax:
        return None

    code_joined = "\n".join(all_code)
    steady = first_regex([code_joined], r'\.SteadyStateLimit\s+"([^"]+)"') or "-40"
    stim = "All" if port_count != 1 else (first_regex([code_joined], r'\.StimulationPort\s+"([^"]+)"') or "All")

    if "time domain" in solver.lower():
        return "\n".join(
            [
                'ChangeSolverType "HF Time Domain"',
                f'Solver.FrequencyRange "{fmin}", "{fmax}"',
                "With Mesh",
                '    .MeshType "PBA"',
                '    .SetCreator "High Frequency"',
                "End With",
                "With Solver",
                '    .Method "Hexahedral"',
                '    .CalculationType "TD-S"',
                f'    .StimulationPort "{stim}"',
                f'    .StimulationMode "{stim}"',
                f'    .SteadyStateLimit "{steady}"',
                '    .CalculateModesOnly "False"',
                "End With",
                "",
            ]
        )

    if "multilayer" in solver.lower():
        return "\n".join(
            [
                'ChangeSolverType "HF Multilayer"',
                f'Solver.FrequencyRange "{fmin}", "{fmax}"',
                'Mesh.MeshType "SurfaceML"',
                'SetSolverType "HF_MULTILAYER"',
                "",
            ]
        )

    if "frequency domain" in solver.lower():
        return "\n".join(
            [
                'ChangeSolverType "HF Frequency Domain"',
                f'Solver.FrequencyRange "{fmin}", "{fmax}"',
                "With FDSolver",
                "    .Reset",
                '    .SetMethod "Tetrahedral", "General purpose"',
                '    .OrderTet "Second"',
                '    .Stimulation "All", "All"',
                '    .AccuracyTet "1e-4"',
                '    .MeshAdaptionTet "True"',
                "End With",
                "",
            ]
        )

    return None


def write_table(rows: List[List[str]]) -> str:
    if not rows:
        return ""
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    lines = []
    for idx, row in enumerate(rows):
        lines.append("| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(row))) + " |")
        if idx == 0:
            lines.append("| " + " | ".join("-" * widths[i] for i in range(len(row))) + " |")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", required=True, help="Official case folder without the .cst suffix")
    ap.add_argument("--project-id", required=True)
    ap.add_argument("--outroot", default="results")
    args = ap.parse_args()

    source_dir = Path(args.source_dir)
    history_path = source_dir / "Model" / "3D" / "ModelHistory.json"
    params_path = source_dir / "Model" / "Parameters.json"
    simprops_path = source_dir / "Model" / "simulationproperties.json"
    if not history_path.exists():
        raise SystemExit(f"missing ModelHistory.json: {history_path}")

    history = read_json(history_path)
    params = read_json(params_path)
    simprops = read_json(simprops_path)
    entries = history.get("history") or []

    project_root = Path(args.outroot) / args.project_id
    artifacts = project_root / "artifacts"
    log_dir = project_root / "log"
    artifacts.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    blocks: List[Dict[str, Any]] = []
    all_code_texts: List[str] = []
    port_count = 0

    pblock = parameter_block(params)
    if pblock:
        param_dir = artifacts / "parameters"
        param_dir.mkdir(parents=True, exist_ok=True)
        param_path = param_dir / "000_define_parameters.bas"
        param_path.write_text(pblock, encoding="utf-8")
        blocks.append(
            {
                "index": 0,
                "title": "000 define parameters",
                "caption": "define parameters",
                "step": "parameters",
                "path": str(param_path),
                "risky_solver_or_mesh_dump": False,
                "include_in_safe_replay": True,
                "source_version": "Parameters.json",
            }
        )

    for idx, entry in enumerate(entries, start=1):
        caption = str(entry.get("caption", f"block {idx:03d}"))
        code_lines = entry.get("code") or []
        code = "\n".join(str(line) for line in code_lines).rstrip() + "\n"
        all_code_texts.append(code)
        if "define port" in caption.lower():
            port_count += 1

        step = classify(caption)
        step_dir = artifacts / step
        step_dir.mkdir(parents=True, exist_ok=True)
        bas_path = step_dir / f"{idx:03d}_{slugify(caption)}.bas"
        bas_path.write_text(code, encoding="utf-8")
        risky = bool(SKIP_SAFE_RE.search(caption))
        include_safe = not risky
        blocks.append(
            {
                "index": idx,
                "title": f"{idx:03d} {caption}",
                "caption": caption,
                "step": step,
                "path": str(bas_path),
                "risky_solver_or_mesh_dump": risky,
                "include_in_safe_replay": include_safe,
                "source_version": entry.get("version", ""),
            }
        )

    solver = active_solver(simprops)
    freq = frequency(simprops, history)
    solver_code = minimal_solver_block(solver, freq, all_code_texts, port_count)
    if solver_code:
        solver_dir = artifacts / "solver"
        solver_dir.mkdir(exist_ok=True)
        solver_path = solver_dir / "999_generated_minimal_solver.bas"
        solver_path.write_text(solver_code, encoding="utf-8")
        blocks.append(
            {
                "index": 999,
                "title": "999 generated minimal solver",
                "caption": "generated minimal solver",
                "step": "solver",
                "path": str(solver_path),
                "risky_solver_or_mesh_dump": False,
                "include_in_safe_replay": True,
                "source_version": "generated",
            }
        )

    safe_blocks = [b for b in blocks if b.get("include_in_safe_replay")]
    (artifacts / "blocks.json").write_text(json.dumps(blocks, indent=2), encoding="utf-8")
    (artifacts / "blocks_safe.json").write_text(json.dumps(safe_blocks, indent=2), encoding="utf-8")

    general = history.get("general") or {}
    rows = [["idx", "step", "safe", "caption"]]
    for b in blocks:
        rows.append(
            [
                str(b["index"]),
                str(b["step"]),
                "yes" if b.get("include_in_safe_replay") else "no",
                str(b["caption"]),
            ]
        )

    param_lines = ["| name | expr | value |", "|---|---|---|"]
    for p in param_rows(params):
        param_lines.append(f"| {p['name']} | {p['expr']} | {p['value']} |")
    if len(param_lines) == 2:
        param_lines.append("| n/a | n/a | n/a |")

    inventory = "\n".join(
        [
            f"# Source inventory: {args.project_id}",
            "",
            f"- source_dir: `{source_dir}`",
            f"- history: `{history_path}`",
            f"- cst_version: `{general.get('version', '')}`",
            f"- project_type: `{general.get('project_type', '')}`",
            f"- units: length `{general.get('length', '')}`, frequency `{freq.get('unit', '')}`",
            f"- frequency_range: `{freq.get('minimum', '')}` to `{freq.get('maximum', '')}`",
            f"- active_solver: `{solver}`",
            f"- history_blocks: `{len(entries)}`",
            f"- safe_replay_blocks: `{len(safe_blocks)}`",
            "",
            "## Parameters",
            "",
            "\n".join(param_lines),
            "",
            "## History Captions",
            "",
            write_table(rows),
            "",
        ]
    )
    (log_dir / "source_inventory.md").write_text(inventory, encoding="utf-8")
    (log_dir / "history_digest.md").write_text(write_table(rows) + "\n", encoding="utf-8")
    (log_dir / "state.md").write_text(
        "\n".join(
            [
                f"# State: {args.project_id}",
                "",
                "- source inventory: done",
                "- history extraction: done",
                "- L0 lint: pending",
                "- CST safe replay: pending",
                "- solve: pending",
                "- note distillation: pending",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "project_id": args.project_id,
                "source_dir": str(source_dir),
                "history_blocks": len(entries),
                "safe_replay_blocks": len(safe_blocks),
                "artifacts": str(artifacts),
                "inventory": str(log_dir / "source_inventory.md"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
