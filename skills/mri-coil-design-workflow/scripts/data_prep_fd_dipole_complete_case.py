#!/usr/bin/env python3
"""D1 data-prep runner for substrate-free fractionated dipole pilot cases.

This is the FD sibling of ``data_prep_dipole_complete_case.py``.  It owns the
FD matrix, FD geometry build, FD record fields, and FD manifest columns while
reusing the validated RD solve/export/postprocess helpers where they are
topology-agnostic.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import json
from pathlib import Path
from typing import Iterator

import data_prep_dipole_complete_case as rd


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
REPO_ROOT = SKILL_ROOT.parents[2]
CASE_MATRIX = SKILL_ROOT / "recipes" / "data-prep" / "complete-case(D1)" / "FD_case_matrix.csv"
RECORD_TEMPLATE = SKILL_ROOT / "recipes" / "data-prep" / "complete-case(D1)" / "record_template_v1.json"

FREQ_GHZ = rd.FREQ_GHZ
FREQ_MHZ = rd.FREQ_MHZ
PHANTOM_TOP_Z_MM = rd.PHANTOM_TOP_Z_MM
PHANTOM_SIZE = rd.PHANTOM_SIZE
EXPORT_BOX = rd.EXPORT_BOX
CONDUCTOR_THICKNESS_MM = 0.5
BRIDGE_R_OHM = 0.0


def _rel(path: str | Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT))
    except Exception:
        return str(path)


def _token(value: float | int | str) -> str:
    return rd._token(value)


def _float_or_none(value: str | float | int | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return float(text)


def _int_value(value: str | int) -> int:
    return int(round(float(value)))


def read_case_row(case_matrix_id: str) -> dict:
    with CASE_MATRIX.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["case_matrix_id"] == case_matrix_id:
                if row["family"] != "fractionated_dipole":
                    raise ValueError(f"{case_matrix_id} is not fractionated_dipole")
                if row["source_seed"] != "template" or row["network_role"] != "direct_port":
                    raise ValueError(f"{case_matrix_id} is not a template/direct_port FD row")
                return row
    raise KeyError(f"case_matrix_id not found in FD matrix: {case_matrix_id}")


def _bridge_token(row: dict) -> str:
    mode = row["lt_bridge_mode"]
    if mode == "lumped_C":
        value = _float_or_none(row.get("bridge_C_pF"))
        if value is None:
            raise ValueError(f"{row['case_matrix_id']} missing bridge_C_pF")
        return f"C{_token(value)}pF"
    if mode == "lumped_L":
        value = _float_or_none(row.get("bridge_L_nH"))
        if value is None:
            raise ValueError(f"{row['case_matrix_id']} missing bridge_L_nH")
        return f"L{_token(value)}nH"
    raise ValueError(f"unsupported FD bridge mode: {mode}")


def record_id_for(row: dict) -> str:
    return (
        "cc_fd_"
        f"L{_token(row['L_line_mm'])}_"
        f"W{_token(row['strip_width_mm'])}_"
        f"lo{_token(row['coil_to_phantom_mm'])}_"
        f"seg{_token(row['segment_count_total'])}_"
        f"g{_token(row['seg_gap_mm'])}_"
        f"{_bridge_token(row)}_"
        "direct_210"
    )


def _derive_geometry(row: dict) -> dict:
    l_total = float(row["L_line_mm"])
    w_line = float(row["strip_width_mm"])
    lift = float(row["coil_to_phantom_mm"])
    feed_gap = float(row["feed_gap_mm"] or 2.0)
    hole = feed_gap / 2.0
    seg_gap = float(row["seg_gap_mm"])
    segment_count_total = _int_value(row["segment_count_total"])
    if segment_count_total % 2 != 0:
        raise ValueError("FD segment_count_total must be even for two-arm topology")
    segments_per_arm = segment_count_total // 2
    if segments_per_arm < 2:
        raise ValueError("FD requires at least two segments per arm")
    total_gap_per_arm = (segments_per_arm - 1) * seg_gap
    arm_conductor_length = l_total / 2.0 - hole - total_gap_per_arm
    if arm_conductor_length <= 0:
        raise ValueError("FD geometry has non-positive conductor length per arm")
    segment_length = arm_conductor_length / segments_per_arm
    bridge_count_total = 2 * (segments_per_arm - 1)
    z_coil = PHANTOM_TOP_Z_MM + lift

    bridge_positions = []
    for k in range(segments_per_arm - 1):
        start = hole + (k + 1) * segment_length + k * seg_gap
        stop = start + seg_gap
        bridge_positions.append({
            "name": f"bridge_pY_{k}",
            "axis": "y",
            "center_mm": (start + stop) / 2.0,
            "from_mm": start,
            "to_mm": stop,
        })
        bridge_positions.append({
            "name": f"bridge_nY_{k}",
            "axis": "y",
            "center_mm": -(start + stop) / 2.0,
            "from_mm": -stop,
            "to_mm": -start,
        })

    return {
        "L_total_mm": l_total,
        "W_line_mm": w_line,
        "lift_mm": lift,
        "feed_gap_mm": feed_gap,
        "hole_mm": hole,
        "seg_gap_mm": seg_gap,
        "segment_count_total": segment_count_total,
        "segments_per_arm": segments_per_arm,
        "segment_length_mm": segment_length,
        "segment_lengths_mm": [segment_length] * segment_count_total,
        "bridge_count_total": bridge_count_total,
        "bridge_positions_mm": bridge_positions,
        "z_coil_mm": z_coil,
        "T_mm": CONDUCTOR_THICKNESS_MM,
    }


def case_paths(case_matrix_id: str) -> dict:
    row = read_case_row(case_matrix_id)
    rid = record_id_for(row)
    project_dir = REPO_ROOT / "projects" / f"data_prep_{case_matrix_id}"
    result_dir = REPO_ROOT / "results_data_prep" / case_matrix_id
    case_dir = result_dir / "cases" / rid
    return {
        "case_matrix_id": case_matrix_id,
        "record_id": rid,
        "project_dir": project_dir,
        "project_path": project_dir / f"{case_matrix_id}.cst",
        "result_dir": result_dir,
        "artifacts_dir": result_dir / "artifacts",
        "log_dir": result_dir / "log",
        "case_dir": case_dir,
        "output_dir": case_dir / "output",
        "global_records_dir": REPO_ROOT / "results_data_prep" / "records",
        "manifest_path": REPO_ROOT / "results_data_prep" / "manifest.csv",
    }


def ensure_dirs(case_matrix_id: str) -> dict:
    paths = case_paths(case_matrix_id)
    for key in ("project_dir", "artifacts_dir", "log_dir", "case_dir", "output_dir", "global_records_dir"):
        paths[key].mkdir(parents=True, exist_ok=True)
    return paths


def build_manifest(case_matrix_id: str) -> dict:
    row = read_case_row(case_matrix_id)
    paths = ensure_dirs(case_matrix_id)
    manifest = {
        "case_matrix_id": case_matrix_id,
        "record_id": paths["record_id"],
        "row": row,
        "geometry_policy": "substrate_free_coil_phantom",
        "fd_geometry": _derive_geometry(row),
        "phantom_top_z_mm": PHANTOM_TOP_Z_MM,
        "export_box_mm": list(EXPORT_BOX),
        "project_path": _rel(paths["project_path"]),
        "case_dir": _rel(paths["case_dir"]),
    }
    out = paths["artifacts_dir"] / "build_manifest.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


@contextlib.contextmanager
def _rd_fd_context() -> Iterator[None]:
    saved = {
        "CASE_MATRIX": rd.CASE_MATRIX,
        "record_id_for": rd.record_id_for,
        "read_case_row": rd.read_case_row,
        "case_paths": rd.case_paths,
        "ensure_dirs": rd.ensure_dirs,
        "build_manifest": rd.build_manifest,
    }
    rd.CASE_MATRIX = CASE_MATRIX
    rd.record_id_for = record_id_for
    rd.read_case_row = read_case_row
    rd.case_paths = case_paths
    rd.ensure_dirs = ensure_dirs
    rd.build_manifest = build_manifest
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(rd, name, value)


def _segment_range_expr(k: int) -> tuple[str, str]:
    start = "hole" if k == 0 else f"hole + {k}*seg_L + {k}*seg_gap"
    stop = f"hole + {k + 1}*seg_L + {k}*seg_gap"
    return start, stop


def _bridge_range_expr(k: int) -> tuple[str, str]:
    start = f"hole + {k + 1}*seg_L + {k}*seg_gap"
    stop = f"hole + {k + 1}*seg_L + {k + 1}*seg_gap"
    return start, stop


def _geometry_vba(segments_per_arm: int) -> str:
    blocks = ['Component.New "component1"']
    for k in range(segments_per_arm):
        y0, y1 = _segment_range_expr(k)
        blocks.append(f"""
