# Stage 03 · Evaluate Configurations — shape depends on `paper_type`

**Goal**: Reproduce the paper's core evaluation. The SHAPE of this stage is set by `paper_type` in `01_paper_spec.md` — **do NOT assume it's always a sweep**:

| `paper_type` | Stage 03 shape |
|---|---|
| `optimization-sweep` | Loop over the sweep space, extract metric-vs-param, identify the paper's optimum by `metric_criterion`. (Fractionated Dipole: length + lumped sweeps.) |
| `single-design-demo` | ONE characterization run of the reference design (no loop). Extract the paper's reported quantities; skip "optimum" logic. |
| `comparison` | Run each discrete design (e.g. A / B / none), tabulate the compared metric, no continuous sweep or optimum. |

Read `01_paper_spec.md` `paper_type` + `metric_criterion` FIRST. The rest of this recipe details the `optimization-sweep` case (the most complex); the other two are strict subsets (fewer solves, no optimum-picking).

## Inputs
- `stages/01_paper_spec.md` — paper_type, sweep space (if any), metric_criterion
- `stages/02_baseline_build.md` — proven-working reference build (check `verification.gate: pass`);
  reuse its `handoff_hash.artifacts_dir` + `build_manifest` + solver choice
- The .cst project from stage 02
- The artifact-first pipeline (`../../driving/artifact-pipeline.md`) — Stage 03 reuses the SAME
  generated `.bas` set; a swept point changes ONE value, re-rendered/re-executed the same way.

## Prerequisite check
- **Confirm `stages/02_baseline_build.md` has `verification.gate: pass`.** If it's `FAIL`/`blocked`, STOP — the baseline is broken, sweeping is wasted. (The main loop should not have dispatched you, but double-check.)
- **Solver = same as Stage 02** (conditional: TD-hex if `requires_sar`, else per physics). Don't switch solver mid-pipeline.

## Normalization principle (UNIVERSAL — the physics that removes per-case matching)
Both numerator and denominator of any transmit-efficiency FoM are normalized to **1 W accepted power**, measured per case:
- Antenna is linear → fixed accepted power ⇒ fixed feed current ⇒ fixed current distribution ⇒ B1+ and SAR distributions are determined by geometry+load ALONE, independent of the feed network.
- Therefore **no per-case matching is needed**: "per-config match + forward-power norm" ≡ "no match + accepted-power norm". This decouples the swept variable from matching.
- **Iron rule**: measure P_acc per case (`1D Results\Power\Excitation [1]\Power Accepted per Port\Port 1` @freq via `run_ids[-1]`). NEVER assume 1 W stimulus = 1 W accepted (a bare dipole can be 0.00025–0.5 W accepted — a 2000× spread). B1+∝1/√P_acc, SAR∝1/P_acc.
- The **FoM formula itself is paper-specific** (`metric_criterion` from spec, e.g. `B1+/√SARmax at 10cm`). This principle is universal; the formula is not — do NOT hardcode a default formula.

## Method — the compression-critical stage

**This stage does the most solves and thus the most raw log traffic.** Keep everything except the summary tables OUT of the artifact:

1. **Confirm sweep plan** from `01_paper_spec.md`. If the plan is large (>10 solves), consider:
   - **Trial mode** first: 3 values only, spanning the range (e.g. 5, 25, 45 cm for length) → confirm pipeline before committing to full sweep
   - After trial passes, either extend to full sweep or note "trial-only" in artifact and let the user decide

