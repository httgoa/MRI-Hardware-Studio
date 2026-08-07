"""Live CST helpers for the fractionated-dipole paper reproduction.

Import this module only inside ``cst_run_python_tool``.  The caller owns solver
polling so a long sweep remains observable and resumable one case at a time.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


FREQ_GHZ = 0.298
HFIELD_NODE = r"2D/3D Results\H-Field\h-field (f=0.298) [1]"
LOSS_MONITOR = "loss (f=0.298) [1]"
POWER_ACCEPTED_NODE = r"1D Results\Power\Excitation [1]\Power Accepted per Port\Port 1"

# Fig. 3(d) must include lossy phantom beyond both conductor ends. The
# validated reference run used +/-160 mm through L=300 mm, then retained a
# 15 mm margin for longer dipoles. Keep this rule here instead of in callers.
FIG3_MIN_Y_HALF_MM = 160.0
FIG3_END_MARGIN_MM = 15.0
FIG3_FIXED_SPAN_MAX_LENGTH_MM = 300.0


def longitudinal_export_y_half_mm(length_mm: float) -> float:
    """Return the paper-reproduction Y half-span for Fig. 3/4 exports."""
    length_mm = float(length_mm)
    if not 0.0 < length_mm <= 500.0:
        raise ValueError("length_mm must be in (0, 500] for the 500 mm phantom")
    if length_mm <= FIG3_FIXED_SPAN_MAX_LENGTH_MM:
        return FIG3_MIN_Y_HALF_MM
    return length_mm / 2.0 + FIG3_END_MARGIN_MM


def _vba(model3d, code: str) -> None:
    model3d._execute_vba_code("Sub Main\n" + code + "\nEnd Sub")


def set_case(model3d, *, length_mm: float = 300.0, l_nh: float = 0.0, c_pf: float = 0.0) -> dict:
    _vba(
        model3d,
        'StoreParameter "L_total", "%g"\n'
        'StoreParameter "L_seg", "%g"\n'
        'StoreParameter "C_seg", "%g"' % (length_mm, l_nh, c_pf),
    )
    model3d.Rebuild()
    actual = {
        "length_mm": float(model3d.RestoreParameter("L_total")),
        "l_nh": float(model3d.RestoreParameter("L_seg")),
        "c_pf": float(model3d.RestoreParameter("C_seg")),
    }
    expected = {
        "length_mm": float(length_mm),
        "l_nh": float(l_nh),
        "c_pf": float(c_pf),
    }
    mismatches = {
        key: {"expected": expected[key], "actual": actual[key]}
        for key in expected
        if abs(expected[key] - actual[key]) > 1.0e-9
    }
    if mismatches:
        raise RuntimeError("case parameter rebuild mismatch: %r" % mismatches)
    return actual


def start_case(project, model3d) -> dict:
    project.save()
    model3d.start_solver()
    return {"started": True, "running": bool(model3d.is_solver_running())}


def poll_case(model3d) -> dict:
    return {
        "running": bool(model3d.is_solver_running()),
        "info": model3d.get_solver_run_info(),
    }


def required_results_ready(model3d) -> dict:
    nodes = [
        HFIELD_NODE,
        r"2D/3D Results\Power Loss Dens.\loss (f=0.298) [1]",
    ]
    status = {}
    errors = {}
    for node in nodes:
        try:
            status[node] = bool(model3d.SelectTreeItem(node))
        except Exception as exc:
            status[node] = False
            errors[node] = repr(exc)
    return {"ok": all(status.values()), "nodes": status, "errors": errors}


def _export_hfield(model3d, path: Path, y_half_mm: float, step: int = 2) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    if not model3d.SelectTreeItem(HFIELD_NODE):
        raise RuntimeError("H-field node not selectable: " + HFIELD_NODE)
    _vba(
        model3d,
        'SelectTreeItem "%s"\n'
        'With ASCIIExport\n.Reset\n.FileName "%s"\n.SetFileType "hdf5"\n'
        '.Mode "FixedWidth"\n.Step %d\n.UseSubvolume "True"\n'
        '.SetSubvolume "-80", "80", "%g", "%g", "-160", "25"\n'
        '.ExportCoordinatesInMeter "False"\n.Execute\nEnd With'
        % (
            HFIELD_NODE.replace('"', '""'),
            str(path).replace('"', '""'),
            step,
            -y_half_mm,
            y_half_mm,
        ),
    )
    if not path.exists():
        raise RuntimeError("H-field export did not create " + str(path))
    return path.stat().st_size


def _read_paccepted(project) -> float:
    import cst.results as cr
    import numpy as np

    pf = cr.ProjectFile(project.filename(), allow_interactive=True)
    r3d = pf.get_3d()
    run_ids = r3d.get_run_ids(POWER_ACCEPTED_NODE)
    if not run_ids:
        raise RuntimeError("no run ids for accepted-power result: " + POWER_ACCEPTED_NODE)
    data = r3d.get_result_item(POWER_ACCEPTED_NODE, run_ids[-1])
    x = np.asarray(data.get_xdata())
    y = np.asarray(data.get_ydata())
    if x.size == 0 or y.size == 0 or x.size != y.size:
        raise RuntimeError("accepted-power result is empty or malformed")
    index = int(np.argmin(np.abs(x - FREQ_GHZ)))
    paccepted = float(np.real(y[index]))
    if not np.isfinite(paccepted) or paccepted <= 0.0:
        raise RuntimeError("invalid accepted power at 0.298 GHz: %r" % paccepted)
    return paccepted


def export_case(
    de,
    project,
    model3d,
    *,
    case_id: str,
    log_dir: str,
    length_mm: float,
    y_half_mm: float | None = None,
) -> dict:
    """Export H before SAR.Create, native SAR HDF5, and accepted power.

    Derive the longitudinal ROI from ``length_mm`` by default. A caller may
    request a larger ROI, but a smaller one is rejected so Fig. 3(d) cannot be
    silently clipped to the conductor length.
    """
    import importlib
    import export_native_sar as sarx

    sarx = importlib.reload(sarx)
    required_y_half_mm = longitudinal_export_y_half_mm(length_mm)
    if y_half_mm is None:
        y_half_mm = required_y_half_mm
    y_half_mm = float(y_half_mm)
    if y_half_mm + 1.0e-9 < required_y_half_mm:
        raise ValueError(
            "longitudinal export ROI is too small for Fig. 3/4: "
            f"requested +/-{y_half_mm:g} mm, required at least "
            f"+/-{required_y_half_mm:g} mm for L={float(length_mm):g} mm"
        )
    root = Path(log_dir)
    root.mkdir(parents=True, exist_ok=True)
    hfield = root / f"{case_id}_hfield.h5"
    sar_h5 = root / f"{case_id}_sar10g.h5"
    h_bytes = _export_hfield(model3d, hfield, y_half_mm=y_half_mm, step=2)
    sar = sarx.full_pipeline(
        de,
        str(sar_h5),
        rescale="no rescale",
        monitor=LOSS_MONITOR,
        freq_mhz=298,
        source_id="[1]",
        subvol=("-40", "40", str(-y_half_mm), str(y_half_mm), "-40", "0"),
        step=2,
        export_label=f"{case_id}_SAR10g_export",
    )
    paccepted = _read_paccepted(project)
    result = {
        "ok": True,
        "case_id": case_id,
        "hfield_h5": str(hfield),
        "hfield_bytes": h_bytes,
        "sar10g_h5": str(sar_h5),
        "sar10g_bytes": sar["h5_bytes"],
        "sarmax_raw_Wkg": sar["sarmax_getvalue"],
        "p_accepted_W": paccepted,
        "sarmax_1W_Wkg": sar["sarmax_getvalue"] / paccepted,
        "length_mm": float(length_mm),
        "export_y_min_mm": -y_half_mm,
        "export_y_max_mm": y_half_mm,
        "required_y_half_mm": required_y_half_mm,
    }
    (root / f"{case_id}_export.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result
