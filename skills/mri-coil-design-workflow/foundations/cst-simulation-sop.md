# CST Per-Case Simulation SOP (mandatory execution checklist)

The **mandatory per-case timing checklist** for MRI coil EM simulation (geometry/component sweeps, B1+/SAR extraction) \u2014 walk through this before every CST-driving action, for every case. Tiers: **Must / Forbidden / Should**. Violating a "Forbidden" item is known to error out or hang the session.

**Positioning**: this is the timing-ordered index + mandatory checklist for `mcp-pitfalls.md`, and the global per-case SOP for this skill. Project modules may add narrower rules. For data-prep dipole complete cases, read `recipes/data-prep/complete-case(D1)/data-prep-complete-case-dipole.md` and `notes/data_prep/AGENT_BATCH_SIMULATION_PIPELINE.md`; their case matrix, phantom subvolume, direct-port source, record fields, and SAR HDF5 validation rules override generic defaults for that module. Mechanism/root cause: see the corresponding entry in `mcp-pitfalls.md`; hard rules: `cst-red-lines.md`; stage orchestration: `recipes/paper-reproduction/`. Distilled from the FD segmented-dipole reproduction (2026-07-16); \u00a7D.3\u2013D.5 and the \u00a7E trap index table were merged in from the old `sop-simulation-pipeline.md` (2026-07-21 single-file consolidation).

---

## A. Preparation (once per session)

