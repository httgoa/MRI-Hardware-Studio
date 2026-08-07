#!/usr/bin/env python3
"""
build_dipole.py — Zero-LLM builder for the verified dipole+phantom model.

Runs INSIDE the CST MCP process via `cst_run_python_tool` (so `de`, `model3d`,
`project` are already in scope). Do NOT run it standalone — there is no CST COM
outside the MCP process, and starting a second COM client deadlocks the session
(see foundations/cst-red-lines.md).

WHY THIS EXISTS
    The dipole+phantom geometry is a FIXED, verified design (see
    building-blocks/vba-blocks/dipole-build.md — 5T, 210 MHz, matches the
    reference B1+). Re-deriving its 8 VBA blocks every session via the agent's
    ReAct loop is slow, burns tokens, and — worst — drives CST through N separate
    MCP round-trips (one popup or COM stall per block can hang the session).

    This module fixes the blocks as constants and drives them in ONE batched,
    quiet-mode `add_to_history` loop. Zero LLM, minimal round-trips, popups
    suppressed. This is the `batch_quiet` execution mode of
    driving/batch-execution.md, specialized for the dipole.

WHAT IT DOES NOT DO
    Only 3D modeling (parameters → units/background/boundary → materials →
    geometry → feed port → monitors → solver). Circuit tuning, AC co-sim, and
    B1+/SAR post-processing stay on the interactive MCP path (they are design/
    decision surfaces, not rote geometry) — see recipes/build/dipole-from-scratch.md
    stages 2-3.

USAGE inside cst_run_python_tool (after cst_new_project_tool + cst_save_project_tool):
    exec(open(r"...\\scripts\\build_dipole.py", encoding="utf-8").read())
    result = run_dipole_build(de, model3d, project)   # or pass params=... to tune
    # `result` -> {"done":[titles], "failed":(title,err)|None, "n_shapes":int|None,
    #              "shape_check":"ok"|"warn: ...", "elapsed_s":float}

The block CONTENTS are the ground truth from dipole-build.md. If that file and
this module ever disagree, dipole-build.md wins — reconcile before running.
"""

import time


# ---------------------------------------------------------------------------
# Verified defaults (dipole-build.md "Parameters"). Length mm / Frequency GHz,
# so the Larmor frequency 210 MHz == 0.21 GHz. Keep units consistent everywhere.
# ---------------------------------------------------------------------------
DEFAULT_PARAMS = {
    "L_line": "300",              # dipole arm length (mm) — KEY tunable
    "W_line": "5",                # dipole width (mm)
    "T": "0.35",                  # conductor thickness (mm)
    "hole": "1",                  # feed-gap half-height (mm)
    "W_total": "50",             # substrate width (mm)
    "L_total": "L_line+50",      # substrate length (mm) — expression
    "T_FR4": "1.5",              # FR-4 thickness (mm)
    "T_polycarbonate": "18",
    "T_foam": "1",
    "T_dipolet_to_plantom": "T_FR4+T_polycarbonate+T_foam",  # expression
    "x_plantom": "270",          # phantom size X (mm)
    "y_plantom": "650",          # phantom size Y (mm)
    "z_plantom": "300",          # phantom depth Z (mm)
    "freq": "0.21",              # Larmor frequency in GHz (monitors + solver band center)
}

# Solids created by the geometry blocks below, for the post-build shape-count
# self-check (Dipole1 + FR4_board + polycarbonate_board + foam + plantom = 5;
# `hole` is subtracted away, so it does NOT count).
EXPECTED_SHAPES = 5


def _params_block(params):
    """`define parameters` block: MakeSureParameterExists per entry (order kept)."""
    lines = []
    for name, expr in params.items():
        # StoreParameter-family: create-if-absent, does not clobber a user override.
        lines.append(f'MakeSureParameterExists("{name}", "{expr}")')
    return "\n".join(lines)