2. **For each sweep point** (follow `../../foundations/cst-simulation-sop.md` B.3–B.7 for the exact per-case timing):
   - **Update the swept parameter — two cases (pick by whether topology changes):**
     - **Pure scalar, no topology change** (a defined CST parameter like a length/gap that
       history expressions reference): `StoreParameter` (VBA) or the schematic Block
       property, then Rebuild. **Do NOT use `StoreDoubleParameter` for analysis values**
       (wipes run_id=0 results, `../../pitfalls/mcp-pitfalls.md` #2 = L2 F2).
     - **Topology / geometry change** (segment count, element presence, a Tier-B-generated
       block): **re-render/regenerate that ONE step via the pipeline** — bump the value in
       `build_manifest.json` `globals`/step params and re-run `render_templates.py` (Tier A)
       or re-generate the Tier-B block, then `lint_vba.py --fix`, then batch-execute just
       that block. This keeps the swept build reproducible from the manifest and keeps the
       artifact set the single source of truth (no drift between the .cst and the artifacts).
   - Re-solve (async); TD first-solve may drop volume fields → re-solve guard (#23)
   - **Export H-field BEFORE any SAR.Create** (#24). If `requires_sar`: SAR scalar via `no rescale` + self-check `scale accepted` (#20); SAR 3D field via `export_native_sar.py` two-hop (#19/#22)
   - Read accepted power per case (`run_ids[-1]` @freq) — normalize B1+∝1/√P_acc, SAR∝1/P_acc
   - Extract only the summary numbers: (S11 if driven-port), peak B1+ in phantom @1W, peak SAR @1W if computed, P_acc, solve time
   - Save the full HDF5 (if B1+ export needed) to `log/<param>_<value>.h5`
   - DO NOT save every solver message tail to the artifact — reference the CST log path if needed

3. **After the loop**, build a summary table (one row per solve, all in the artifact). Columns depend on the paper's metric — e.g.:
   ```
   | length_cm | P_acc_W | peak_B1p_uT | peak_SAR10g | <metric_criterion> | solve_s |
   ```

4. **(optimization-sweep only)** Identify the optimal point by the spec's `metric_criterion` (NOT a hardcoded formula) and note it prominently.

5. **Compare to paper's reported optimum / values**. Report agreement / discrepancy.

## Trial mode vs full mode

For the first paper being tried on this pipeline, start with **trial mode** (3 sweep points, or 3+3 if two dims). Rationale:
- Validates that stage boundary is right-sized (subagent shouldn't run out of context)
- Validates artifact schema captures enough
- Catches solver setup bugs before wasting time on 24 solves

If trial passes cleanly, either:
- Extend to full sweep in the SAME stage (if context budget allows)
- OR mark `status: partial` in the artifact with `notes:` explaining trial-only, let user OK expanding

## Do NOT
- Save all 24 exported HDF5 to the artifact. Reference paths only.
- Paste solver message tails from 24 runs into the artifact.
- Run more than 30 solves in one subagent — if paper needs more, split into two Stage 03 subagents (03a, 03b).

## Handoff — write `stages/03_sweep_results.md`

Template:
```markdown
---
stage_id: 03_parameter_sweep
status: passed | partial
project: <project_id>
inputs:
  - stages/01_paper_spec.md
  - stages/02_baseline_build.md
outputs:
  - results/<project>/log/sweep_<param>_*.h5  (glob)
  - results/<project>/log/sweep_summary.csv
stats:
  paper_type: <optimization-sweep | single-design-demo | comparison>
  solver: <HF TD Hex | HF FD Tet>
  sweep_dim: <param name | "none">
  n_solves: <N>
  metric_criterion: "<from spec, verbatim>"       # NOT a framework default
  optimum_param_value: <val | null if not optimization-sweep>
  optimum_metric_value: <val | null>
  paper_reported_optimum: <val | null>
  agreement: "matches paper" | "differs, see notes"
verification:                                       # soft gate — flag but don't block
  optimum_matches_paper: <yes | no — bug or real discrepancy?>
notes: "trial-only, 3 of planned 9 points" | ""
---

## Sweep summary table
(inline, ≤30 rows; if >30, reference sweep_summary.csv only)

## Optimum
- Our optimum: <param>=<val>, <metric>=<val>
- Paper optimum: <param>=<val>, <metric>=<val>
- Agreement: ...

## Anomalies / warnings
Bullets. E.g. "solve at length=45cm took 3× longer, expected due to larger mesh"

## What downstream needs
- Stage 04 will post-process the optimum config: at `<param>=<val>`, HDF5 at `log/sweep_<param>_<val>.h5`
```

## Return value to main loop
3–5 lines: sweep dim, N points, optimum value + metric, agreement with paper.

## Related pitfalls
- `../../pitfalls/mcp-pitfalls.md` #2 (StoreDoubleParameter wipes results)
- `../../pitfalls/mcp-pitfalls.md` #11 (solver param blocks — keep minimal)
- `../../pitfalls/mcp-pitfalls.md` #12 (avoid `python -c` for post-processing → use script files under `log/`)