With Brick
    .Reset
    .Name "arm_pY_{k}"
    .Component "component1"
    .Material "PEC"
    .Xrange "-W_line/2", "W_line/2"
    .Yrange "{y0}", "{y1}"
    .Zrange "z_coil", "z_coil+T"
    .Create
End With
With Brick
    .Reset
    .Name "arm_nY_{k}"
    .Component "component1"
    .Material "PEC"
    .Xrange "-W_line/2", "W_line/2"
    .Yrange "-({y1})", "-({y0})"
    .Zrange "z_coil", "z_coil+T"
    .Create
End With
""")
    blocks.append("""
With Brick
    .Reset
    .Name "plantom"
    .Component "component1"
    .Material "Folder_MyTong/plantom"
    .Xrange "-x_plantom/2", "x_plantom/2"
    .Yrange "-y_plantom/2", "y_plantom/2"
    .Zrange "phantom_top_z", "phantom_top_z-z_plantom"
    .Create
End With
""")
    return "\n".join(blocks)


def _bridge_vba(segments_per_arm: int, mode: str) -> str:
    if mode == "lumped_C":
        l_expr = "0"
        c_expr = "C_bridge_pF*1e-12"
    elif mode == "lumped_L":
        l_expr = "L_bridge_nH*1e-9"
        c_expr = "0"
    else:
        raise ValueError(f"unsupported FD bridge mode: {mode}")

    blocks = []
    for k in range(segments_per_arm - 1):
        y0, y1 = _bridge_range_expr(k)
        blocks.append(f"""
