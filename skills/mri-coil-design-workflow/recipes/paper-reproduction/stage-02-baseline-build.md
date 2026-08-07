# Stage 02 · Reference-Configuration Build — Build & solve the paper's reference config(s)

**Goal**: Prove the CST translation of the paper's geometry works by building the paper's **reference configuration** and getting a sanity-check B1+ (and S11 IF the device is a driven port). "Reference config" = the paper's canonical/optimal design for a `driven-port` paper; for a `passive-structure-with-external-coil` paper it's usually **two builds** (with-structure and without-structure), since the paper's claim is the *difference*.

**Read `01_paper_spec.md` `excitation_model` and `paper_type` first** — they decide how many builds and whether S11 applies.

## Inputs
- `stages/01_paper_spec.md` — the reproduction contract
- **The artifact-first pipeline (how modeling is built): `../../driving/artifact-pipeline.md`** —
  generate (Tier A render / Tier B few-shot) → L0 lint → L1 batch → L2/L3/L4 error
  ladder. This REPLACES the old "drive CST live, block by block" method below.
- Pipeline scripts: `../../scripts/render_templates.py` (Tier A ①),
  `../../scripts/prepare_tierb_gen.py` (Tier B ①), `../../scripts/lint_vba.py` (L0),
  `../../scripts/batch_execute.py` (L1), `../../scripts/apply_error_fix.py` (L2),
  `../../scripts/prepare_l3_repair.py` (L3); `../../pitfalls/error-fixes.md` (L2 table);
  `../../templates/*.vba.j2` (Tier A); `../../building-blocks/vba-knowledge/*.md` (Tier B seeds)
- Existing skill VBA blocks (reference for parameter values): `../../building-blocks/vba-blocks/dipole-build.md`,
  `../../building-blocks/vba-blocks/dipole-schematic.md`, `../../building-blocks/vba-blocks/field-export.md`
- Skill red-lines: `../../foundations/cst-red-lines.md`, `../../pitfalls/mcp-pitfalls.md`

## Method

