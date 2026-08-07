# MRI CST Workflow

Task routing and execution order. Use with `mcp-tool-map.md` (tool names) and the recipes under `recipes/`.

## Universal Preflight

1. Confirm the request mode: plan-only, inspect existing, run known pipeline, design from scratch, or modify+re-run.
2. `cst_detect_tool` — verify CST + Python + running instances (see `mcp-setup.md` if it fails).
3. `cst_connect_tool` — connect; `launch_if_needed=true` only when execution is wanted and no instance is running.
4. `cst_project_info_tool` — active/open project + message log (watch for "not writable").
5. Note whether the task is plan-only, destructive, or expensive.

Do not run CST for plan-only tasks — return the workflow, assumptions, expected outputs, and the MCP tools that would be used.

## Inspect Existing / Unknown Project Flow

When the user points at a `.cst` you did not build → follow `recipes/inspect/inspect-unknown-project.md`:
1. Connect and locate the project.
2. If modifying/solving: copy the `.cst` **and its companion folder** to `projects/<name>_run/` (red line: never edit the source), open the copy.
3. Run the one-shot reconnaissance (`scripts/probe_project.py` via `cst_run_python_tool`).
4. Interpret solver/params/tree/hints → decide what pipeline the project supports.
5. Route to the matching task recipe.

Never rebuild an existing project from scratch unless asked.

## Run Known Pipeline Flow

When the project is understood and the user wants a standard analysis → follow the matching recipe, e.g. `recipes/b1-sar/b1-field-pipeline.md`:
1. Copy to a run project if not already on one; save before solving.
2. Execute the recipe's stages (for B1+: 3D solve → circuit AC co-sim → post-processing).
3. Export the requested field(s); run the stable plotting helper.
4. Validate per `result-validation.md`.
5. Save all outputs into an auto-named results subfolder; produce the report.

## Design From Scratch Flow

Build with small named history blocks (see `mcp-tool-map.md` naming): parameters → units/background → materials → geometry → feed port → monitors → solver, then solve; then circuit tuning; then post-processing. For a dipole+phantom this is fully templated in `recipes/build/dipole-from-scratch.md` (with VBA blocks in `../building-blocks/vba-blocks/`). Other coil types (birdcage/surface/array) are later additions — follow the same three-stage structure.

## Modify + Re-run Flow

1. Locate the source `.cst`; copy to a run project.
2. Inspect current parameters/monitors/solver/results.
3. Change only what the user requested (e.g. a tuning capacitor value).
4. Save, re-run the relevant pipeline, re-export, validate, report before/after.

## Data Prep Complete Case Flow

When the user asks for case-matrix records or official complete-case data:

1. Read `recipes/data-prep/data-prep-complete-case.md`.
2. For the current dipole module, read
   `recipes/data-prep/complete-case(D1)/data-prep-complete-case-dipole.md`.
3. Use the colocated module inputs:
   `recipes/data-prep/complete-case(D1)/RD_case_matrix.csv` (regular_dipole),
   `recipes/data-prep/complete-case(D1)/FD_case_matrix.csv` (fractionated_dipole),
   and `recipes/data-prep/complete-case(D1)/record_template_v1.json`.
4. Apply `notes/data_prep/AGENT_BATCH_SIMULATION_PIPELINE.md` as the D1
   project SOP, especially for direct-port `[1]` normalization and native SAR
   HDF5 export.
5. Save outputs under `results_data_prep/<case_matrix_id>/` and update
   `results_data_prep/manifest.csv` last.

## Default Report Shape

Markdown unless the user asks otherwise, saved inside the run's auto-named results subfolder:

- task summary
- source project and working (copied) project paths
- assumptions / defaults used
- MCP tools / stages executed, in order
- parameter table (if changed)
- solver + monitor + post-processing setup
- result file paths (figures, exported data)
- MRI metrics (resonance, S11, B1+ peak/mean/CV, SAR) with units
- validation status
- limitations, issues, recommended next changes