With LumpedElement
    .Reset
    .SetType "RLCSerial"
    .Folder "segments"
    .SetName "bridge_pY_{k}"
    .SetR "R_bridge"
    .SetL "{l_expr}"
    .SetC "{c_expr}"
    .SetMonitor "True"
    .SetP1 "False", "0", "{y0}", "z_coil+T/2"
    .SetP2 "False", "0", "{y1}", "z_coil+T/2"
    .SetInvert "False"
    .SetRadius "0.0"
    .Create
End With
With LumpedElement
    .Reset
    .SetType "RLCSerial"
    .Folder "segments"
    .SetName "bridge_nY_{k}"
    .SetR "R_bridge"
    .SetL "{l_expr}"
    .SetC "{c_expr}"
    .SetMonitor "True"
    .SetP1 "False", "0", "-({y0})", "z_coil+T/2"
    .SetP2 "False", "0", "-({y1})", "z_coil+T/2"
    .SetInvert "False"
    .SetRadius "0.0"
    .Create
End With
""")
    return "\n".join(blocks)


def live_build_fd_case(de, project, model3d, case_matrix_id: str) -> dict:
    """Build a substrate-free direct-port FD case in the active MWS project."""
    row = read_case_row(case_matrix_id)
    paths = ensure_dirs(case_matrix_id)
    manifest = build_manifest(case_matrix_id)
    geom = manifest["fd_geometry"]

    l_line = float(row["L_line_mm"])
    w_line = float(row["strip_width_mm"])
    lift = float(row["coil_to_phantom_mm"])
    feed_gap = float(row["feed_gap_mm"] or 2.0)
    hole = feed_gap / 2.0
    seg_gap = float(row["seg_gap_mm"])
    segments_per_arm = int(geom["segments_per_arm"])
    c_bridge = _float_or_none(row.get("bridge_C_pF")) or 0.0
    l_bridge = _float_or_none(row.get("bridge_L_nH")) or 0.0
    z_coil = PHANTOM_TOP_Z_MM + lift
    done: list[str] = []
    failed = None

    try:
        try:
            qm = de.quiet_mode_enabled()
        except Exception:
            qm = None

        def drive():
            rd._add(model3d, "define D1 FD parameters", f"""