1. Read `01_paper_spec.md`. Identify the reference config(s):
   - `driven-port` → the paper's canonical/optimal config (e.g. dipole length = 30 cm for Fractionated Dipole). Usually ONE build.
   - `passive-structure-with-external-coil` → usually TWO builds: driving-coil-alone and driving-coil-plus-structure (the paper's claim is the delta).
2. **Solver choice — CONDITIONAL (do NOT default to one solver)**:
   - **IF `requires_sar: true`** → **HF Time Domain hexahedral** (native 10g SAR only exists on hex; see `../../pitfalls/mcp-pitfalls.md` #18 + `../../foundations/cst-simulation-sop.md` B.1). Set a uniform `SteadyStateLimit` (−30 dB for high-Q mismatched cases, #25).
   - **ELSE** (only B1+ / S-params / narrow-band field) → pick by physics: HF FD Tet 2nd order is fine for narrow-band lossy loads (validated in dipole/patch repro).
3. **Build the model with the artifact-first pipeline** (`../../driving/artifact-pipeline.md`) —
   NOT live block-by-block. This is OFFLINE (no CST) until the batch execute step:
   1. **Classify each step → Tier A/B/C** (`../../driving/artifact-pipeline.md` §1). Standard step
      order: `parameters → setup(units/background/boundary) → materials → geometry
      → ports → monitors → solver`. Map to tiers:
      - **Tier A** (deterministic render, zero LLM): setup, materials, ports, monitors,
        solver, and any geometry a `templates/*.vba.j2` already covers (dipole).
      - **Tier B** (few-shot single-shot): a NOVEL geometry no template covers
        (birdcage, loop, saddle, passive metasurface). Use `prepare_tierb_gen.py`
        (verified 2026-07-20 on birdcage) — it deterministically selects the
        `../../building-blocks/vba-knowledge/*.md` + `../../notes/` decision refs + pitfall constraints; the
        subagent makes ONE generation call; `finalize_tierb_block` lints + writes it.
      - **Tier C** (agent reasoning): genuine design decisions only — NOT procedural VBA.
      > Warning: do NOT render `templates/birdcage.vba.j2` as Tier A — it is DEPRECATED
      > (structurally incompatible; see its header banner). Birdcage geometry = Tier B.
   2. **Frequency/units live ONCE in the manifest `globals`** (`../../driving/artifact-pipeline.md`
      §2.2 IRON RULE) — the paper's Larmor freq, `freq_min/freq_max`, `units_frequency`.
      This is where a paper's frequency enters; it flows into setup+monitors+solver so
      it cannot drift (the MHz-vs-GHz 1000× bug). The renderer's freq-gate refuses to
      emit if a monitor freq falls outside the sweep band.
   3. **Generate** all `.bas` OFFLINE → `results/<project>/artifacts/<step>/*.bas`:
      Tier A via `render_templates.py --manifest <build_manifest.json>`; Tier B via
      `prepare_tierb_gen.py` + one generation call + `finalize_tierb_block`.
      - `define ports` — ONLY for `driven-port` (`../../pitfalls/mcp-pitfalls.md` #15 if differential).
        A passive structure has no port of its own — the driving coil carries the port.
      - boundaries default `expanded open`; `set monitors` = h-field always,
        loss/powerloss ONLY if `requires_sar`; solver per step 2 (minimal setters, #11).
   4. **L0 lint**: `python lint_vba.py --fix results/<project>/artifacts` → resolve any
      ERROR before touching CST (zero LLM, zero CST).
4. Create the CST project + **execute the artifacts (L1)**:
   - `cst_new_project_tool(project_type="mws")` → `cst_save_project_tool(path=<abs>)`
   - Send `batch_execute.py` ONCE via `cst_run_python_tool` (open with `encoding="utf-8"`)
     and call `run_blocks(project, de, BLOCKS, quiet=True)` — the per-block loop lives in
     the script, the LLM is NOT in the loop. It returns one structured table.
   - **On a failed block → walk the error ladder** (`../../driving/artifact-pipeline.md` §6), cheapest
     first, resume from checkpoint: **L2** `apply_error_fix.try_l2_fix(result, BLOCKS)`
     (deterministic patch of the failing `.bas` against `../../pitfalls/error-fixes.md`, e.g. F1/F2/F4/F10,
     zero LLM) → if no match, **L3** `prepare_l3_repair.prepare_l3_context(result, BLOCKS)`
     (deterministic ref selection + ≤2 retry budget; the subagent rewrites ONLY that one
     block) → **L4** surface to user with the checkpoint intact. After any fix, resume:
     `run_blocks(..., start_index=result["failed_index"])`.
5. Save → async solve → poll (TD first-solve may drop volume fields → re-solve guard, `../../pitfalls/mcp-pitfalls.md` #23):
   ```
   project.save(); model3d.start_solver()
   # poll model3d.is_solver_running(); if h-field node missing, start_solver again (≤3×)
   ```
6. Sanity check on the result tree:
   - `cst_list_results_tool(module="3d")` — confirm expected nodes exist
   - **S11 ONLY IF `driven-port`**: read S11 at paper freq via `cst.results.ProjectFile(path, allow_interactive=True)` — is |S11| plausibly matched or resonant? (A passive-structure paper has no S11 to check.)
   - Read peak B1+ from a quick HDF5 export (small box, step 2mm; export H BEFORE any SAR.Create, #24) → `compute_b1plus.py --norm-1w`

## Do NOT
- Do NOT run parameter sweeps here. This stage is the reference config(s) only.
- Do NOT try to tune matching. Reference config may not be 50Ω-matched; that's fine (FoM normalizes to accepted power — see Stage 03). We just record what we get.
- Do NOT re-open the source case files (all read-only textbook cases stay untouched).
- Do NOT force S11 on a passive-structure paper — it has no port of its own.

## Verification gate (BLOCKING — this is the highest-value check in the pipeline)

Before returning, compare the sanity-check B1+ (and S11 if driven) against the **baseline anchor** in `01_paper_spec.md`:
- **If within ~order-of-magnitude of the paper anchor** → `verification.gate: pass`, proceed.
- **If off by ≳10×** → `verification.gate: FAIL`, set `status: blocked`, write what's suspected (units mm/GHz? normalization? port type? monitor missing?) and **STOP** — do NOT let the main loop dispatch Stage 03. Sweeping N configs on a broken baseline wastes the whole sweep.
- The main loop checks `verification.gate` before dispatching Stage 03.

## Handoff — write `stages/02_baseline_build.md`

Template:
```markdown
---
stage_id: 02_baseline_build
status: passed | partial
project: <project_id>
inputs:
  - stages/01_paper_spec.md
outputs:
  - results/<project>/<project>.cst
  - results/<project>/log/baseline.h5
  - results/<project>/log/S11.csv
stats:
  reference_config: {length_mm: 300, feed_gap_mm: 2, ...}
  solver: <HF TD Hex | HF FD Tet>       # per requires_sar
  freq_mhz: 298
  s11_at_freq_db: <val | null if passive-structure>
  peak_b1p_in_phantom_ut_per_sqrtW: <val>
  peak_position_mm: [x, y, z]
  mesh_cells: <N>
  solve_time_s: <t>
verification:                           # B6 gate — main loop reads this before dispatching Stage 03
  gate: <pass | FAIL>
  anchor_used: "<paper Fig/Table + value>"
  our_value: <val>
  agreement: "<within order-of-magnitude | off by ~Nx — suspected cause>"
handoff_hash:
  history_block_titles: [set units and boundary, build geometry, define ports, ...]
  artifacts_dir: results/<project>/artifacts        # the generated .bas set (reuse in Stage 03)
  build_manifest: results/<project>/artifacts/build_manifest.json
  step_tiers: {geometry: B, setup: A, ports: A, monitors: A, solver: A}
  error_ladder_hits: []      # e.g. [{step: geometry, layer: L3, error: "...", fixed: true}] — honest record
  export_box_mm: [xmin, xmax, ymin, ymax, zmin, zmax]
  grid_step_mm: 2
---

## What this stage did
Built the paper's canonical config in CST + solved + sanity-checked B1+.

## Key decisions / assumptions
- Solver choice: <HF FD Tet | HF TD Hex>, reason: <...>
- Boundary: ...
- Port: ...

## Blockers / warnings
- ...

## Sanity check vs paper anchor
Paper says (Fig X): B1+ peak ≈ <paper_value>. We got: <our_value>.
Agreement: <good | order-of-magnitude | off by factor ~N — investigate>.

## What downstream needs from this
- Stage 03 will vary <param> from spec; the baseline config is at `<param>=<canonical>`
- Grid step + export box: reuse `handoff_hash` above
```

## Return value to main loop
3–5 lines: canonical config, freq, S11 dB, B1+ peak, agreement w/ paper anchor.

## Common pitfalls
- **Most procedural pitfalls are now caught OFFLINE by the pipeline** — you should not
  re-derive them by hand: solver version-mismatch setters (#11) = **L2 F4**; reserved
  param names (#1) = **L0 lint + L2 F1**; schematic coord offset = **L2 F10**;
  StoreDoubleParameter wiping results (#2) = **L2 F2**. Let L0/L2 handle these; only
  reason live when the error is NOT in `error-fixes.md` (→ L3).
- `cst_save_project_tool(path=...)` not `save_as_path=` (see `../../pitfalls/mcp-pitfalls.md` #10).
- Save before solve; use async solver + poll pattern; TD first-solve drops volume fields → re-solve guard (#23).
- If `requires_sar`: export H-field BEFORE any SAR.Create (#24); the whole per-case timing is in `../../foundations/cst-simulation-sop.md`.
- Warning — **COM zombie handle** (`../../pitfalls/mcp-pitfalls.md` #18): if any MCP call (even read-only
  `cst_detect`) hangs/times out, CST likely crashed and MCP holds a dead COM handle —
  do NOT keep retrying `connect`; restart the MCP server (`/mcp`), then reconnect to the
  new PID and resume from the checkpoint (artifacts are on disk).
