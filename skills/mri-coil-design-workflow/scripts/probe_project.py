#!/usr/bin/env python3
"""
probe_project.py — One-shot reconnaissance of an (unknown) CST project.

Runs INSIDE the CST MCP process via `cst_run_python_tool` (so `project`,
`model3d`, `de` are already in scope). Do NOT run it standalone.

Purpose: replace the ~20 ad-hoc probing calls that happen when facing a
project you did not build. Emits ONE structured JSON summary describing:
  - active project identity + type
  - 3D solver type
  - parameter list (names + expressions)
  - full navigation/result tree (3D + schematic), walked robustly
  - post-processing template result names
  - existing 3D field monitors / field results
  - schematic simulation tasks (best-effort)

Hard-won API notes baked in (so we never re-discover them):
  - Resulttree.GetFirstChildName("") returns "" — must start from a concrete
    node name. GetNextItemName(node) does a DFS *within that node's subtree*.
  - GetParameterNValue throws when a parameter is an expression; read SValue.
  - Mesh.GetNP throws for tet (frequency-domain) solvers — don't probe it.
  - cst.results get_tree_items() lists only 0D/1D items, NOT 3D fields;
    3D fields must be enumerated by walking the nav tree via VBA.

Usage inside cst_run_python_tool:
    exec(open(r"...\\scripts\\probe_project.py", encoding="utf-8").read())
    # `result` is set to the summary dict.
"""

import os
import json
import tempfile


def _tmp_path(tag):
    d = tempfile.gettempdir()
    return os.path.join(d, f"_cst_probe_{tag}.txt")


def _walk_tree(model3d, root, max_items=400):
    """Walk a nav-tree subtree via VBA, return list of full item paths."""
    out = _tmp_path("tree")
    if os.path.exists(out):
        try:
            os.remove(out)
        except OSError:
            pass
    rr = root.replace("\\", "\\\\")
    op = out.replace("\\", "\\\\")
    vba = (
        "Sub Main\n"
        f'Open "{op}" For Output As #1\n'
        "Dim it As String\n"
        f'it = Resulttree.GetFirstChildName("{rr}")\n'
        "Dim n As Long\n n = 0\n"
        f"Do While it <> \"\" And n < {max_items}\n"
        "  Print #1, it\n"
        "  it = Resulttree.GetNextItemName(it)\n"
        "  n = n + 1\n"
        "Loop\n"
        "Close #1\n"
        "End Sub\n"
    )
    try:
        model3d._execute_vba_code(vba)
    except Exception as e:
        return {"_error": str(e)}
    try:
        with open(out, "r", encoding="utf-8", errors="replace") as f:
            return [l.strip() for l in f if l.strip()]
    except OSError as e:
        return {"_error": f"read failed: {e}"}


def probe(project, model3d):
    info = {}

    # --- identity ---
    ident = {}
    for m in ("filename", "folder"):
        try:
            ident[m] = getattr(project, m)()
        except Exception as e:
            ident[m] = f"ERR {e}"
    info["identity"] = ident

    # --- 3D solver ---
    try:
        info["solver_type"] = model3d.GetSolverType()
    except Exception as e:
        info["solver_type"] = f"ERR {e}"

    # --- parameters (expressions; NValue throws on expressions) ---
    params = {}
    try:
        npar = int(model3d.GetNumberOfParameters())
        for i in range(npar):
            nm = model3d.GetParameterName(i)
            # RestoreParameterExpression is the reliable reader (SValue/NValue
            # throw for expression-valued params in this API build).
            try:
                params[nm] = str(model3d.RestoreParameterExpression(nm))
            except Exception:
                try:
                    params[nm] = str(model3d.RestoreParameter(nm))
                except Exception:
                    params[nm] = "<unreadable>"
    except Exception as e:
        params = {"_error": str(e)}
    info["parameters"] = params

    # --- navigation tree (3D roots we care about) ---
    tree = {}
    for root in (
        "1D Results",
        "2D/3D Results",
        "2D/3D Results\\H-Field",
        "2D/3D Results\\E-Field",
        "2D/3D Results\\B1+ and B1-",
        "2D/3D Results\\SAR",
        "2D/3D Results\\Surface Current",
        "Field Monitors",
        "Excitation Signals",
        "Tables\\0D Results",
        "Tables\\1D Results",
    ):
        walked = _walk_tree(model3d, root)
        if walked and not (isinstance(walked, dict)):
            tree[root] = walked
    info["nav_tree"] = tree

    # --- 0D/1D readable items via cst.results ---
    try:
        import cst.results as cr
        pf = cr.ProjectFile(project.filename(), allow_interactive=True)
        r3d = pf.get_3d()
        items = list(r3d.get_tree_items())
        info["n_readable_1d_items"] = len(items)
        info["sparameter_items"] = [i for i in items if "S-Parameters" in i][:20]
        info["b1_table_items"] = [i for i in items if "B1" in i][:20]
        info["sar_table_items"] = [i for i in items if "SAR" in i][:20]
        try:
            rsch = pf.get_schematic()
            sch_items = list(rsch.get_tree_items())
            info["n_schematic_1d_items"] = len(sch_items)
            info["schematic_sparam_items"] = [i for i in sch_items if "S-Param" in i][:20]
        except Exception as e:
            info["schematic_results"] = f"unavailable: {e}"
    except Exception as e:
        info["cst_results"] = f"ERR {e}"

    # --- interpretation hints ---
    hints = []
    st = info.get("solver_type", "")
    if "Frequency Domain" in str(st):
        hints.append("HF Frequency Domain solver → tetrahedral mesh, narrow/high-Q sweep typical.")
    pnames = set(info.get("parameters", {}).keys()) if isinstance(info.get("parameters"), dict) else set()
    if {"Cp", "Ct", "Lp", "Lt"} & pnames:
        hints.append("Has lumped tuning params (Cp/Ct/Lp/Lt) → circuit co-sim (AC task) likely part of workflow.")
    if any("plantom" in p or "phantom" in p for p in pnames):
        hints.append("Has phantom position params → MRI loading present; B1+/SAR analysis meaningful.")
    hf = info.get("nav_tree", {}).get("2D/3D Results\\H-Field", [])
    if any("[AC" in h for h in hf):
        hints.append("H-field [AC*] present → circuit co-sim already run.")
    elif any("[1]" in h for h in hf):
        hints.append("Only H-field [1] present → 3D solved but circuit co-sim (AC) NOT run yet.")
    info["interpretation"] = hints

    return info


# When exec'd inside cst_run_python_tool, `project` and `model3d` are in scope.
try:
    result = probe(project, model3d)  # noqa: F821
except NameError:
    result = {"error": "Run this inside cst_run_python_tool (project/model3d must be in scope)."}