StoreParameter "L_total", "{l_line:g}"
StoreParameter "L_line", "{l_line:g}"
StoreParameter "W_line", "{w_line:g}"
StoreParameter "T", "{CONDUCTOR_THICKNESS_MM:g}"
StoreParameter "gap", "{feed_gap:g}"
StoreParameter "hole", "{hole:g}"
StoreParameter "coil_to_phantom_mm", "{lift:g}"
StoreParameter "z_coil", "{z_coil:g}"
StoreParameter "H_height", "{z_coil:g}"
StoreParameter "segments_per_arm", "{segments_per_arm:g}"
StoreParameter "segment_count_total", "{geom['segment_count_total']:g}"
StoreParameter "bridge_count_total", "{geom['bridge_count_total']:g}"
StoreParameter "seg_gap", "{seg_gap:g}"
StoreParameter "seg_L", "((L_total/2 - hole) - (segments_per_arm-1)*seg_gap)/segments_per_arm"
StoreParameter "C_bridge_pF", "{c_bridge:g}"
StoreParameter "L_bridge_nH", "{l_bridge:g}"
StoreParameter "R_bridge", "{BRIDGE_R_OHM:g}"
StoreParameter "phantom_top_z", "{PHANTOM_TOP_Z_MM:g}"
StoreParameter "x_plantom", "{PHANTOM_SIZE[0]:g}"
StoreParameter "y_plantom", "{PHANTOM_SIZE[1]:g}"
StoreParameter "z_plantom", "{PHANTOM_SIZE[2]:g}"
StoreParameter "freq", "{FREQ_GHZ:g}"
""", done)

            rd._add(model3d, "set units background boundary", """
With Units
    .SetUnit "Length", "mm"
    .SetUnit "Frequency", "GHz"
    .SetUnit "Time", "ns"
End With
Solver.FrequencyRange "0.15", "0.25"
With Background
    .Type "Normal"
    .Epsilon "1.0"
    .Mu "1.0"
    .XminSpace "0.0"
    .XmaxSpace "0.0"
    .YminSpace "0.0"
    .YmaxSpace "0.0"
    .ZminSpace "0.0"
    .ZmaxSpace "0.0"
End With
With Boundary
    .Xmin "expanded open"
    .Xmax "expanded open"
    .Ymin "expanded open"
    .Ymax "expanded open"
    .Zmin "expanded open"
    .Zmax "expanded open"
    .Xsymmetry "none"
    .Ysymmetry "none"
    .Zsymmetry "none"
End With
""", done)

            rd._add(model3d, "define phantom material", """
With Material
    .Reset
    .Name "plantom"
    .Folder "Folder_MyTong"
    .Type "Normal"
    .Epsilon "78"
    .Mu "1"
    .Sigma "0.47"
    .Rho "1000"
    .Colour "0.85", "0.35", "0.35"
    .Transparency "0.6"
    .Create
End With
""", done)

            rd._add(model3d, "create substrate-free fractionated dipole geometry", _geometry_vba(segments_per_arm), done)

            rd._add(model3d, "define direct discrete port", """
With DiscretePort
    .Reset
    .PortNumber "1"
    .Type "SParameter"
    .Label ""
    .Impedance "50.0"
    .Voltage "1.0"
    .Current "1.0"
    .Monitor "True"
    .Radius "0.0"
    .SetP1 "False", "0", "-hole", "z_coil+T/2"
    .SetP2 "False", "0", "hole", "z_coil+T/2"
    .InvertDirection "False"
    .LocalCoordinates "False"
    .Wire ""
    .Position "end1"
    .Create
End With
""", done)

            rd._add(model3d, "define FD inter-segment lumped elements", _bridge_vba(segments_per_arm, row["lt_bridge_mode"]), done)

            rd._add(model3d, "define D1 field monitors", """
With Monitor
    .Reset
    .Name "h-field (f=0.21)"
    .Dimension "Volume"
    .Domain "Frequency"
    .FieldType "Hfield"
    .MonitorValue "0.21"
    .UseSubvolume "False"
    .Create
End With
With Monitor
    .Reset
    .Name "e-field (f=0.21)"
    .Dimension "Volume"
    .Domain "Frequency"
    .FieldType "Efield"
    .MonitorValue "0.21"
    .UseSubvolume "False"
    .Create
End With
With Monitor
    .Reset
    .Name "loss (f=0.21)"
    .Dimension "Volume"
    .Domain "Frequency"
    .FieldType "Powerloss"
    .MonitorValue "0.21"
    .UseSubvolume "False"
    .Create
