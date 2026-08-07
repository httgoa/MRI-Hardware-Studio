#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
export_native_sar.py — AUTOMATED export of CST's native IEEE 10 g SAR 3D field,
through the MCP-managed DesignEnvironment. NO GUI, NO manual clicks.

Breakthrough (2026-07-16, ind150 test): native SAR 3D fields ARE exportable headless.
M3 fell back to GUI for two compounding reasons, both now solved:

  ROOT CAUSE 1 — result storage. CST 2024 keeps fields in the compressed `Storage.sdb`,
  NOT as loose `.m3d` files, UNLESS they are materialized. `Result3D("<name>")` needs a
  real `.m3d` on disk. Fields are materialized as `.m3d` ONLY in the in-memory window
  right after a solve (and by GUI interaction). After a plain close→reopen, or after a
  bare `SAR.Create` in a stale session, the `.m3d` are archived back into Storage.sdb and
  Result3D/SelectTreeItem/ASCIIExport all fail ("file does not exist" / "not available for
  current view"). => Do the SAR export in the SAME fresh post-solve session, before reopen.
  (If the project has a SAR post-processing template, the solve itself writes the SAR .m3d;
   otherwise call create_native_sar() once in that same window.)

  ROOT CAUSE 2 — tree visibility. `SAR.Create`'s own tree node is invisible to the headless
  SelectTreeItem/ASCIIExport channel (and calling SAR.Create can collapse the 2D/3D tree
  enumeration). The fix is to NOT select the SAR.Create node. Instead:
  1. (post-solve window) the native SAR .m3d exists on disk.
  2. `Result3D("SAR (f=freq) [1] (10g)")` — load that .m3d as a Result3D object
     (pure data read, bypasses the tree). Gives GetArray/GetNxNyNz/GetUnit directly.
  3. `res.AddToTree "2D/3D Results\SAR", "<label>"` — RE-INSERT it into the tree.
     THIS is the missing step: the re-inserted node IS selectable by SelectTreeItem,
     so a normal ASCIIExport (with coordinates) then works.

Verified: both methods below reproduce yesterday's GUI export BIT-FOR-BIT (0.000% max
point difference for ind150; peak 0.9355 W/kg, twin peaks y=+-112 mm, center dip 0.56).

Two ways to get the data out, both verified equal to yesterday's GUI export (peak
0.9355 W/kg, twin peaks y=+-112 mm, center dip 0.56 for ind150):
  A. `res.GetArray("xre")` in Python  -> raw scalar array (Nz,Ny,Nx), no coords, native
     non-uniform hex grid. Fast, zero files. Use when you only need scalar stats / a line
     and can get coords elsewhere.
  B. AddToTree + ASCIIExport -> HDF5 with `SAR` + `Mesh line x/y/z` (resampled uniform grid,
     same as GUI). Use when you need coordinates / a drop-in replacement for the GUI file.

Prereqs: the case's TD solve is done AND a power-loss density monitor `loss (f=freq) [1]`
exists. Run this in `cst_run_python_tool` with the live MCP `de` and the case active:
    import export_native_sar as E
    E.export(de, r"...\log\seg_ind150_sar_native.h5")     # method B (HDF5 + coords)
    stats = E.read_scalar(de)                              # method A (array + stats)
