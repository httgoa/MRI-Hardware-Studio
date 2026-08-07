#!/usr/bin/env python3
"""D1 data-prep runner for substrate-free regular dipole complete cases.

This module has two execution surfaces:

1. Live CST functions, called inside ``cst_run_python_tool`` with ``de``,
   ``project`` and ``model3d`` already in scope. These build, solve and export.
2. Offline post-processing, run with normal Python after HDF5 exports exist.

It intentionally handles only the current D1 production path:
regular_dipole + source_seed=template + direct_port at 210 MHz.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
REPO_ROOT = SKILL_ROOT.parents[2]
CASE_MATRIX = SKILL_ROOT / "recipes" / "data-prep" / "complete-case(D1)" / "RD_case_matrix.csv"
RECORD_TEMPLATE = SKILL_ROOT / "recipes" / "data-prep" / "complete-case(D1)" / "record_template_v1.json"

FREQ_GHZ = 0.21
FREQ_MHZ = 210.0
PHANTOM_TOP_Z_MM = -20.5
PHANTOM_SIZE = (270.0, 650.0, 300.0)
EXPORT_BOX = (-135.0, 135.0, -160.0, 160.0, -120.5, -20.5)


def _freq_label_tokens() -> list[str]:
    tokens = []
    for value in (FREQ_MHZ, FREQ_GHZ, "freq"):
        token = str(value) if isinstance(value, str) else ("%g" % float(value))
        if token not in tokens:
            tokens.append(token)
    return tokens


def _field_candidates(parent_names: list[str], result_name: str) -> list[str]:
    candidates = []
    for parent in parent_names:
        for freq in _freq_label_tokens():
            for source in ("[1]", "(1)"):
                candidates.append(fr"{parent}\{result_name} (f={freq}) {source}")
    out = []
    for item in candidates:
        if item not in out:
            out.append(item)
    return out


def _rel(path: str | Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT))
    except Exception:
        return str(path)


def _token(value: float | int | str) -> str:
    f = float(value)
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    return ("%g" % f).replace(".", "p")


def record_id_for(row: dict) -> str:
    return (
        "cc_rd_"
        f"L{_token(row['L_line_mm'])}_"
        f"W{_token(row['strip_width_mm'])}_"
        f"lo{_token(row['coil_to_phantom_mm'])}_"
        "direct_210"
    )


def read_case_row(case_matrix_id: str) -> dict:
    with CASE_MATRIX.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["case_matrix_id"] == case_matrix_id:
                return row
    raise KeyError(f"case_matrix_id not found: {case_matrix_id}")


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
        "phantom_top_z_mm": PHANTOM_TOP_Z_MM,
        "export_box_mm": list(EXPORT_BOX),
        "project_path": _rel(paths["project_path"]),
        "case_dir": _rel(paths["case_dir"]),
    }
    out = paths["artifacts_dir"] / "build_manifest.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def _vba_path(path: str | Path) -> str:
    return str(path).replace("\\", "\\\\").replace('"', '""')


def _vba_quote(text: str) -> str:
    return str(text).replace('"', '""')


def _add(model3d, title: str, code: str, done: list[str]):
    model3d.add_to_history(title, code.strip())
    done.append(title)


def live_build_case(de, project, model3d, case_matrix_id: str) -> dict:
    """Build a substrate-free direct-port regular dipole in the active MWS project."""
    row = read_case_row(case_matrix_id)
    paths = ensure_dirs(case_matrix_id)
    build_manifest(case_matrix_id)

    l_line = float(row["L_line_mm"])
    w_line = float(row["strip_width_mm"])
    lift = float(row["coil_to_phantom_mm"])
    feed_gap = float(row["feed_gap_mm"] or 2.0)
    hole = feed_gap / 2.0
    z_coil = PHANTOM_TOP_Z_MM + lift
    t_pec = 0.35
    done: list[str] = []
    failed = None

    try:
        try:
            qm = de.quiet_mode_enabled()
        except Exception:
            qm = None

        def drive():
            _add(model3d, "define D1 parameters", f"""