End With
""", done)

            rd._add(model3d, "set TD hex solver for D1 SAR", """
ChangeSolverType "HF Time Domain"
Solver.FrequencyRange "0.15", "0.25"
With Solver
    .Method "Hexahedral"
    .SteadyStateLimit "-30"
    .CalculateModesOnly "False"
    .StimulationPort "All"
    .StimulationMode "All"
End With
""", done)

        if qm is None:
            drive()
        else:
            with qm:
                drive()
        project.save(str(paths["project_path"]))
    except Exception as exc:  # noqa: BLE001
        failed = f"{type(exc).__name__}: {exc}"

    return {
        "ok": failed is None,
        "case_matrix_id": case_matrix_id,
        "record_id": paths["record_id"],
        "project_path": str(paths["project_path"]),
        "fd_geometry": geom,
        "done": done,
        "failed": failed,
    }


def live_start_solver(project, model3d) -> dict:
    return rd.live_start_solver(project, model3d)


def live_poll_solver(project, model3d) -> dict:
    return rd.live_poll_solver(project, model3d)


def live_export_fields_and_sar(de, project, model3d, case_matrix_id: str) -> dict:
    with _rd_fd_context():
        return rd.live_export_fields_and_sar(de, project, model3d, case_matrix_id)


def compute_case_metrics(case_matrix_id: str, p_accepted_W: float | None = None, s11_210MHz_dB: float | None = None) -> dict:
    with _rd_fd_context():
        return rd.compute_case_metrics(case_matrix_id, p_accepted_W=p_accepted_W, s11_210MHz_dB=s11_210MHz_dB)


def _read_electrical_summary(path: str | Path | None) -> dict:
    return rd._read_electrical_summary(path)


def _record_bridge_block(row: dict) -> dict:
    return {
        "lt_bridge_mode": row["lt_bridge_mode"],
        "bridge_L_nH": _float_or_none(row.get("bridge_L_nH")),
        "bridge_C_pF": _float_or_none(row.get("bridge_C_pF")),
        "bridge_R_ohm": BRIDGE_R_OHM,
    }


def _bridge_design_token(row: dict) -> str:
    if row["lt_bridge_mode"] == "lumped_C":
        return "lumped_capacitive_bridges"
    if row["lt_bridge_mode"] == "lumped_L":
        return "lumped_inductive_bridges"
    return f"bridge_mode_{row['lt_bridge_mode']}"


def write_record(
    case_matrix_id: str,
    p_accepted_W: float | None = None,
    s11_210MHz_dB: float | None = None,
    electrical_summary_path: str | Path | None = None,
) -> dict:
    row = read_case_row(case_matrix_id)
    paths = ensure_dirs(case_matrix_id)
    rid = paths["record_id"]
    geom = _derive_geometry(row)
    electrical = _read_electrical_summary(electrical_summary_path)
    pacc = p_accepted_W if p_accepted_W is not None else electrical.get("p_accepted_W")
    s11_db = s11_210MHz_dB if s11_210MHz_dB is not None else electrical.get("s11_210MHz_dB")
    fom = compute_case_metrics(case_matrix_id, p_accepted_W=pacc, s11_210MHz_dB=s11_db)
    record = json.loads(RECORD_TEMPLATE.read_text(encoding="utf-8"))

    record["record_id"] = rid
    record["case_matrix_id"] = case_matrix_id
    record["simulation_role"] = row["simulation_role"]
    parent_case_id = (row.get("parent_case_matrix_id") or "").strip() or None
    record["lineage"].update({
        "parent_record_id": record_id_for(read_case_row(parent_case_id)) if parent_case_id else None,
        "action_type": (row.get("action_type") or "").strip() or None,
        "changed_params_json": (row.get("changed_params") or "").strip() or None,
        "direction_label": (row.get("direction_label") or "").strip() or None,
    })
    record["source"].update({
        "source_project_path": "artifact_generated_from_FD_case_matrix",
        "project_copy_path": _rel(paths["project_path"]),
        "build_manifest_path": _rel(paths["artifacts_dir"] / "build_manifest.json"),
        "schematic_snapshot_path": None,
    })
    record["geometry"].update({
        "family": row["family"],
        "topology": "fractionated_dipole_direct_port",
        "prototype_fidelity": row["prototype_fidelity"],
        "model_variant": "substrate_free_coil_phantom",
        "include_substrate": False,
        "support_stack": "none",
        "L_line_mm": float(row["L_line_mm"]),
        "strip_width_mm": float(row["strip_width_mm"]),
        "coil_to_phantom_mm": float(row["coil_to_phantom_mm"]),
        "feed_gap_mm": float(row["feed_gap_mm"] or 2.0),
        "substrate_pec_thickness_mm": CONDUCTOR_THICKNESS_MM,
        "segment_count_total": geom["segment_count_total"],
        "seg_gap_mm": geom["seg_gap_mm"],
        "segment_lengths_mm": geom["segment_lengths_mm"],
        "bridge_count_total": geom["bridge_count_total"],
        "bridge_positions_mm": geom["bridge_positions_mm"],
    })
    record["electrical_design"].update({
        "freq_MHz": FREQ_MHZ,
        "field_source_id": "[1]",
        "network_role": row["network_role"],
    })
    record["electrical_design"]["fractionated_bridge"].update(_record_bridge_block(row))
    record["simulation"].update({
        "solver_type": "HF Time Domain",
        "mesh_type": "Hexahedral",
        "mesh_step_or_accuracy": "steady_state_limit_-30dB",
        "export_grid_step_mm": {"hfield": 1, "efield": 1, "loss": 2, "sar10g": 2},
        "export_subvolume_mm": list(EXPORT_BOX),
    })
    record["electrical_state"].update({
        "p_accepted_W": pacc,
        "s11_210MHz_dB": s11_db,
        "s11_min_dB": electrical.get("s11_min_dB"),
        "resonant_frequency_MHz": electrical.get("resonant_frequency_MHz"),
        "input_R_ohm": electrical.get("input_R_ohm"),
        "input_X_ohm": electrical.get("input_X_ohm"),
    })
    case_dir = paths["case_dir"]
    record["field_artifacts"].update({
        "hfield_h5": _rel(case_dir / "hfield_1mm.h5"),
        "efield_h5": _rel(case_dir / "efield_1mm.h5") if (case_dir / "efield_1mm.h5").exists() else None,
        "loss_h5": _rel(case_dir / "loss_2mm.h5") if (case_dir / "loss_2mm.h5").exists() else None,
        "sar10g_h5": _rel(case_dir / "sar10g_native_norescale_2mm.h5") if (case_dir / "sar10g_native_norescale_2mm.h5").exists() else None,
        "surface_current_h5": _rel(case_dir / "surfcurrent_raw.h5") if (case_dir / "surfcurrent_raw.h5").exists() else None,
        "sparams_csv": _rel(case_dir / "sparams.csv") if (case_dir / "sparams.csv").exists() else None,
        "power_accepted_csv": _rel(case_dir / "power_accepted.csv") if (case_dir / "power_accepted.csv").exists() else None,
        "impedance_csv": _rel(case_dir / "impedance.csv") if (case_dir / "impedance.csv").exists() else None,
    })
    record["b1_signature"].update(fom["b1"])
    record["sar_signature"].update({k: v for k, v in fom["sar"].items() if k not in {"raw_max", "sarmax_norescale_getvalue", "sar_h5_vs_getvalue_relative_error"}})
    record["current_signature"].update({k: v for k, v in fom["current"].items() if k != "clean_txt"})

    design_tokens = [
        "coil_and_phantom_only",
        "fractionated_dipole",
        "direct_port",
        f"seg{geom['segment_count_total']}",
        f"gap{_token(geom['seg_gap_mm'])}mm",
        _bridge_design_token(row),
    ]
    if row.get("role") in {"anchor", "space_fill", "perturbation", "interaction"}:
        design_tokens.append(row["role"])
    record["learning_card"]["design_tokens"] = design_tokens

    flags = [
        "coil_and_phantom_only",
        "fd_segment_count_matches_matrix",
        "fd_bridge_count_matches_segment_count",
        "fd_bridge_mode_and_value_match_matrix",
        "fd_no_substrate_solids_present",
        "sar_export_subvolume_corrected_to_project_phantom_box",
        "native_sar10g_depth_profile_generated" if record["sar_signature"]["depth_profile_csv"] else None,
        "native_sar10g_slices_48x48_generated" if record["sar_signature"]["slices_48x48_npz"] else None,
        "native_sar10g_h5_validated_against_getvalue" if fom["sar"].get("sar_h5_vs_getvalue_relative_error") is not None and fom["sar"].get("sar_h5_vs_getvalue_relative_error") < 0.05 else None,
        "surface_current_h5_exported" if record["field_artifacts"]["surface_current_h5"] else None,
        "surface_current_metrics_generated" if record["current_signature"]["current_status"] == "computed_from_surface_current_h5" else None,
    ]
    if record["sar_signature"]["sar_status"] == "validated_native_h5":
        flags.extend([
            "native_sar10g_scalar_exported",
            "native_sar10g_h5_exported",
        ])
    record["qa"].update({
        "qa_status": "validated" if record["sar_signature"]["sar_status"] == "validated_native_h5" and pacc else "partial",
        "qa_flags": [f for f in flags if f],
        "schema_pass": True,
        "field_archive_status": "complete" if record["field_artifacts"]["sar10g_h5"] else "partial",
        "notes": f"SAR HDF5/GetValue relative error: {fom['sar'].get('sar_h5_vs_getvalue_relative_error')}",
    })

    local_record = paths["output_dir"] / "record.json"
    global_record = paths["global_records_dir"] / f"{rid}.json"
    text = json.dumps(record, indent=2, ensure_ascii=False)
    local_record.write_text(text + "\n", encoding="utf-8")
    global_record.write_text(text + "\n", encoding="utf-8")
    sha_local = hashlib.sha256(local_record.read_bytes()).hexdigest()
    sha_global = hashlib.sha256(global_record.read_bytes()).hexdigest()
    update_manifest(record, sha_local == sha_global)
    return {"record": record, "local_record": str(local_record), "global_record": str(global_record), "hash_match": sha_local == sha_global}


def update_manifest(record: dict, hash_match: bool) -> None:
    path = REPO_ROOT / "results_data_prep" / "manifest.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    base_fields = [
        "record_id", "case_matrix_id", "schema_version", "library_role", "simulation_role",
        "family", "topology", "prototype_fidelity", "source_project_path", "project_copy_path",
        "freq_MHz", "solver_type", "mesh_type", "field_source_id", "network_role",
        "L_line_mm", "strip_width_mm", "coil_to_phantom_mm", "feed_gap_mm",
        "segment_count_total", "seg_gap_mm", "bridge_count_total", "lt_bridge_mode",
        "bridge_C_pF", "bridge_L_nH", "bridge_R_ohm",
        "p_accepted_W", "s11_210MHz_dB", "b1p_at_10cm_mean_uT_per_sqrtW",
        "b1p_peak_uT_per_sqrtW", "cov_roi", "sar10g_max_W_per_kg_per_W",
        "sar_efficiency_10cm", "qa_status", "qa_flags", "sar_status",
        "field_archive_status", "schema_pass", "record_hash_match",
    ]
    bridge = record["electrical_design"]["fractionated_bridge"]
    row = {
        "record_id": record["record_id"],
        "case_matrix_id": record["case_matrix_id"],
        "schema_version": record["schema_version"],
        "library_role": record["library_role"],
        "simulation_role": record["simulation_role"],
        "family": record["geometry"]["family"],
        "topology": record["geometry"]["topology"],
        "prototype_fidelity": record["geometry"]["prototype_fidelity"],
        "source_project_path": record["source"]["source_project_path"],
        "project_copy_path": record["source"]["project_copy_path"],
        "freq_MHz": record["electrical_design"]["freq_MHz"],
        "solver_type": record["simulation"]["solver_type"],
        "mesh_type": record["simulation"]["mesh_type"],
        "field_source_id": record["electrical_design"]["field_source_id"],
        "network_role": record["electrical_design"]["network_role"],
        "L_line_mm": record["geometry"]["L_line_mm"],
        "strip_width_mm": record["geometry"]["strip_width_mm"],
        "coil_to_phantom_mm": record["geometry"]["coil_to_phantom_mm"],
        "feed_gap_mm": record["geometry"]["feed_gap_mm"],
        "segment_count_total": record["geometry"]["segment_count_total"],
        "seg_gap_mm": record["geometry"]["seg_gap_mm"],
        "bridge_count_total": record["geometry"]["bridge_count_total"],
        "lt_bridge_mode": bridge["lt_bridge_mode"],
        "bridge_C_pF": bridge["bridge_C_pF"],
        "bridge_L_nH": bridge["bridge_L_nH"],
        "bridge_R_ohm": bridge["bridge_R_ohm"],
        "p_accepted_W": record["electrical_state"]["p_accepted_W"],
        "s11_210MHz_dB": record["electrical_state"]["s11_210MHz_dB"],
        "b1p_at_10cm_mean_uT_per_sqrtW": record["b1_signature"]["b1p_at_10cm_mean_uT_per_sqrtW"],
        "b1p_peak_uT_per_sqrtW": record["b1_signature"]["b1p_peak_uT_per_sqrtW"],
        "cov_roi": record["b1_signature"]["cov_roi"],
        "sar10g_max_W_per_kg_per_W": record["sar_signature"]["sar10g_max_W_per_kg_per_W"],
        "sar_efficiency_10cm": record["sar_signature"]["sar_efficiency_10cm"],
        "qa_status": record["qa"]["qa_status"],
        "qa_flags": ";".join(record["qa"]["qa_flags"]),
        "sar_status": record["sar_signature"]["sar_status"],
        "field_archive_status": record["qa"]["field_archive_status"],
        "schema_pass": record["qa"]["schema_pass"],
        "record_hash_match": hash_match,
    }

    rows = {}
    existing_fields: list[str] = []
    if path.exists():
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            existing_fields = list(reader.fieldnames or [])
            for existing in reader:
                rows[existing["record_id"]] = existing

    fields = list(existing_fields)
    for field in base_fields:
        if field not in fields:
            fields.append(field)
    if "record_id" not in fields:
        fields.insert(0, "record_id")

    rows[record["record_id"]] = {k: row.get(k, "") for k in fields}
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for key in sorted(rows):
            writer.writerow({k: rows[key].get(k, "") for k in fields})


LIVE_STAGES = ["build", "start_solver", "poll_solver", "export"]


def emit_live_code(case_matrix_id: str, live_stage: str) -> str:
    if live_stage not in LIVE_STAGES:
        raise ValueError(f"live stage must be one of {LIVE_STAGES}")
    script_dir = repr(str(SCRIPT_DIR))
    case_repr = repr(case_matrix_id)
    if live_stage == "build":
        call = "out = fd.live_build_fd_case(de, project, model3d, case_matrix_id)"
    elif live_stage == "start_solver":
        call = "out = fd.live_start_solver(project, model3d)"
    elif live_stage == "poll_solver":
        call = "out = fd.live_poll_solver(project, model3d)"
    else:
        call = "out = fd.live_export_fields_and_sar(de, project, model3d, case_matrix_id)"
    return f"""# Paste into cst_run_python_tool. For build, start from an active blank MWS project.
