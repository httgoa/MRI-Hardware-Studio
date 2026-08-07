# CST Red Lines (MRI)

Rules that protect correctness, source projects, and CST session stability. Do not violate.

## Project Safety

- Do not overwrite the user's source `.cst`. Work on a copied project unless explicitly told otherwise.
- When copying a `.cst`, copy its **companion folder** too (results/metadata live beside it).
- Inspect an existing/open project before writing (run `probe_project.py`).
- If multiple projects are open and the target is ambiguous, stop and ask.
- Save before every solve.
- Report `.lok` locks or cleanup/access-denied residuals; do not hide them.

## Session and Process Safety

- "MCP server alive" and "CST project usable" are separate states.
- Do not assume a project is loaded just because CST is running.
- Prefer the async solver pattern (`start_solver` + poll `is_solver_running`/`get_solver_run_info`) over blocking `cst_run_solver_tool` for 3D solves — blocking risks a tool timeout.
- Keep modeling operations and result-reading operations separate when the tooling separates them.
- **Keep exactly one live MCP server.** A pile of zombie `mcp_server.py` processes from prior sessions saturates the API channel — updates/exports then silently fail or hang. Before API work, kill old duplicates, keep only the latest pair.
- **NEVER launch a standalone `cst.interface` / `win32com` COM client while the MCP server holds the connection.** The second client competes for the same COM channel and blocks indefinitely (freezes at `connect()`/`active_project()`, no error). Do everything through MCP tools or in-process VBA (`cst_execute_vba_tool`). This is the single most common "it just hangs" cause.
- Export 3D fields through `cst_execute_vba_tool` (in-process VBA), not a separate COM script.

## Schematic / Circuit (field-circuit co-simulation)

- **Series element must span two different nets** (pin0 → incoming net, pin1 → new net to the load). Both pins of a series L/C on the SAME net = short circuit = matching silently has NO effect. Shunt elements go between a rail node and GND. See `../recipes/build/smith-matching.md` and `../building-blocks/vba-blocks/dipole-schematic.md`.
- **`Externalport` casing is literal**: exactly `"Externalport"` (capital E, lowercase everything else including the `p`). Never `.upper()`/`.lower()` it — the connection fails silently.
- **Do not reuse a polluted `Externalport`.** A port repeatedly hit with `Net.Delete` refuses new connections. Delete and recreate it instead of cleaning it.
- **Refresh circuit/AC tasks with `SimulationTask.Update()`, never `RunAndWait()`** (the latter crashes on Chinese solver stdout with `UnicodeDecodeError`). The prior solve caches under `run_id=0`; `Update()` re-solves.
- Match the real block name in `blocknameforcombineresults` (e.g. `MWSSCHEM1`); an empty/wrong name makes combine produce nothing.

## Pipeline Correctness (MRI-specific)

- A required stage skipped ≠ optional. Matched/circuit-driven B1+/SAR post-processing needs the **circuit co-sim field `[AC*]`**, not the raw 3D field `[1]`; skipping the AC stage makes `EvaluateResultTemplates` fail with "H-Result not found". Exception: data-prep direct-port complete cases explicitly use source `[1]` and normalize all metrics by measured accepted power.
- Rebuild/save after geometry or parameter changes before solving.
- Add monitors before solving when their outputs are required.

## Numerical Correctness