- **Must** `cst_detect_tool` \u2192 `cst_connect_tool` \u2192 `cst_project_info_tool` to confirm the active project.
- **Forbidden** to leave zombie `mcp_server.py` processes running (especially from other envs/workspaces) \u2192 saturates the COM channel, causing all-zero export (`mcp-pitfalls.md` #26). Clean up **precisely** \u2014 don't accidentally kill this session's own server.
- **Forbidden** to start an independent COM client (`cst.interface`/win32com) while the MCP holds its connection \u2192 channel contention deadlock.
- **Must** never overwrite the source `.cst`: copy the `.cst` + companion folder first, then modify; case-id must be unique and never reused (avoids orphaned `.lok` files).

## B. Full pipeline (per case, fixed order, skip no step)

**B.1 Modeling** \u2014 small, named history blocks, in order: parameters \u2192 units/background/boundary \u2192 materials \u2192 geometry \u2192 ports \u2192 monitors \u2192 solver.
- **Must** inject sweep parameters into the `define parameters` block (via `StoreParameter`); **forbidden** to rebuild-append (drops volume-field monitors), **forbidden** to use `StoreDoubleParameter` to store analysis values (deletes run_id=0 results, `mcp-pitfalls.md` #2).
- **Must** define volume-field monitors before solving: h-field (\u2192B1+); **IF SAR is needed** \u2192 add a powerloss/loss monitor (\u219210g SAR).
- **Solver (conditional, not unconditional)**:
  - **IF native 10g SAR is required \u2192 must use HF Time Domain hexahedral** (native 10g SAR only supports hex, `mcp-pitfalls.md` #18); use one `SteadyStateLimit` consistently across the whole sweep (use \u221230dB to speed up high-Q mismatched points, #25; empirical basis in \u00a7D.4).
  - **ELSE (only B1+ / S-parameters / narrowband fields needed) \u2192 choose by physics**: a narrowband lossy load can also use FD Tet 2nd order (verified in the dipole/patch reproductions).

**B.2 Save** \u2014 **Must** `project.save()` before solving.

**B.3 Async solve + guard** \u2014 **Must** use non-blocking `start_solver()` + poll `is_solver_running()`; **forbidden** to use the blocking `cst_run_solver_tool`.
- **Should** abort any leftover solver before solving (an interrupted run leaves a background solver that collides next time).
- **TD's first solve often produces no 3D volume-field monitor \u2192 call `start_solver` again if missing** (guard, up to 3\u00d7, `mcp-pitfalls.md` #23).
- \u26a0\ufe0f `get_solver_run_info()` can misreport `state=ERROR`; trust `is_solver_running()==False` + `messages_tail` instead.

**B.4 Export H-field (after solving, before SAR)** \u2014 **Must** do the H-field ASCIIExport before any `SAR.Create` call (`SAR.Create` changes the active view, after which export reports "not available for current view", #24).
- HDF5 is a structured array (Nz,Ny,Nx) Fortran order; `.Mode "FixedWidth"` + `.Step` (mm); `.ExportCoordinatesInMeter "False"`; `.Execute` is mandatory.
- Exporting via `project.model3d._execute_vba_code` is more stable than the MCP's `cst_execute_vba_tool`.

**B.5 SAR (IF needed, same post-solve window)** \u2014 **Must** use `no rescale` for the scalar `GetValue("max sar")` (reliable); **forbidden** to trust `scale accepted` without a self-check (silently fails on severe mismatch, #20; self-check method in \u00a7D.3).
- SAR **3D field**: data-prep cases must call `export_data_prep_sar10g(...)`, the two-hop helper in `.agents/skills/mri-coil-design-workflow/scripts/export_native_sar.py` (`Result3D(...)` reads the native SAR \u2192 `AddToTree` creates a new node \u2192 `ASCIIExport` on the new node). **Forbidden** to `SelectTreeItem` the default `SAR.Create` node directly (#19); if the helper fails, log the helper error and mark `sar_status=partial` \u2014 don't keep trying the old path; fall back to the GUI if headless hits instability (#22).
- Data-prep D1 uses the project phantom/loss box `[-135,135,-160,160,-120.5,-20.5]` mm and normally labels 210 MHz results as `f=0.21` in CST. Do not use older generic `z=-20..0` SAR profile boxes for D1; an all-zero HDF5 is a failed export, not a valid low-SAR result.
- **Forbidden** to use the E-field proxy `0.5\u03c3|E|\u00b2/\u03c1` to compute the SAR distribution (falsified, #21).

**B.6 Read accepted power (after SAR field export)** \u2014 **Must** read `Power Accepted per Port\Port 1` @freq using `run_ids[-1]`; P_acc\u22640 = failure. **Forbidden** to start a second results client inside the export window (disturbs the window).

**B.7 Extract + normalize** \u2014 **Must** normalize to **accepted power** (not forward power); B1+\u221d1/\u221aP_acc, SAR\u221d1/P_acc; dedupe cases.csv with last-wins.

**B.8 Wrap-up** \u2014 **Forbidden** to batch abort/close (cascades and takes down the whole DE + the user's other projects); switch projects using the order `close()`\u2192sleep\u2192`open_project()`. **Forbidden** to save a contaminated temporary label.

## C. Token control (only applies during the "establish" phase; exempt when "following" an already-verified path)

**The deciding axis is establish vs. follow, not whether the case is new, nor whether "we've done this before".** One-line test:
> **Is there a verified path you can follow step by step with no trial and error?** \u2014 Yes \u2192 follow (exempt from this section); No \u2192 establish (this section applies).

- **Applies (establish)**: the task has **no** existing verified path to follow yet, and requires probing unknown APIs / trial-and-error to get the pipeline working from scratch for the first time.
- **Does not apply (follow)**: exempt whenever an executable, verified path already exists \u2014 **regardless of whether the user is doing it for the first time, and regardless of whether it's an article "we've reproduced before"**:
  - an already-templated recipe (`recipes/build/dipole-from-scratch.md`);
  - demo/recording mode (`recipes/build/demo-recording-mode.md`);
  - **an article that has been reproduced and has a "no-trial-and-error replay" artifact** distilled from it (a complete case note `notes/repro-*.md` + a `state.md`/stage artifact you can follow).
- **Boundary case**: if an article was reproduced before but **left no** followable artifact (only scattered memory), a new user redoing it still counts as "establish", and **this section applies**. The exemption threshold is **the artifact being complete enough to replay with no trial and error**, not "has it been done before".

> Background: empirically (2026-07-16 session audit), about **89% of tokens are spent on "repeatedly resending accumulated context"** (cache read+create); the dominant multipliers are **turn count** and **large resident outputs**, not SKILL size. Audit script: `results/_token_audit/analyze.py`.

- **Should (persist to disk, keep out of context \u2014 strategy 2)**: dumps from your own scripts (`probe_project.py`/`plot_*`/export macros) should always be written to `results/<proj>/log/`; read them back with `Grep`/line ranges, **pulling only the lines you need**; use line ranges with `Read` for large files instead of pulling the whole file into context.
  - **Note**: MCP tool output (`cst_project_info`/`cst_execute_vba`, etc.) is returned directly into context and **cannot be redirected to disk** \u2014 for these, only "call as needed, don't poll repeatedly"; don't treat them as a "persist to disk" target.
- **Should (dedicated subagent for first-time exploration \u2014 strategy 3)**: put trial-and-error for a brand-new case into one `Agent()` sub-context, which reports back only **a 3-5 line summary + one on-disk artifact**.
  - **Forbidden** for the main thread and a subagent to **interleave** `cst_*` calls: the CST MCP has only one COM connection, and interleaved contention will deadlock (`cst-red-lines.md`). Rule = **the subagent has exclusive use of CST for that entire case's interaction; the main thread must not touch CST while it runs**.
  - **Forbidden** to run tasks requiring interactivity/foreground sync (demo milestone pauses, `AskUserQuestion`) inside a subagent \u2014 subagents are stateless and this breaks interactivity.
- **Should (fewer turns \u2014 strategy 1)**: **batch independent read-only probes together** (multiple queries in one call); but **history blocks must stay small and named** \u2014 **forbidden** to cram multiple lumped elements/components into one `add_to_history` block just to save turns (`mcp-pitfalls.md` #7).
  - **Should** cap trial-and-error: after **2-3** consecutive failures on the same API \u2192 stop \u2192 go back to the docs (the iron rule) \u2192 if still stuck, `AskUserQuestion`; **forbidden** to retry indefinitely.
- **Should (inter-stage checkpoints \u2014 strategy 4)**: write state to `results/<proj>/log/state.md` at the end of each stage (current progress / verified blocks / next step); for long tasks, prefer **resuming in a new session** from `state.md` rather than dragging the whole history to the end. Switching sessions is a host-level behavior; the skill only provides the checkpoint landing spot.
- **Forbidden** to copy the entire `With FDSolver/IESolver/Solver` parameter block from an official `.mod` verbatim (may bring in newer-version APIs that pop a blocking dialog, #11) \u2014 only issue the necessary 5-10 setters.

## D. Data-processing correctness

- **D.1 Normalization iron rule**: normalizing by accepted power makes FoM invariant to matching (no per-case matching needed, due to antenna linearity); but **P_acc must be measured per case**, never assume 1W excitation = 1W accepted.
- **D.2 Quantity definitions**: B1+ = the CP transmit component `(Hx\u2212iHy)/2`\u00d7\u03bc\u2080\u03bcr (B0 along +z), in \u00b5T, not |H|; state SAR as 10g/1g + W/kg; S\u2192dB uses `20log10(abs(S))`; read resonance/optimum points from data, never eyeball them.
- **D.3 SAR `scale accepted` fails silently on mismatch (self-check mandatory)**: when a bare port is severely mismatched, CST's `SetOption "scale accepted"` **silently fails** (the return value equals `no rescale`, when it should differ by 1/P_acc). **A self-check is mandatory**: on the same project, the ratio of `GetValue("max sar")` between `no rescale` and `scale accepted` should be \u2248 1/P_acc; if it equals 1, the rescale failed \u2192 switch to manually dividing by the measured P_acc.
- **D.4 Steady-state limit \u221230dB**: large inductance + severe mismatch \u2192 long high-Q ringing \u2192 TD steady-state time explodes (up to 450s at \u221240dB). Switching to \u221230dB: sufficient accuracy for DFT-integrated frequency-domain field monitors (B1+/SAR distribution) (residual 0.1%, FoM ratio even more stable since it's self-referential); measured 450s\u2192228s on ind150, \u221240 vs \u221230 FoM difference <1.5%. **Use one consistent steady-state limit across the whole sweep.**
- **D.5 Plotting conventions**: plot SAR longitudinal profiles at **absolute @1W values**; **forbidden** to normalize each line by its own peak (the peak height itself is physical \u2014 capacitors raise SAR, inductors lower it; self-normalizing erases this). Paper-style panels: (a) absolute depth profile; (b) relative to a reference antenna; (c/f) vs. the swept variable, optionally self-normalized per depth to show "relative optimum"; (d) SAR longitudinal profile identifying single/double peaks. Depth axis 0-20cm with 5cm ticks, high-contrast discrete colors.
- **D.6 Data-prep D1 native SAR HDF5**: validated status requires both scalar and spatial checks: HDF5 has `SAR` + `Mesh line x/y/z`, `SAR.max()>0`, and raw HDF5 max matches no-rescale `GetValue("max sar")` within 5%; then divide by measured `P_acc` for @1W accepted metrics and generate SAR depth profile + 48x48 slices.

## E. Risks and warnings (trap index table)

> Every entry has actually been hit. **Detailed mechanism + workaround + origin are in the corresponding `pitfalls/` file** (this table only gives a one-line symptom + pointer, to avoid duplication).

| # | Symptom (one line) | See |
|---|---|---|
| E.1 | 3D field (H/E/SAR) export reports "file does not exist" / "not available for current view"; after reopening, even the H-field becomes unselectable | `pitfalls/field-export.md` (Storage.sdb materialization window); SAR-specific: `pitfalls/sar.md` |
| E.2 | After `SAR.Create`, `SelectTreeItem` on the SAR node = False, tree enumeration collapses | `pitfalls/sar.md` (use Result3D.Load+AddToTree instead; `scripts/export_native_sar.py`) |
| E.3 | Using the E-field proxy `0.5\u03c3\|E\|\u00b2/\u03c1` for SAR \u2192 distribution is the opposite of reality, no double peak | `pitfalls/sar.md` (banned, use the native field) |
| E.4 | A read immediately following a write returns stale data; `cst_list_results_tool` can't see 3D fields | `pitfalls/field-export.md` |
| E.5 | Series element short circuit / AC Combine `"*"` popup / RunAndWait crash / `Externalport` casing | `pitfalls/schematic-cosim.md` |
| E.6 | Mysterious hangs, results going empty, CST crashing (COM contention / zombie server / batch close) | `pitfalls/session-stability.md` |
| E.7 | TD first solve drops volume fields / steady-state limit / hexahedral SAR constraint / eigenmode frequency dialog | `pitfalls/solver-meshing.md` |
| E.8 | scale-accepted failing on mismatch / B1+\u2260\|H\| / dB conversion / normalize by accepted power | `pitfalls/numerical.md` + `pitfalls/sar.md` |

**Sticking to the \u00a7B order during execution (H-field\u2192SAR field\u2192P_acc, no reopening within the same post-solve session) avoids most triggers of E.1-E.4.**

## F. Per-case self-check list

- [ ] Solver chosen as required (SAR needed \u2192 TD hex + consistent steady-state limit; otherwise chosen by physics)
- [ ] Volume-field monitors complete / TD first-solve missing fields already re-solved
- [ ] H-field exported before `SAR.Create`
- [ ] SAR 3D field uses the `export_native_sar.py::export_data_prep_sar10g` two-hop helper (no reopen); helper result already logged; the default `SAR.Create` node was not selected directly; D1 used subvolume `[-135,135,-160,160,-120.5,-20.5]`; scalar scale-accepted has been self-checked when used (\u00a7D.3)
- [ ] P_acc read via run_ids[-1] @freq, after SAR export, >0
- [ ] Normalization correct, no E-proxy used
- [ ] SAR peak \u2248 GetValue("max sar")@1W (<5%)
- [ ] cases.csv deduplicated, no temporary label saved
