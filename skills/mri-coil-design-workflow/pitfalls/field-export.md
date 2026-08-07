# Pitfalls — 3D Field Export

Nearly all 3D field (H/E/SAR) export traps come down to "session timing" and "storage format". Rule version: `foundations/cst-red-lines.md`; SAR-specific traps: `sar.md`.

### Warning: results live in Storage.sdb; fields only materialize to .m3d inside the "post-solve in-memory window" (the #1 gotcha)
- **Symptom**: `Result3D("<name>")` reports "file does not exist"; `SelectTreeItem`/`ASCIIExport` reports "not available for current view"; after close→reopen even the H-field becomes unselectable/unexportable.
- **Root cause**: CST 2024 by default packs fields into `Result/Storage.sdb` and does **not** materialize a `.m3d` on disk. But `Result3D`/`ASCIIExport` need a real on-disk `.m3d`. Fields only materialize to `.m3d` inside the **same in-memory session right after solving** (and during GUI interaction); once you close→reopen or run certain post-processing bare, the `.m3d` gets archived back into Storage.sdb.
- **Workaround**: do ALL 3D field exports (H/E/SAR) **in one pass, inside the same fresh post-solve session**, in order H-field → SAR field → P_acc, **without reopening or opening another project in parallel**. If you must export fields from a reopened old project → **re-solve first** (re-solving re-materializes `.m3d`).
- **Origin**: cracked during the ind150 case (2026-07-16). Full detail: `recipes/b1-sar/sar-field-export.md` §0.

### All-zero field export trap (coordinates correct, field columns all 0)
- **Symptom**: immediately after `start_solver`/`cst_run_circuit_cosimulation_tool` completes, doing ASCIIExport in the same background COM session writes a file with **correct coordinate columns but all-zero field columns** (both HDF5/ASCII hit this, `err=0`, no error raised); yet loading the same `.m3t` via `Result3D.Load` returns full non-zero data.
- **Root cause**: the export buffer/tree hasn't refreshed yet; at this point `SelectTreeItem` returns `err=0` for any path (not trustworthy).
- **Workaround**: `project.save()` → `project.close()` → `de.open_project(fn)` → `cst_active_project_tool` to make the MCP rebind the active project, then ASCIIExport becomes non-zero. Prefer `Result3D.Load` over the exported file to check for all-zero data. (`de` has no `close_project`; use `project.close()`.)
- **Origin**: confirmed empirically 2026-07-15.

### Export must happen before SAR.Create
- **Symptom**: calling `ASCIIExport.Execute` after computing SAR reports "The ASCII export option is not available for the current view".
- **Root cause**: `SAR.Create` changes the active view.
- **Workaround**: fixed order — **solve → re-solve guard → export H-field → THEN compute SAR**.
- **Rule anchor**: → red-lines "Pipeline Correctness".

### CST HDF5 fields are structured numpy arrays, not groups
- **Symptom**: calling `.keys()` or `reshape(order="C")` on `f["H-Field"]` yields corrupted data.
- **Root cause**: CST HDF5 field export is a **structured array**: `f["H-Field"]["x"]["re"]`, shape `(Nz,Ny,Nx)`, **Fortran order**.
- **Workaround**: read `f["H-Field"]["x"]["re"]` and `reshape(..., order="F")`. SAR is a real scalar field, so read `f["SAR"]` directly (no re/im substructure). See `building-blocks/vba-blocks/field-export.md`.
- **Rule anchor**: → red-lines "Numerical Correctness".

### ASCIIExport syntax essentials
- `.Reset` always goes first (stale options leak across calls); `.Mode "FixedWidth"` + `.Step 1/2` (physical mm, NOT the old `FixedNumber` per-axis point count); `.ExportCoordinatesInMeter False` (keep mm); a trailing `.Execute` is mandatory (otherwise no file, no error). `SelectTreeItem` paths vary with CST version/task suffix — loop over a candidate list and take the first success.
- Standard comparison plots: full domain + `.Step 2` (2mm), no subvolume; shallow quantitative work: phantom subvolume + `.Step 1` (1mm); put 1D profile lines inside the phantom (avoid landing on a PEC plane — metal-edge singularity oscillations).

### cst_list_results_tool can't see 3D fields
- **Symptom**: using `cst_list_results_tool` to check whether a 3D field exists returns no 3D entries.
- **Root cause**: this tool **only returns 1D results**.
- **Workaround**: probe with VBA `SelectTreeItem`, or `cst.results...get_3d().get_tree_items()`.