"""
import os
import tempfile
from pathlib import Path

SAR_MONITOR = "loss (f=freq) [1]"
SAR_TREE_LABEL = "SAR (f=freq) [1] (10g)"   # CST's default auto-name (no SetLabel)
SAR_PARENT = "2D/3D Results\\SAR"
DEFAULT_EXPORT_LABEL = "SAR_auto"
DATA_PREP_SUBVOL = ("-135", "135", "-160", "160", "-120.5", "-20.5")


def _quote_vba(value):
    return str(value).replace('"', '""')


def _path_vba(value):
    return _quote_vba(str(value))


def _vba(m, code):
    m._execute_vba_code("Sub Main\n" + code + "\nEnd Sub")


def _format_freq_token(value):
    value = float(value)
    if value.is_integer():
        return str(int(value))
    return "%g" % value


def _freq_label_tokens_from_mhz(freq_mhz):
    """Return likely CST result-tree frequency tokens for a MHz input.

    Data-prep records store frequency as MHz (210), while CST projects commonly
    use GHz units in result labels (`f=0.21`). Keep both tokens to avoid missing
    the native SAR/loss monitor because of project-unit naming.
    """
    mhz = float(freq_mhz)
    tokens = [_format_freq_token(mhz), _format_freq_token(mhz / 1000.0)]
    out = []
    for token in tokens:
        if token not in out:
            out.append(token)
    return out


def power_loss_monitor_candidates(freq_mhz=None, source_id="[1]"):
    candidates = []
    if freq_mhz is not None:
        for f in _freq_label_tokens_from_mhz(freq_mhz):
            candidates.extend([
                f"loss (f={f}) {source_id}",
                f"loss (f={f}) (1)",
            ])
    candidates.extend([
        f"loss (f=freq) {source_id}",
        "loss (f=freq) (1)",
        SAR_MONITOR,
    ])
    out = []
    for item in candidates:
        if item not in out:
            out.append(item)
    return out


def native_sar_label_candidates(freq_mhz=None, source_id="[1]"):
    """Return likely CST native SAR result labels, newest/current data-prep first.

    CST may name the same native SAR result with either a concrete monitor frequency
    (`f=0.21` when project units are GHz, `f=210` in MHz projects) or the parameter
    token (`f=freq`), and direct-port source names vary between `[1]` and `(1)` in
    older projects.
    """
    candidates = []
    if freq_mhz is not None:
        for f in _freq_label_tokens_from_mhz(freq_mhz):
            candidates.extend([
                f"SAR (f={f}) {source_id} (10g)",
                f"SAR (f={f}) (1) (10g)",
            ])
    candidates.extend([
        f"SAR (f=freq) {source_id} (10g)",
        "SAR (f=freq) (1) (10g)",
        SAR_TREE_LABEL,
    ])
    out = []
    for item in candidates:
        if item not in out:
            out.append(item)
    return out


def native_sar_file_candidates(de):
    """Return materialized SAR .m3d files from the active project's Result folder.

    CST sometimes refuses to resolve decimal-frequency labels such as
    ``Result3D("SAR (f=0.21) [1] (10g)")`` even though the matching .m3d exists.
    Passing the full .m3d path works, so data-prep exports should try these first.
    """
    try:
        project_path = Path(de.active_project().filename())
    except Exception:
        return []
    result_dir = project_path.with_suffix("") / "Result"
    if not result_dir.exists():
        return []
    return [str(p) for p in sorted(result_dir.glob("SAR*.m3d"), key=lambda p: p.stat().st_mtime, reverse=True)]


def create_native_sar(de, rescale="no rescale", monitor=SAR_MONITOR, average_weight="10",
                      scalar_path=None):
    """Hop 1: run SAR.Create with DEFAULT label so CST writes the native .m3d to Result/.

    rescale: use 'no rescale' for production; normalize manually by measured P_acc.
             'scale accepted' is known to silently fail on severe direct-port mismatch.
    Returns max-sar scalar (as reported by GetValue, always reliable).
    """
    p = de.active_project()
    m = p.model3d
    cleanup_scalar = False
    if scalar_path is None:
        fd, scalar_path = tempfile.mkstemp(prefix="cst_sarmax_", suffix=".txt")
        os.close(fd)
        cleanup_scalar = True
    _vba(m,
         'Dim sarmax As Double\n'
         'With SAR\n.Reset\n.PowerlossMonitor "%s"\n.AverageWeight "%s"\n'
         '.SetOption "IEEE C95.3"\n.SetOption "%s"\n.SetOption "volaccuracy 0.05"\n'
         '.Create\n'
         'sarmax = .GetValue("max sar")\nEnd With\n'
         'Dim fnum As Integer\n'
         'fnum = FreeFile\n'
         'Open "%s" For Output As #fnum\n'
         'Print #fnum, CStr(sarmax)\n'
         'Close #fnum'
         % (_quote_vba(monitor), _quote_vba(average_weight), _quote_vba(rescale), _path_vba(scalar_path)))
    try:
        with open(scalar_path, "r", encoding="utf-8") as fh:
            return float(fh.read().strip())
    finally:
        if cleanup_scalar:
            try:
                os.remove(scalar_path)
            except OSError:
                pass


def read_scalar(de, label=SAR_TREE_LABEL):
    """Method A: load native SAR .m3d as Result3D and pull the scalar array in Python.

    Returns dict(nx,ny,nz, unit, freq, max, array=(Nz,Ny,Nx) numpy). No coordinates
    (native hex grid is non-uniform; use export() if you need coords).
    """
    import numpy as np
    p = de.active_project()
    m = p.model3d
    r = m.Result3D(label)                       # loads Result/<label>.m3d, bypasses tree
    nx, ny, nz = r.GetNx(), r.GetNy(), r.GetNz()
    a = np.asarray(r.GetArray("xre"), dtype=np.float64)   # scalar stored in xre
    sar = a.reshape((nz, ny, nx))               # index = ix + iy*nx + iz*nx*ny
    return {"nx": nx, "ny": ny, "nz": nz, "unit": r.GetUnit(),
            "freq": r.GetFrequency(), "max": float(sar.max()), "array": sar}


def add_native_sar_to_tree(de, labels=None, export_label=DEFAULT_EXPORT_LABEL):
    """Two-hop fix: load native SAR by Result3D, then re-insert under a selectable label.

    Returns dict(native_label, tree_label, tree_node). This deliberately does NOT
    SelectTreeItem the SAR.Create node, which is invisible/collapsed in headless runs.
    """
    p = de.active_project()
    m = p.model3d
    labels = list(labels or [SAR_TREE_LABEL])
    parent = SAR_PARENT
    tree_node = parent + "\\" + export_label
    errors = []
    for native_label in labels:
        try:
            _vba(
                m,
                'Dim res As Object\n'
                'Set res = Result3D("%s")\n'
                'res.AddToTree "%s", "%s"'
                % (_quote_vba(native_label), _quote_vba(parent), _quote_vba(export_label)),
            )
            select_nodes = [tree_node]
            native_name = Path(str(native_label)).stem if str(native_label).lower().endswith(".m3d") else str(native_label)
            real_node = parent + "\\" + native_name
            if real_node not in select_nodes:
                select_nodes.append(real_node)
            selected = None
            select_errors = []
            for node in select_nodes:
                try:
                    if m.SelectTreeItem(node):
                        selected = node
                        break
                    select_errors.append({"node": node, "ok": False})
                except Exception as exc:
                    select_errors.append({"node": node, "error": repr(exc)})
            if selected:
                return {
                    "native_label": native_label,
                    "tree_label": export_label,
                    "tree_node": selected,
                }
            errors.append({"label": native_label, "error": "AddToTree completed but SelectTreeItem returned False", "select_nodes": select_errors})
        except Exception as exc:
            errors.append({"label": native_label, "error": repr(exc)})
    raise RuntimeError("Could not AddToTree/select native SAR. Tried: %r" % errors)


def export(de, out_h5, subvol=DATA_PREP_SUBVOL, step=2,
           label=SAR_TREE_LABEL, labels=None, export_label=DEFAULT_EXPORT_LABEL):
    """Method B: AddToTree + ASCIIExport -> HDF5 with SAR + Mesh line x/y/z (coords).

    Drop-in replacement for the GUI 'Export 3D Field Result'. Default subvolume is
    the D1 data-prep phantom/loss non-zero box. Returns dict with byte size and
    labels used.
    """
    p = de.active_project()
    m = p.model3d
    if os.path.exists(out_h5):
        os.remove(out_h5)
    labels = labels or [label]
    inserted = add_native_sar_to_tree(de, labels=labels, export_label=export_label)
    node = inserted["tree_node"]
    x0, x1, y0, y1, z0, z1 = subvol
    _vba(m,
         'SelectTreeItem "%s"\nWith ASCIIExport\n.Reset\n.FileName "%s"\n'
         '.SetFileType "hdf5"\n.Mode "FixedWidth"\n.Step %d\n.UseSubvolume "True"\n'
         '.SetSubvolume "%s", "%s", "%s", "%s", "%s", "%s"\n'
         '.ExportCoordinatesInMeter "False"\n.Execute\nEnd With'
         % (_path_vba(node), _path_vba(out_h5), step,
            _quote_vba(x0), _quote_vba(x1), _quote_vba(y0), _quote_vba(y1), _quote_vba(z0), _quote_vba(z1)))
    if not os.path.exists(out_h5):
        raise RuntimeError("ASCIIExport produced no file")
    return {
        "h5_bytes": os.path.getsize(out_h5),
        "out_h5": out_h5,
        "tree_node": node,
        "native_label": inserted["native_label"],
        "export_label": inserted["tree_label"],
    }


def full_pipeline(de, out_h5, rescale="no rescale", monitor=SAR_MONITOR, freq_mhz=None,
                  source_id="[1]", subvol=DATA_PREP_SUBVOL,
                  step=2, export_label=DEFAULT_EXPORT_LABEL):
    """Convenience: SAR.Create (native .m3d) -> AddToTree -> ASCIIExport HDF5. One call.

    Assumes solve is done. Returns dict(sarmax_getvalue, h5_bytes, out_h5).
    """
    sarmax = create_native_sar(de, rescale=rescale, monitor=monitor)
    # SAR.Create materializes the native field only now.  Re-scan the Result
    # directory after Create and prefer the concrete .m3d path; decimal-frequency
    # labels are not reliably resolved by Result3D even when that file exists.
    labels = native_sar_file_candidates(de) + native_sar_label_candidates(
        freq_mhz=freq_mhz, source_id=source_id
    )
    exported = export(de, out_h5, subvol=subvol, step=step, labels=labels, export_label=export_label)
    exported.update({"sarmax_getvalue": sarmax, "rescale": rescale, "monitor": monitor})
    return exported


def export_data_prep_sar10g(de, case_id, log_dir, freq_mhz=210, source_id="[1]",
                            monitor=None, create=False, rescale="no rescale",
                            subvol=DATA_PREP_SUBVOL,
                            step=2):
    """Standard complete-case SAR export with an audit JSON.

    Use this from `cst_run_python_tool` in the same fresh post-solve session:

        import sys
        sys.path.insert(0, r"...\\.agents\\skills\\mri-coil-design-workflow\\scripts")
        import export_native_sar as sarx
        result = sarx.export_data_prep_sar10g(de, "RD_A02", r"...\\results_data_prep\\RD_A02\\log")

    If `create=True`, the helper runs SAR.Create with no-rescale first and records the
    scalar. If SAR.Create was already run in the same session, keep `create=False`.
    """
    import json
    os.makedirs(log_dir, exist_ok=True)
    file_freq_token = _format_freq_token(float(freq_mhz))
    out_h5 = os.path.join(log_dir, f"{case_id}_sar10g_f_{file_freq_token}_1.h5")
    audit_path = os.path.join(log_dir, "sar_export_hdf5.json")
    monitor_candidates = [monitor] if monitor else power_loss_monitor_candidates(freq_mhz=freq_mhz, source_id=source_id)
    monitor = monitor_candidates[0]
    result = {
        "ok": False,
        "case_id": case_id,
        "path": out_h5,
        "audit_path": audit_path,
        "freq_mhz": float(freq_mhz),
        "source_id": source_id,
        "monitor": monitor,
        "monitor_candidates": monitor_candidates,
        "subvol": list(subvol),
        "step": step,
        "create": create,
    }
    try:
        labels = native_sar_file_candidates(de) + native_sar_label_candidates(freq_mhz=freq_mhz, source_id=source_id)
        if create:
            scalar_path = os.path.join(log_dir, f"{case_id}_sar10g_no_rescale_scalar.txt")
            result["scalar_path"] = scalar_path
            create_errors = []
            for candidate_monitor in monitor_candidates:
                try:
                    result["sarmax_getvalue"] = create_native_sar(
                        de,
                        rescale=rescale,
                        monitor=candidate_monitor,
                        scalar_path=scalar_path,
                    )
                    monitor = candidate_monitor
                    result["monitor"] = monitor
                    break
                except Exception as exc:
                    create_errors.append({"monitor": candidate_monitor, "error": repr(exc)})
            else:
                result["create_errors"] = create_errors
                raise RuntimeError("SAR.Create failed for all monitor candidates: %r" % create_errors)
            result["rescale"] = rescale
            labels = native_sar_file_candidates(de) + native_sar_label_candidates(freq_mhz=freq_mhz, source_id=source_id)
        exported = export(
            de,
            out_h5,
            labels=labels,
            subvol=subvol,
            step=step,
            export_label=f"{case_id}_SAR10g_export",
        )
        result.update(exported)
        result["ok"] = True
    except Exception as exc:
        result["error"] = repr(exc)
    with open(audit_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    if not result["ok"]:
        raise RuntimeError("data-prep SAR HDF5 export failed; see %s: %s" % (audit_path, result.get("error")))
    return result