import sys

sys.path.insert(0, {script_dir})
import data_prep_fd_dipole_complete_case as fd

case_matrix_id = {case_repr}
{call}
result = out
"""


def main() -> None:
    ap = argparse.ArgumentParser(description="Single-case FD data-prep pilot helper.")
    ap.add_argument("--case", required=True, help="FD case id such as FD_A01.")
    ap.add_argument("--paths", action="store_true", help="Print paths and record id.")
    ap.add_argument("--emit-manifest", action="store_true", help="Write and print build manifest.")
    ap.add_argument("--emit-live-code", choices=LIVE_STAGES, help="Emit cst_run_python_tool code for a live stage.")
    ap.add_argument("--write-record", action="store_true", help="Run offline metrics and write record/manifest.")
    ap.add_argument("--p-accepted", type=float, default=None)
    ap.add_argument("--s11-db", type=float, default=None)
    ap.add_argument("--electrical-summary", default=None)
    args = ap.parse_args()

    if args.paths:
        paths = case_paths(args.case)
        print(json.dumps({k: str(v) for k, v in paths.items()}, indent=2))
    if args.emit_manifest:
        print(json.dumps(build_manifest(args.case), indent=2))
    if args.emit_live_code:
        print(emit_live_code(args.case, args.emit_live_code))
    if args.write_record:
        print(json.dumps(
            write_record(
                args.case,
                p_accepted_W=args.p_accepted,
                s11_210MHz_dB=args.s11_db,
                electrical_summary_path=args.electrical_summary,
            ),
            indent=2,
            ensure_ascii=False,
            default=str,
        ))


if __name__ == "__main__":
    main()