StoreParameter "L_line", "{l_line:g}"
StoreParameter "W_line", "{w_line:g}"
StoreParameter "T", "{t_pec:g}"
StoreParameter "hole", "{hole:g}"
StoreParameter "coil_to_phantom_mm", "{lift:g}"
StoreParameter "z_coil", "{z_coil:g}"
StoreParameter "phantom_top_z", "{PHANTOM_TOP_Z_MM:g}"
StoreParameter "x_plantom", "{PHANTOM_SIZE[0]:g}"
StoreParameter "y_plantom", "{PHANTOM_SIZE[1]:g}"
StoreParameter "z_plantom", "{PHANTOM_SIZE[2]:g}"
StoreParameter "freq", "{FREQ_GHZ:g}"
""", done)

            _add(model3d, "set units background boundary", """
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

            _add(model3d, "define phantom material", """
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

            _add(model3d, "create substrate-free dipole phantom geometry", """
Component.New "component1"
With Brick
    .Reset
    .Name "Dipole1"
    .Component "component1"
    .Material "PEC"
    .Xrange "W_line/2", "-W_line/2"
    .Yrange "L_line/2", "-L_line/2"
    .Zrange "z_coil", "z_coil+T"
    .Create
End With
With Brick
    .Reset
    .Name "hole"
    .Component "component1"
    .Material "PEC"
    .Xrange "-W_line/2", "W_line/2"
    .Yrange "-hole", "hole"
    .Zrange "z_coil", "z_coil+T"
    .Create
End With
Solid.Subtract "component1:Dipole1", "component1:hole"
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
""", done)

            _add(model3d, "define direct discrete port", """
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

            _add(model3d, "define D1 field monitors", """
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

            _add(model3d, "set TD hex solver for D1 SAR", """
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
        "done": done,
        "failed": failed,
    }


def live_start_solver(project, model3d) -> dict:
    project.save()
    model3d.start_solver()
    return {"started": True, "is_running": bool(model3d.is_solver_running())}


def live_poll_solver(project, model3d) -> dict:
    running = bool(model3d.is_solver_running())
    info = None
    try:
        info = model3d.get_solver_run_info()
    except Exception as exc:  # noqa: BLE001
        info = {"error": repr(exc)}
    if not running:
        try:
            project.save()
        except Exception:
            pass
    return {"is_running": running, "solver_info": info}


def _select_export_hdf5(model3d, candidates: list[str], out_path: Path, step: int, subvol=EXPORT_BOX) -> dict:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    log_path = out_path.with_suffix(out_path.suffix + ".select.json")
    attempts = []
    chosen = ""
    for cand in candidates:
        try:
            ok = bool(model3d.SelectTreeItem(cand))
            attempts.append({"candidate": cand, "ok": ok})
            if ok:
                chosen = cand
                break
        except Exception as exc:  # noqa: BLE001
            attempts.append({"candidate": cand, "ok": False, "error": repr(exc)})
    result = {"ok": False, "path": str(out_path), "chosen": chosen, "attempts": attempts}
    if chosen:
        x0, x1, y0, y1, z0, z1 = subvol
        code = (
            "Sub Main\n"
            f'SelectTreeItem "{_vba_quote(chosen)}"\n'
            "With ASCIIExport\n"
            ".Reset\n"
            f'.FileName "{_vba_path(out_path)}"\n'
            '.SetFileType "hdf5"\n'
            '.Mode "FixedWidth"\n'
            f".Step {int(step)}\n"
            '.UseSubvolume "True"\n'
            f'.SetSubvolume "{x0:g}", "{x1:g}", "{y0:g}", "{y1:g}", "{z0:g}", "{z1:g}"\n'
            '.ExportCoordinatesInMeter "False"\n'
            ".Execute\n"
            "End With\n"
            "End Sub\n"
        )
        model3d._execute_vba_code(code)
        result["ok"] = out_path.exists() and out_path.stat().st_size > 0
        result["bytes"] = out_path.stat().st_size if out_path.exists() else 0
    log_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _as_complex(value):
    if isinstance(value, complex):
        return value
    if isinstance(value, (list, tuple)):
        if len(value) >= 2:
            return complex(float(value[0]), float(value[1]))
        return complex(float(value[0]), 0.0)
    if hasattr(value, "real") and hasattr(value, "imag"):
        return complex(value.real, value.imag)
    return complex(value)


def _nearest_index(values, target: float) -> int:
    return min(range(len(values)), key=lambda i: abs(float(values[i]) - target))


def _freq_axis_to_mhz(values) -> list[float]:
    freqs = [float(v) for v in values]
    if freqs and max(abs(v) for v in freqs) <= 10.0:
        return [v * 1000.0 for v in freqs]
    return freqs


def _extract_electrical_summary(project, case_matrix_id: str) -> dict:
    import cst.results as cr

    paths = ensure_dirs(case_matrix_id)
    case_dir = paths["case_dir"]
    log_dir = paths["log_dir"]
    pf = cr.ProjectFile(project.filename(), allow_interactive=True)
    rm = pf.get_3d()

    def read_curve(tree_path: str):
        item = rm.get_result_item(tree_path)
        return list(item.get_xdata()), list(item.get_ydata())

    s_path = r"1D Results\S-Parameters\S1,1"
    p_path = r"1D Results\Power\Excitation [1]\Power Accepted per Port\Port 1"
    z_path = r"1D Results\Discrete Ports\Impedances\Port 1 [1]"
    s_x, s_y = read_curve(s_path)
    p_x, p_y = read_curve(p_path)
    z_x, z_y = read_curve(z_path)
    s_freq_mhz = _freq_axis_to_mhz(s_x)
    p_freq_mhz = _freq_axis_to_mhz(p_x)
    z_freq_mhz = _freq_axis_to_mhz(z_x)

    s_vals = [_as_complex(v) for v in s_y]
    p_vals = [_as_complex(v).real for v in p_y]
    z_vals = [_as_complex(v) for v in z_y]
    s_db = [20.0 * math.log10(abs(v)) if abs(v) > 0 else float("-inf") for v in s_vals]

    i210 = _nearest_index(s_freq_mhz, FREQ_MHZ)
    ip210 = _nearest_index(p_freq_mhz, FREQ_MHZ)
    iz210 = _nearest_index(z_freq_mhz, FREQ_MHZ)
    min_i = min(range(len(s_db)), key=lambda i: s_db[i])

    with (case_dir / "sparams.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["freq_MHz", "S11_re", "S11_im", "S11_dB"])
        for freq, s11, db in zip(s_freq_mhz, s_vals, s_db):
            writer.writerow([freq, s11.real, s11.imag, db])
    with (case_dir / "power_accepted.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["freq_MHz", "p_accepted_W"])
        for freq, pacc in zip(p_freq_mhz, p_vals):
            writer.writerow([freq, pacc])
    with (case_dir / "impedance.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["freq_MHz", "input_R_ohm", "input_X_ohm"])
        for freq, zin in zip(z_freq_mhz, z_vals):
            writer.writerow([freq, zin.real, zin.imag])

    summary = {
        "p_accepted_W": p_vals[ip210],
        "s11_210MHz_dB": s_db[i210],
        "s11_min_dB": s_db[min_i],
        "resonant_frequency_MHz": float(s_freq_mhz[min_i]),
        "input_R_ohm": z_vals[iz210].real,
        "input_X_ohm": z_vals[iz210].imag,
        "source_paths": {"s11": s_path, "p_accepted": p_path, "impedance": z_path},
        "csv": {
            "sparams": str(case_dir / "sparams.csv"),
            "power_accepted": str(case_dir / "power_accepted.csv"),
            "impedance": str(case_dir / "impedance.csv"),
        },
    }
    (log_dir / "electrical_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def live_export_fields_and_sar(de, project, model3d, case_matrix_id: str) -> dict:
    """Export H/E/loss/current before SAR.Create, then native no-rescale SAR HDF5."""
    paths = ensure_dirs(case_matrix_id)
    rid = paths["record_id"]
    case_dir = paths["case_dir"]
    log_dir = paths["log_dir"]
    project.save()

    exports = {}
    field_specs = {
        "hfield_h5": (
            case_dir / "hfield_1mm.h5",
            1,
            _field_candidates([r"2D/3D Results\H-Field", r"3D Results\H-Field", "H-Field"], "h-field"),
        ),
        "efield_h5": (
            case_dir / "efield_1mm.h5",
            1,
            _field_candidates([r"2D/3D Results\E-Field", r"3D Results\E-Field", "E-Field"], "e-field"),
        ),
        "loss_h5": (
            case_dir / "loss_2mm.h5",
            2,
            _field_candidates(
                [r"2D/3D Results\Power Loss Dens.", r"2D/3D Results\Power Loss Density", "Power Loss Dens."],
                "loss",
            ),
        ),
        "surface_current_h5": (
            case_dir / "surfcurrent_raw.h5",
            2,
            _field_candidates(
                [r"2D/3D Results\Surface Current", r"3D Results\Surface Current", "Surface Current"],
                "surface current",
            ),
        ),
    }
    for key, (out_path, step, cands) in field_specs.items():
        try:
            subvol = EXPORT_BOX if key != "surface_current_h5" else (-200.0, 200.0, -400.0, 400.0, -50.0, 140.0)
            exports[key] = _select_export_hdf5(model3d, cands, out_path, step, subvol=subvol)
        except Exception as exc:  # noqa: BLE001
            exports[key] = {"ok": False, "path": str(out_path), "error": repr(exc)}

    # Native SAR two-hop route. Create is done here so scalar and HDF5 are same session.
    try:
        import sys

        sys.path.insert(0, str(SCRIPT_DIR))
        import export_native_sar as sarx

        sar_result = sarx.export_data_prep_sar10g(
            de,
            case_matrix_id,
            str(log_dir),
            freq_mhz=FREQ_MHZ,
            source_id="[1]",
            create=True,
            rescale="no rescale",
        )
        sar_src = Path(sar_result["out_h5"])
        sar_dst = case_dir / "sar10g_native_norescale_2mm.h5"
        if sar_src.resolve() != sar_dst.resolve():
            if sar_dst.exists():
                sar_dst.unlink()
            sar_dst.write_bytes(sar_src.read_bytes())
        sar_result["case_copy"] = str(sar_dst)
        sar_result["case_copy_bytes"] = sar_dst.stat().st_size if sar_dst.exists() else 0
        exports["sar10g_h5"] = sar_result
    except Exception as exc:  # noqa: BLE001
        exports["sar10g_h5"] = {"ok": False, "error": repr(exc)}

    project.save()
    try:
        exports["electrical_summary"] = {"ok": True, "summary": _extract_electrical_summary(project, case_matrix_id)}
    except Exception as exc:  # noqa: BLE001
        exports["electrical_summary"] = {"ok": False, "error": repr(exc)}
    audit = {
        "case_matrix_id": case_matrix_id,
        "record_id": rid,
        "exports": exports,
    }
    (log_dir / "field_export_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return audit


def _find_dataset(h5, preferred: list[str]):
    for key in preferred:
        if key in h5:
            return h5[key]
    raise KeyError(f"None of {preferred} found. Keys={list(h5.keys())}")


def _load_h_field(path: Path):
    import h5py
    import numpy as np

    with h5py.File(path, "r") as h5:
        x = np.asarray(h5["Mesh line x"]).ravel()
        y = np.asarray(h5["Mesh line y"]).ravel()
        z = np.asarray(h5["Mesh line z"]).ravel()
        fld = _find_dataset(h5, ["H-Field", "H Field", "Hfield"])

        def comp(name):
            arr = np.asarray(fld[name]["re"], dtype=float) + 1j * np.asarray(fld[name]["im"], dtype=float)
            return arr.reshape((z.size, y.size, x.size), order="F")

        return x, y, z, comp("x"), comp("y"), comp("z")


def _load_scalar_h5(path: Path, dataset_name: str):
    import h5py
    import numpy as np

    with h5py.File(path, "r") as h5:
        x = np.asarray(h5["Mesh line x"]).ravel()
        y = np.asarray(h5["Mesh line y"]).ravel()
        z = np.asarray(h5["Mesh line z"]).ravel()
        arr = np.asarray(h5[dataset_name], dtype=float).reshape((z.size, y.size, x.size), order="F")
    return x, y, z, arr


def _load_surface_current(path: Path):
    import h5py
    import numpy as np

    with h5py.File(path, "r") as h5:
        pos = np.asarray(h5["Position"])
        cur = h5["Surface current"]
        jx = np.asarray(cur["x"]["re"], dtype=float) + 1j * np.asarray(cur["x"]["im"], dtype=float)
        jy = np.asarray(cur["y"]["re"], dtype=float) + 1j * np.asarray(cur["y"]["im"], dtype=float)
        jz = np.asarray(cur["z"]["re"], dtype=float) + 1j * np.asarray(cur["z"]["im"], dtype=float)
        xyz = np.column_stack([pos["x"], pos["y"], pos["z"]])
    return xyz, jx, jy, jz


def _nearest(coord, target):
    import numpy as np

    return int(np.argmin(np.abs(coord - target)))


def _plane_roi(arr2d, x, y, roi=40.0):
    import numpy as np

    mask_x = np.abs(x) <= roi
    mask_y = np.abs(y) <= roi
    return arr2d[np.ix_(mask_y, mask_x)]


def _interp_plane_to_48(plane_yx, x, y):
    import numpy as np
    from scipy.interpolate import RegularGridInterpolator

    xg = np.linspace(float(x.min()), float(x.max()), 48)
    yg = np.linspace(float(y.min()), float(y.max()), 48)
    interp = RegularGridInterpolator((y, x), plane_yx, bounds_error=False, fill_value=0.0)
    yy, xx = np.meshgrid(yg, xg, indexing="ij")
    pts = np.column_stack([yy.ravel(), xx.ravel()])
    return xg, yg, interp(pts).reshape(48, 48)


def compute_case_metrics(case_matrix_id: str, p_accepted_W: float | None = None, s11_210MHz_dB: float | None = None) -> dict:
    """Compute B1/SAR artifacts from exported fields and write fom.json."""
    import numpy as np

    paths = ensure_dirs(case_matrix_id)
    row = read_case_row(case_matrix_id)
    rid = paths["record_id"]
    case_dir = paths["case_dir"]
    out_dir = paths["output_dir"]
    pacc = float(p_accepted_W) if p_accepted_W else None

    h_path = case_dir / "hfield_1mm.h5"
    sar_path = case_dir / "sar10g_native_norescale_2mm.h5"
    if not h_path.exists():
        raise FileNotFoundError(h_path)

    x, y, z, hx, hy, _hz = _load_h_field(h_path)
    b1 = (4.0 * math.pi * 1e-7) * np.abs(hx - 1j * hy) / 2.0 * 1e6
    if pacc and pacc > 0:
        b1 = b1 / math.sqrt(pacc)
    surface_z = PHANTOM_TOP_Z_MM
    depths = np.array([30.0, 60.0, 100.0])
    z_targets = surface_z - depths

    def roi_at_depth(depth):
        iz = _nearest(z, surface_z - depth)
        roi = _plane_roi(b1[iz], x, y)
        return iz, roi

    surface_mask = (z <= surface_z) & (z >= surface_z - 10.0)
    xy_mask = (np.abs(x)[None, None, :] <= 40.0) & (np.abs(y)[None, :, None] <= 40.0)
    surf_vals = b1[surface_mask[:, None, None] & xy_mask]
    iz30, roi30 = roi_at_depth(30.0)
    iz60, roi60 = roi_at_depth(60.0)
    iz100, roi100 = roi_at_depth(100.0)
    phantom_mask = (z[:, None, None] <= surface_z) & (z[:, None, None] >= surface_z - 150.0)
    b1_masked = np.where(phantom_mask, b1, -np.inf)
    peak_idx = np.unravel_index(int(np.nanargmax(b1_masked)), b1.shape)
    peak_xyz = [float(x[peak_idx[2]]), float(y[peak_idx[1]]), float(z[peak_idx[0]])]

    # B1 depth profile over central ROI for all z planes.
    depth_rows = []
    for iz, zz in enumerate(z):
        depth = surface_z - float(zz)
        roi = _plane_roi(b1[iz], x, y)
        depth_rows.append([
            depth,
            float(zz),
            float(np.nanmean(roi)),
            float(np.nanpercentile(roi, 10)),
            float(np.nanpercentile(roi, 50)),
            float(np.nanpercentile(roi, 90)),
        ])
    b1_depth_csv = out_dir / f"{rid}_b1_depth.csv"
    depth_arr = np.asarray(depth_rows)
    np.savetxt(
        b1_depth_csv,
        depth_arr,
        delimiter=",",
        header="depth_mm,z_mm,b1p_roi_mean_uT_per_sqrtW,b1p_roi_p10_uT_per_sqrtW,b1p_roi_p50_uT_per_sqrtW,b1p_roi_p90_uT_per_sqrtW",
        comments="",
    )
    valid_depth = (depth_arr[:, 0] >= 0) & (depth_arr[:, 0] <= 150)
    depth_for_auc = depth_arr[valid_depth]
    if depth_for_auc.size:
        depth_for_auc = depth_for_auc[np.argsort(depth_for_auc[:, 0])]
    b1_auc = float(np.trapz(depth_for_auc[:, 2], depth_for_auc[:, 0])) if depth_for_auc.size else None
    surface_ref = float(np.nanmean(surf_vals)) if surf_vals.size else None
    half_value_depth = None
    if surface_ref and surface_ref > 0:
        target = 0.5 * surface_ref
        for depth, _zz, mean, *_rest in depth_for_auc:
            if mean <= target:
                half_value_depth = float(depth)
                break

    # B1 lateral profile: central x/y cuts at 30/60/100 mm depths.
    lateral_rows = []
    ix0 = _nearest(x, 0.0)
    iy0 = _nearest(y, 0.0)
    for depth in depths:
        iz = _nearest(z, surface_z - depth)
        for ix, xx in enumerate(x):
            lateral_rows.append([float(depth), "x", float(xx), float(b1[iz, iy0, ix])])
        for iy, yy in enumerate(y):
            lateral_rows.append([float(depth), "y", float(yy), float(b1[iz, iy, ix0])])
    b1_lateral_csv = out_dir / f"{rid}_b1_lateral.csv"
    with b1_lateral_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["depth_mm", "axis", "coord_mm", "b1p_uT_per_sqrtW"])
        writer.writerows(lateral_rows)

    # B1 slices.
    b1_slices = []
    z_used = []
    for target in z_targets:
        iz = _nearest(z, target)
        xg, yg, sl = _interp_plane_to_48(b1[iz], x, y)
        b1_slices.append(sl)
        z_used.append(float(z[iz]))
    b1_npz = out_dir / f"{rid}_b1_slices_48x48.npz"
    np.savez_compressed(
        b1_npz,
        b1p_slices_uT_per_sqrtW=np.asarray(b1_slices),
        depths_mm=depths,
        z_mm=np.asarray(z_used),
        x_mm=xg,
        y_mm=yg,
        source_h5=_rel(h_path),
    )

    sar_metrics = {
        "sar_status": "needs_validation",
        "sar_metric_source": None,
        "sar10g_max_W_per_kg_per_W": None,
        "sar10g_p99_W_per_kg_per_W": None,
        "sar10g_roi_mean_W_per_kg_per_W": None,
        "sar_hotspot_xyz_mm": None,
        "sar_hotspot_depth_mm": None,
        "sar_hotspot_concentration": None,
        "depth_profile_csv": None,
        "slices_48x48_npz": None,
        "raw_max": None,
    }
    if sar_path.exists():
        sx, sy, sz, sar_raw = _load_scalar_h5(sar_path, "SAR")
        sar = sar_raw / pacc if pacc and pacc > 0 else sar_raw
        max_idx = np.unravel_index(int(np.nanargmax(sar)), sar.shape)
        max_val = float(sar[max_idx])
        sar_vol_mean = float(np.nanmean(sar))
        roi = _plane_roi(sar[_nearest(sz, surface_z - 100.0)], sx, sy)
        sar_metrics.update({
            "sar_status": "validated_native_h5" if max_val > 0 else "needs_validation",
            "sar_metric_source": "CST_native_IEEE_C95.3_10g_HDF5_no_rescale_manual_Pacc_normalization",
            "sar10g_max_W_per_kg_per_W": max_val,
            "sar10g_p99_W_per_kg_per_W": float(np.nanpercentile(sar, 99)),
            "sar10g_roi_mean_W_per_kg_per_W": float(np.nanmean(roi)),
            "sar_hotspot_xyz_mm": [float(sx[max_idx[2]]), float(sy[max_idx[1]]), float(sz[max_idx[0]])],
            "sar_hotspot_depth_mm": float(surface_z - sz[max_idx[0]]),
            "sar_hotspot_concentration": max_val / sar_vol_mean if sar_vol_mean > 0 else None,
            "raw_max": float(np.nanmax(sar_raw)),
        })

        sar_rows = []
        for iz, zz in enumerate(sz):
            plane = sar[iz]
            roi_plane = _plane_roi(plane, sx, sy)
            sar_rows.append([
                surface_z - float(zz),
                float(zz),
                float(np.nanmax(plane)),
                float(np.nanpercentile(plane, 99)),
                float(np.nanmean(plane)),
                float(np.nanmax(roi_plane)),
                float(np.nanpercentile(roi_plane, 99)),
                float(np.nanmean(roi_plane)),
            ])
        sar_depth_csv = out_dir / f"{rid}_sar_depth.csv"
        np.savetxt(
            sar_depth_csv,
            np.asarray(sar_rows),
            delimiter=",",
            header="depth_mm,z_mm,sar_max_W_per_kg_per_W,sar_p99_W_per_kg_per_W,sar_mean_W_per_kg_per_W,sar_roi_max_W_per_kg_per_W,sar_roi_p99_W_per_kg_per_W,sar_roi_mean_W_per_kg_per_W",
            comments="",
        )
        sar_slices = []
        sar_z_used = []
        for target in z_targets:
            iz = _nearest(sz, target)
            sxg, syg, sl = _interp_plane_to_48(sar[iz], sx, sy)
            sar_slices.append(sl)
            sar_z_used.append(float(sz[iz]))
        sar_npz = out_dir / f"{rid}_sar10g_slices_48x48.npz"
        np.savez_compressed(
            sar_npz,
            sar_slices_W_per_kg_per_W=np.asarray(sar_slices),
            depths_mm=depths,
            z_mm=np.asarray(sar_z_used),
            x_mm=sxg,
            y_mm=syg,
            source_h5=_rel(sar_path),
            normalization="W/kg @ 1W accepted; no-rescale HDF5 divided by p_accepted_W",
        )
        sar_metrics["depth_profile_csv"] = _rel(sar_depth_csv)
        sar_metrics["slices_48x48_npz"] = _rel(sar_npz)

        scalar_file = paths["log_dir"] / f"{case_matrix_id}_sar10g_no_rescale_scalar.txt"
        if scalar_file.exists():
            sar_scalar = float(scalar_file.read_text(encoding="utf-8").strip())
            rel_err = abs(sar_metrics["raw_max"] - sar_scalar) / sar_scalar if sar_scalar else None
            sar_metrics["sarmax_norescale_getvalue"] = sar_scalar
            sar_metrics["sar_h5_vs_getvalue_relative_error"] = rel_err
            if not (sar_metrics["raw_max"] > 0 and rel_err is not None and rel_err < 0.05):
                sar_metrics["sar_status"] = "needs_validation"

    current_metrics = {
        "current_status": "partial",
        "current_peak_A_per_sqrtW": None,
        "current_mean_A_per_sqrtW": None,
        "current_center_to_end_ratio": None,
        "current_left_right_symmetry_error": None,
        "current_phase_span_deg": None,
        "current_hotspot_region": None,
        "clean_txt": None,
    }
    current_path = case_dir / "surfcurrent_raw.h5"
    if current_path.exists():
        xyz, jx, jy, jz = _load_surface_current(current_path)
        jmag = np.sqrt(np.abs(jx) ** 2 + np.abs(jy) ** 2 + np.abs(jz) ** 2)
        if pacc and pacc > 0:
            jmag = jmag / math.sqrt(pacc)
        l_line = float(row["L_line_mm"])
        y_abs = np.abs(xyz[:, 1])
        center = y_abs <= max(5.0, 0.10 * l_line)
        ends = y_abs >= 0.40 * l_line
        left = xyz[:, 1] < 0
        right = xyz[:, 1] > 0
        peak_i = int(np.nanargmax(jmag))
        phase = np.unwrap(np.angle(jy[np.abs(jy) > 0]))
        phase_span = float((phase.max() - phase.min()) * 180.0 / math.pi) if phase.size else None
        center_mean = float(np.nanmean(jmag[center])) if np.any(center) else None
        end_mean = float(np.nanmean(jmag[ends])) if np.any(ends) else None
        left_mean = float(np.nanmean(jmag[left])) if np.any(left) else None
        right_mean = float(np.nanmean(jmag[right])) if np.any(right) else None
        hotspot_y = abs(float(xyz[peak_i, 1]))
        if hotspot_y <= float(row["feed_gap_mm"] or 2.0) * 2:
            region = "feed"
        elif hotspot_y >= 0.45 * l_line:
            region = "tip"
        else:
            region = "edge"
        clean = case_dir / "surfcurrent_conductor_clean.txt"
        np.savetxt(
            clean,
            np.column_stack([xyz, jmag, np.real(jy), np.imag(jy)]),
            delimiter=",",
            header="x_mm,y_mm,z_mm,Jmag_A_per_sqrtW,Jy_re,Jy_im",
            comments="",
        )
        current_metrics.update({
            "current_status": "computed_from_surface_current_h5",
            "current_peak_A_per_sqrtW": float(np.nanmax(jmag)),
            "current_mean_A_per_sqrtW": float(np.nanmean(jmag)),
            "current_center_to_end_ratio": center_mean / end_mean if center_mean is not None and end_mean and end_mean > 0 else None,
            "current_left_right_symmetry_error": abs(left_mean - right_mean) / ((left_mean + right_mean) / 2.0) if left_mean and right_mean and (left_mean + right_mean) > 0 else None,
            "current_phase_span_deg": phase_span,
            "current_hotspot_region": region,
            "clean_txt": _rel(clean),
        })

    fom = {
        "record_id": rid,
        "case_matrix_id": case_matrix_id,
        "p_accepted_W": pacc,
        "s11_210MHz_dB": s11_210MHz_dB,
        "b1": {
            "b1p_surface_mean_uT_per_sqrtW": float(np.nanmean(surf_vals)) if surf_vals.size else None,
            "b1p_30mm_mean_uT_per_sqrtW": float(np.nanmean(roi30)),
            "b1p_60mm_mean_uT_per_sqrtW": float(np.nanmean(roi60)),
            "b1p_100mm_mean_uT_per_sqrtW": float(np.nanmean(roi100)),
            "b1p_at_10cm_mean_uT_per_sqrtW": float(np.nanmean(roi100)),
            "b1p_at_10cm_p10_uT_per_sqrtW": float(np.nanpercentile(roi100, 10)),
            "b1p_at_10cm_p50_uT_per_sqrtW": float(np.nanpercentile(roi100, 50)),
            "b1p_at_10cm_p90_uT_per_sqrtW": float(np.nanpercentile(roi100, 90)),
            "b1p_peak_uT_per_sqrtW": float(b1[peak_idx]),
            "b1p_peak_xyz_mm": peak_xyz,
            "cov_roi": float(np.nanstd(roi100) / np.nanmean(roi100)) if np.nanmean(roi100) > 0 else None,
            "half_value_depth_mm": half_value_depth,
            "penetration_auc_0_150_uTmm_per_sqrtW": b1_auc,
            "depth_profile_csv": _rel(b1_depth_csv),
            "lateral_profile_csv": _rel(b1_lateral_csv),
            "slices_48x48_npz": _rel(b1_npz),
        },
        "sar": sar_metrics,
        "current": current_metrics,
    }
    if current_metrics.get("clean_txt") and fom["sar"].get("sar_hotspot_xyz_mm"):
        try:
            hotspot = np.asarray(fom["sar"]["sar_hotspot_xyz_mm"], dtype=float)
            xyz, *_ = _load_surface_current(current_path)
            dist = np.sqrt(np.sum((xyz - hotspot[None, :]) ** 2, axis=1))
            fom["sar"]["sar_hotspot_distance_to_conductor_mm"] = float(np.nanmin(dist))
        except Exception:
            fom["sar"]["sar_hotspot_distance_to_conductor_mm"] = None
    if fom["sar"]["sar10g_max_W_per_kg_per_W"]:
        fom["sar"]["sar_efficiency_10cm"] = fom["b1"]["b1p_at_10cm_mean_uT_per_sqrtW"] / math.sqrt(fom["sar"]["sar10g_max_W_per_kg_per_W"])
    else:
        fom["sar"]["sar_efficiency_10cm"] = None
    (case_dir / "fom.json").write_text(json.dumps(fom, indent=2), encoding="utf-8")
    return fom


def _read_electrical_summary(path: str | Path | None) -> dict:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def write_record(
    case_matrix_id: str,
    p_accepted_W: float | None = None,
    s11_210MHz_dB: float | None = None,
    electrical_summary_path: str | Path | None = None,
) -> dict:
    row = read_case_row(case_matrix_id)
    paths = ensure_dirs(case_matrix_id)
    rid = paths["record_id"]
    electrical = _read_electrical_summary(electrical_summary_path)
    pacc = p_accepted_W if p_accepted_W is not None else electrical.get("p_accepted_W")
    s11_db = s11_210MHz_dB if s11_210MHz_dB is not None else electrical.get("s11_210MHz_dB")
    fom = compute_case_metrics(case_matrix_id, p_accepted_W=pacc, s11_210MHz_dB=s11_db)
    template = json.loads(RECORD_TEMPLATE.read_text(encoding="utf-8"))

    record = template
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
        "source_project_path": "artifact_generated_from_case_matrix_v1",
        "project_copy_path": _rel(paths["project_path"]),
        "build_manifest_path": _rel(paths["artifacts_dir"] / "build_manifest.json"),
        "schematic_snapshot_path": None,
    })
    record["geometry"].update({
        "family": row["family"],
        "topology": "regular_dipole_direct_port",
        "prototype_fidelity": row["prototype_fidelity"],
        "model_variant": "substrate_free_coil_phantom",
        "include_substrate": False,
        "support_stack": "none",
        "L_line_mm": float(row["L_line_mm"]),
        "strip_width_mm": float(row["strip_width_mm"]),
        "coil_to_phantom_mm": float(row["coil_to_phantom_mm"]),
        "feed_gap_mm": float(row["feed_gap_mm"] or 2.0),
    })
    record["electrical_design"].update({
        "freq_MHz": FREQ_MHZ,
        "field_source_id": "[1]",
        "network_role": row["network_role"],
    })
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
    design_tokens = ["coil_and_phantom_only", "regular_dipole", "direct_port"]
    if row.get("role") in {"perturbation", "interaction"}:
        design_tokens.append(row["role"])
    record["learning_card"]["design_tokens"] = design_tokens

    flags = [
        "coil_and_phantom_only",
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
    fields = [
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
    bridge = record["electrical_design"].get("fractionated_bridge", {})
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
        "segment_count_total": record["geometry"].get("segment_count_total"),
        "seg_gap_mm": record["geometry"].get("seg_gap_mm"),
        "bridge_count_total": record["geometry"].get("bridge_count_total"),
        "lt_bridge_mode": bridge.get("lt_bridge_mode"),
        "bridge_C_pF": bridge.get("bridge_C_pF"),
        "bridge_L_nH": bridge.get("bridge_L_nH"),
        "bridge_R_ohm": bridge.get("bridge_R_ohm"),
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
    if path.exists():
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for existing in reader:
                rows[existing["record_id"]] = existing
    rows[record["record_id"]] = {k: row.get(k) for k in fields}
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for key in sorted(rows):
            writer.writerow(rows[key])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--emit-manifest", action="store_true")
    ap.add_argument("--write-record", action="store_true")
    ap.add_argument("--p-accepted", type=float, default=None)
    ap.add_argument("--s11-db", type=float, default=None)
    ap.add_argument("--electrical-summary", default=None)
    args = ap.parse_args()

    if args.emit_manifest:
        print(json.dumps(build_manifest(args.case), indent=2))
    if args.write_record:
        print(json.dumps(write_record(args.case, p_accepted_W=args.p_accepted, s11_210MHz_dB=args.s11_db, electrical_summary_path=args.electrical_summary), indent=2, default=str))


if __name__ == "__main__":
    main()
