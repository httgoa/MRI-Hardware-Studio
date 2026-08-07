# Field Export — Tier B reference (SelectTreeItem + ASCIIExport)

Getting a 3D field (H / E / B1+) out of CST to a file for Python post-processing.
The **verified** macro, option table, and export traps are in
`../vba-blocks/field-export.md`; this is the generalized Tier-B summary. The
deterministic templated version is `templates/field_export.vba.j2` (kind=macro —
run via `cst_execute_vba_tool`, NOT `add_to_history`).

## Which node
- **Raw H-field** `h-field (f=0.21) [AC1]` → export complex Hx,Hy,Hz; compute
  `|B1+| = μ0·|Hx − i·Hy|/2` with `scripts/compute_b1plus.py`. Most robust — no B1+ tree node needed.
- **B1+ node** (after `cst_calc_b1_field_tool`) `B1+ and B1-\B1+ (f=0.21) [AC1]` → already scalar, just visualize.

## The pattern (why it's a macro, not a history block)
1. Iterate a **candidate list** of tree paths (version/suffix vary: with/without
   `2D/3D Results\`, with/without ` GHz`) — take the first that `SelectTreeItem`s
   with `Err=0`. Log which won.
2. `ASCIIExport`: `.Reset` first → `.SetfileType "hdf5"` → `.Mode "FixedWidth"` →
   `.Step 1` (or 2 mm) → optional `.UseSubvolume`+`.SetSubvolume` (mm ROI) →
   `.ExportCoordinatesInMeter False` → `.Execute` (REQUIRED).

## Key traps (pitfalls #19/#24/#26; F9)
- Export the field **BEFORE** any `SAR.Create` (it changes the active view →
  "not available for current view").
- One statement per line (no colon `:`) in MCP-sent VBA.
- `.ExportCoordinatesInMeter False` → keep mm; else coords come out ~0.001×.
- `cst_list_results_tool` lists 1D only — confirm 3D nodes with a `SelectTreeItem` probe.
- All-zero export with no error → zombie-process COM saturation (pitfall #26); prefer `Result3D.Load(...).GetArray(...)`.

Full macro + option table + verify checklist: `../vba-blocks/field-export.md`.