def build_blocks(params=None):
    """Return the ordered list of (title, vba_code) blocks for the dipole build.

    Pure function — no CST calls, safe to import/test offline. `params` overrides
    DEFAULT_PARAMS entry-by-entry (e.g. {"L_line": "320"} to tune arm length).
    Order is a HARD constraint: parameters → units/background → boundary →
    materials → geometry → feed port → monitors → solver (SOP §B.1).
    """
    p = dict(DEFAULT_PARAMS)
    if params:
        p.update(params)
    f = p["freq"]

    blocks = []

    blocks.append(("define parameters", _params_block(p)))

    blocks.append(("set units and background", r'''
With Units
    .SetUnit "Length", "mm"
    .SetUnit "Frequency", "GHz"
    .SetUnit "Time", "ns"
End With
Solver.FrequencyRange "0", "2"
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
'''.strip()))

    blocks.append(("set boundary", r'''
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
'''.strip()))

    # Materials — each gets a distinct .Colour so the 3D viewport is readable.
    blocks.append(("define materials", r'''
With Material
    .Reset
    .Name "FR-4 (lossy)"
    .Folder ""
    .Type "Normal"
    .Epsilon "4.3"
    .Mu "1.0"
    .TanD "0.025"
    .TanDGiven "True"
    .TanDModel "ConstTanD"
    .Colour "0.94", "0.82", "0.76"
    .Create
End With
With Material
    .Reset
    .Name "polycarbonate"
    .Folder "Folder_MyTong"
    .Type "Normal"
    .Epsilon "2.9"
    .Mu "1"
    .TanD "0.01"
    .TanDGiven "True"
    .TanDModel "ConstTanD"
    .Colour "0.65", "0.81", "0.94"
    .Create
End With
With Material
    .Reset
    .Name "foam"
    .Folder "Folder_MyTong"
    .Type "Normal"
    .Epsilon "1.05"
    .Mu "1"
    .Colour "0.90", "0.90", "0.90"
    .Create
End With
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
'''.strip()))

    # Geometry — dipole conductor with feed gap subtracted.
    blocks.append(("create dipole", r'''
Component.New "component1"
With Brick
    .Reset
    .Name "Dipole1"
    .Component "component1"
    .Material "PEC"
    .Xrange "W_line/2", "-W_line/2"
    .Yrange "L_line/2", "-L_line/2"
    .Zrange "0", "T"
    .Create
End With
With Brick
    .Reset
    .Name "hole"
    .Component "component1"
    .Material "FR-4 (lossy)"
    .Xrange "-W_line/2", "W_line/2"
    .Yrange "-hole", "hole"
    .Zrange "0", "T"
    .Create
End With
Solid.Subtract "component1:Dipole1", "component1:hole"
'''.strip()))

    # Substrate + holder + foam + phantom, stacked below the dipole in -Z.
    blocks.append(("create substrate stack", r'''
With Brick
    .Reset
    .Name "FR4_board"
    .Component "component1"
    .Material "FR-4 (lossy)"
    .Xrange "-W_total/2", "W_total/2"
    .Yrange "-L_total/2", "L_total/2"
    .Zrange "-T_FR4", "0"
    .Create
End With
With Brick
    .Reset
    .Name "polycarbonate_board"
    .Component "component1"
    .Material "Folder_MyTong/polycarbonate"
    .Xrange "-W_total/2", "W_total/2"
    .Yrange "-L_total/2", "L_total/2"
    .Zrange "-T_FR4", "-T_FR4-T_polycarbonate"
    .Create
End With
With Brick
    .Reset
    .Name "foam"
    .Component "component1"
    .Material "Folder_MyTong/foam"
    .Xrange "-W_total/2", "W_total/2"
    .Yrange "-L_total/2", "L_total/2"
    .Zrange "-T_dipolet_to_plantom", "-T_dipolet_to_plantom+T_foam"
    .Create
End With
With Brick
    .Reset
    .Name "plantom"
    .Component "component1"
    .Material "Folder_MyTong/plantom"
    .Xrange "-x_plantom/2", "x_plantom/2"
    .Yrange "-y_plantom/2", "y_plantom/2"
    .Zrange "-T_dipolet_to_plantom", "-T_dipolet_to_plantom-z_plantom"
    .Create
End With
'''.strip()))

    # Feed port — coordinate-based DiscretePort (SetP1/P2 first arg "False" =
    # free coordinates, NOT a picked point). Verified from-scratch; a
    # DiscreteFacePort with edge-picks is fragile from an empty project.
    blocks.append(("define feed port", r'''
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
    .SetP1 "False", "0", "-hole", "T/2"
    .SetP2 "False", "0", "hole", "T/2"
    .InvertDirection "False"
    .LocalCoordinates "False"
    .Wire ""
    .Position "end1"
    .Create
End With
'''.strip()))

    # Monitors at the Larmor frequency. h-field -> B1+; loss (Powerloss) -> SAR.
    blocks.append(("define monitors", f'''
With Monitor
    .Reset
    .Name "h-field (f={f})"
    .Dimension "Volume"
    .Domain "Frequency"
    .FieldType "Hfield"
    .MonitorValue "{f}"
    .UseSubvolume "False"
    .Create
End With
With Monitor
    .Reset
    .Name "e-field (f={f})"
    .Dimension "Volume"
    .Domain "Frequency"
    .FieldType "Efield"
    .MonitorValue "{f}"
    .UseSubvolume "False"
    .Create
End With
With Monitor
    .Reset
    .Name "loss (f={f})"
    .Dimension "Volume"
    .Domain "Frequency"
    .FieldType "Powerloss"
    .MonitorValue "{f}"
    .UseSubvolume "False"
    .Create
End With
'''.strip()))

    # Solver — HF Frequency Domain, tetrahedral, narrow band around Larmor.
    # SetKeepSolutionCoefficients keeps the field solution so the later circuit
    # co-sim can back-substitute and produce the [AC*] field.
    blocks.append(("set solver", r'''
ChangeSolverType "HF Frequency Domain"
Solver.FrequencyRange "0.15", "0.25"
With FDSolver
    .Reset
    .SetMethod "Tetrahedral", "General purpose"
    .OrderTet "Second"
    .Stimulation "All", "1"
    .AccuracyTet "1e-4"
    .MeshAdaptionTet "True"
    .CalcPowerLoss "True"
    .SetKeepSolutionCoefficients "MonitorsAndMeshAdaptation"
End With
'''.strip()))

    return blocks