- S-parameters may be complex. Convert to dB with `20*log10(abs(S))`. Never label raw magnitude as dB.
- VSWR uses reflection-coefficient magnitude, not dB.
- **Antenna gain = `Realized Gain` / `Gain` / `Directivity` result — never report `Abs(E)` (raw E-field magnitude) as gain.** They are different quantities.
- **B1+ is the circular-polarized transmit component `(Bx + i·By)/2`, NOT `|H|` or `|B|`.** Use CST's "B1+ and B1-" result, not raw field magnitude.
- Report B1+ in µT (CST field export is Tesla → ×1e6). State the plane/ROI.
- **When deriving B1+ from an exported H-field yourself**, match the sign convention to `b0_plus_z`: B0 along +z ⇒ `(Hx − i·Hy)/2`. Getting the sign wrong swaps B1+ and B1−. See `../scripts/compute_b1plus.py`.
- **CST HDF5 field export is a structured numpy array, NOT a group.** `f["H-Field"]` has fields `x/y/z` each with `re/im`, shape `(Nz, Ny, Nx)` in **Fortran order**. Read `f["H-Field"]["x"]["re"]` and `reshape(..., order="F")`. Calling `.keys()` on it or reshaping `order="C"` corrupts the data. See `../building-blocks/vba-blocks/field-export.md`.
- **`cst_list_results_tool` returns 1D results only** — it cannot confirm a 3D field node exists. Confirm 3D fields with a VBA `SelectTreeItem` probe or `cst.results...get_3d().get_tree_items()`.
- SAR must state the averaging mass (10 g vs 1 g) and units (W/kg); needs a power-loss monitor + lossy tissue.
- Resonance = frequency of minimum S11 or an eigenmode entry — read from data, do not eyeball.
- State frequency units explicitly. Do not claim convergence/pass/fail/optimality without evidence.

## Solver Setup

- Use the solver appropriate to the task: HF Frequency Domain for narrowband/high-Q loaded MRI coils; HF Eigenmode for mode frequencies; Time Domain for broadband.
- Do not blindly set frequency range for every solver (eigenmode may not need `Solver.FrequencyRange`; setting it unset can open an interactive dialog).

## Reporting

- Do not fabricate solver status, mesh counts, S11, resonance, B1+/CV, or SAR.
- Include exact result paths and result-tree items as evidence.
- Mark incomplete extraction as `needs_validation` or `partial`, not success.
- Record defaults/assumptions and any resolution limitations (e.g. coarse export grid distorting CV).

## Automation Scope

- Prefer existing MCP tools + recipes over new ad-hoc scripts. The stable scripts are `probe_project.py`, `plot_field.py`, `plot_b1_profiles.py`, and `compute_b1plus.py` (HDF5 H-field → B1+).
- Use small named VBA/history blocks with clear titles.
- Save figures/reports/data into an auto-named results subfolder, not the shared results root.

## On errors and unknown APIs: consult docs, do not guess (iron rule)

Any of these must trigger a docs lookup BEFORE the next call:
- VBA / Python error: "Method or property not found", "wrong number of parameters", "&H8000ffff …", "Unable to …"
- MCP tool call fails with `InputValidationError` / unknown parameter name
- About to use an object.method you can't cite from a doc or `dir()` line
- Repeated fix attempts on the same error (>1 retry = STOP and read)

Order of lookup:
1. `external/CST-MCP/vendor/cst-runtime-cli/devkit/references/cst-official-api-reference.md` (Python)
2. `external/CST-MCP/vendor/cst-runtime-cli/devkit/references/vba-official-reference.md` (VBA)
3. `external/CST-MCP/mcp_server.py` — grep the tool function to see actual keyword args + defaults
4. Runtime `dir(obj)` via `cst_run_python_tool` for the exact method surface
5. CST Online Help HTML → extract with `references_cases/_tools/htm_text.py`
6. Existing memory (`mcp-repro-pitfalls.md`) for known traps

**Fabricated API names cost real time.** Historical examples that were preventable by this rule:
`FarfieldPlot.GetValue`, `Plot.CaptureCurrentPlot`, `Port.GetNumberOfPorts`, `Net.StartNameIteration`, `Block.GetPinPosition`. Each cost 5–20 min of dead-end debugging + zombie state cleanup.

**Never fabricate**: if the API name comes from intuition rather than a doc line or `dir()` result, add "首次使用、可能失败" to the plan and validate with a minimal probe call — don't chain 5 speculative calls into a big block.