def run_batch(de, model3d, project, blocks, expected_shapes=None):
    """Execute (title, vba) blocks in ONE quiet-mode add_to_history loop.

    Generic batch executor for the `batch_quiet` mode. Popups suppressed via
    de.quiet_mode_enabled(). On a block error, STOPS at the bad block (breakpoint),
    reports (title, error), and keeps the already-applied history — no whole-batch
    rollback (see driving/batch-execution.md). Saves at the end.

    Returns a dict: {done, failed, n_shapes, shape_check, elapsed_s}.
    """
    t0 = time.time()
    done, failed = [], None
    try:
        qm = de.quiet_mode_enabled()
    except Exception:
        qm = None

    def _drive():
        nonlocal failed
        for title, vba in blocks:
            try:
                model3d.add_to_history(title, vba)
                done.append(title)
            except Exception as e:  # noqa: BLE001 — report, do not re-raise
                failed = (title, f"{type(e).__name__}: {e}")
                break

    if qm is not None:
        with qm:
            _drive()
    else:
        _drive()

    # Save so the model is durable even if the foreground GUI didn't repaint
    # (cst-operation-notes.md: MCP background COM does not pump the GUI loop).
    try:
        project.save()
    except Exception as e:  # noqa: BLE001
        if failed is None:
            failed = ("<save>", f"{type(e).__name__}: {e}")

    # Minimal geometry self-check (lightweight CheckSolid analogue): compare the
    # shape count to expectation. WARN only — never auto-rebuild (that stays manual).
    n_shapes, shape_check = None, "skipped"
    if failed is None and expected_shapes is not None:
        try:
            n_shapes = _get_number_of_shapes(model3d)
            if n_shapes == expected_shapes:
                shape_check = "ok"
            else:
                shape_check = f"warn: got {n_shapes} shapes, expected {expected_shapes}"
        except Exception as e:  # noqa: BLE001
            shape_check = f"warn: shape count unavailable ({type(e).__name__}: {e})"

    return {
        "done": done,
        "failed": failed,
        "n_shapes": n_shapes,
        "shape_check": shape_check,
        "elapsed_s": round(time.time() - t0, 2),
    }


def _get_number_of_shapes(model3d):
    """Read Solid.GetNumberOfShapes() WITHOUT adding a history block.

    VBA has no return channel, so run a TRANSIENT VBA snippet (via
    model3d._execute_vba_code — the same private fallback probe_project.py uses;
    does NOT append to the history tree, so no SOP §B.8 label pollution) that
    writes the count to a temp file, then read it back in Python. Uses the
    classic `Open ... For Output As #1` / `Print #1` file I/O that is verified
    reliable in 3D VBA (FileSystemObject is flagged unreliable — see
    recipes/build/demo-recording-mode.md). Best-effort: any failure surfaces as
    a warn in shape_check, never blocks the build.
    """
    import os
    import tempfile

    out = os.path.join(tempfile.gettempdir(), "_cst_dipole_nshapes.txt")
    if os.path.exists(out):
        try:
            os.remove(out)
        except OSError:
            pass
    op = out.replace("\\", "\\\\")
    vba = (
        "Sub Main\n"
        "Dim n As Long\n"
        "n = Solid.GetNumberOfShapes()\n"
        f'Open "{op}" For Output As #1\n'
        "Print #1, n\n"
        "Close #1\n"
        "End Sub\n"
    )
    model3d._execute_vba_code(vba)
    with open(out, encoding="utf-8", errors="replace") as fh:
        return int(float(fh.read().strip()))


def run_dipole_build(de, model3d, project, params=None):
    """Convenience entry point: build the dipole and self-check. Returns result dict."""
    blocks = build_blocks(params)
    return run_batch(de, model3d, project, blocks, expected_shapes=EXPECTED_SHAPES)


# Offline self-test (no CST): `python build_dipole.py` prints block titles + count.
if __name__ == "__main__":
    bl = build_blocks()
    print(f"build_blocks() -> {len(bl)} blocks:")
    for i, (title, vba) in enumerate(bl, 1):
        print(f"  {i}. {title}  ({len(vba)} chars)")
    assert len(bl) == 9, f"expected 9 blocks (8 build + params), got {len(bl)}"
    assert bl[0][0] == "define parameters"
    assert bl[-1][0] == "set solver"
    print("OK: block structure verified.")
