# Fractionated Dipole (FD) Complete-Case SOP — Expert-Reviewed Pilot Spec

Status: **Expert-reviewed FD parameter matrix accepted.** `FD_case_matrix.csv`
is the authority for official FD pilot parameters. This SOP is now approved as
the implementation spec for writing an FD automation engine and attempting one
complete FD pilot case, mirroring the way the regular-dipole SOP was first used.

Important guardrail: no FD row should be run through the existing RD-only
`scripts/data_prep_dipole_complete_case.py::live_build_case` or
`scripts/run_d1_regular_batch.py`. Implement the FD sibling script/entry points
in §3 first, then run one pilot case end-to-end before starting an FD batch.

## 1. Ground Truth For Topology

FD topology and first-pilot parameters are taken from the expert-reviewed
`FD_case_matrix.csv`. Older notes, probe summary JSON, and earlier diagnostic
runs are historical references only when they conflict with this matrix.

The matrix encodes this official first FD topology:

- **Two arms** (`arm_pY_*` for +Y, `arm_nY_*` for -Y), fed at the center by a
  `DiscretePort` between `-hole` and `+hole` — same discrete-port mechanism
  RD uses, just at the arm root instead of a single-brick gap.
- Each arm is split into 2 equal PEC brick segments, so
  **`segment_count_total=4`** physical conductor pieces total.
- There is one `seg_gap_mm=2` bridge gap per arm. Derive
  **`bridge_count_total=2`** for records and QA.
- Segment length per arm:
  `((L_total/2 - hole) - seg_gap) / 2`. Segment `k` (0 or 1) starts at
  `hole + k*(segment_length + seg_gap)`.
- Between the two segments within each arm, create one `LumpedElement`
  (`RLCSerial`) bridging the gap. For `lt_bridge_mode=lumped_C`, set
  `R=0`, `L=0`, `C=bridge_C_pF*1e-12`. For `lt_bridge_mode=lumped_L`, set
  `R=0`, `L=bridge_L_nH*1e-9`, `C=0`.
- The first matrix includes capacitive values `bridge_C_pF={1.0,1.5,2.0,5.0}`
  and inductive values `bridge_L_nH={50,75,100,125,150}`. Use exactly the
  value in the row; do not substitute probe defaults.
- Conductor thickness `T=0.5 mm`; width `W_line=10 mm`; `L_total` comes from
  the row;
  `hole=gap/2=1 mm` (`feed_gap=2 mm`, matches RD's `feed_gap_mm` convention);
  z-position `H_height=20 mm` above the phantom top face (phantom top at
  z=0 in the probe; RD's convention is `z_coil = phantom_top_z + lift`, so
  `H_height` plays the same role as RD's `coil_to_phantom_mm`/`lift`).
- **No substrate/support solids** are allowed in official FD complete cases.
  Model only conductor segments, the discrete port, bridge lumped elements, and
  the phantom.
- Do not reuse `results_data_prep_test/FD_A03` or `FD_A04` geometry as an
  official parent. Those runs are useful only as export/postprocess evidence.

## 2. What Is Identical To The RD Engine (Reuse As-Is)

These pieces of `scripts/data_prep_dipole_complete_case.py` are
topology-agnostic and should be reused unchanged for FD, not rewritten:

- `Units`/`Background`/`Boundary` setup block.
- Phantom material + brick (`eps_r=78`, `sigma=0.47`, `rho=1000`,
  `PHANTOM_SIZE=(270,650,300)`, substrate-free — per the 2026-07-23 policy
  override, this replaces the probe's own `eps_ph=34`/500mm-cube/298MHz
  environment).
- `DiscretePort` VBA block (same `SetP1`/`SetP2` pattern at `±hole`, same
  z-center `z_coil+T/2`).
- Field monitors (h-field/e-field/loss at `freq`), TD hex solver block,
  `Solver.FrequencyRange` policy (adapt center frequency to 210 MHz / GHz
  units like RD, not the probe's 298 MHz / MHz units).
- `live_start_solver`, `live_poll_solver`.
- `live_export_fields_and_sar` (H/E/loss/current export + native SAR
  two-hop `Create`+HDF5 route) — no topology dependency.
- `_extract_electrical_summary` (S11/impedance/power CSV extraction).
- `compute_case_metrics` (B1+/SAR/current post-process from HDF5) — uses
  `row["L_line_mm"]` only for a coarse current center/tip heuristic; works
  for FD without changes.
- `record_template_v1.json` schema — already has the fields FD needs
  (`geometry.segment_count_total`, `segment_lengths_mm`, `seg_gap_mm`,
  `bridge_count_total`, `bridge_positions_mm`,
  `electrical_design.fractionated_bridge.{lt_bridge_mode,bridge_C_pF,
  bridge_L_nH,bridge_R_ohm}`), confirmed by `FD_E00.json`/`FD_E01.json`
  already populating them. **No schema/template change needed.**

## 3. What Must Change / Be Added For FD Before The Pilot

1. **Geometry build function** (new, e.g. `live_build_fd_case`, sibling to
   `live_build_case`): derive `segments_per_arm =
   segment_count_total / 2` from the row. For the current matrix this is fixed
   at 2. Generate `segment_count_total` PEC bricks and
   `bridge_count_total = 2*(segments_per_arm-1)` `LumpedElement` bridges using
   the position formula in §1.
2. **`record_id_for()`**: RD's scheme (`cc_rd_L..._W..._lo..._direct_210`)
   does not encode `bridge_C_pF`/`seg_gap_mm`, so two FD rows that only
   differ in bridge value would collide. Use mode-specific accepted schemes:
   `cc_fd_L{L}_W{W}_lo{lo}_seg{segment_count_total}_g{seg_gap}_C{C}pF_direct_210`
   for capacitive rows and
   `cc_fd_L{L}_W{W}_lo{lo}_seg{segment_count_total}_g{seg_gap}_L{L}nH_direct_210`
   for inductive rows. Needs a family-aware dispatch
   (`if row["family"] == "fractionated_dipole": ...`) since the module
   currently has one global `record_id_for`.
3. **`write_record()`**: `geometry.topology` should be
   `"fractionated_dipole_direct_port"` (not the hardcoded
   `"regular_dipole_direct_port"` currently written unconditionally); the
   `geometry` block needs the extra FD fields from §1 populated from the
   case row + derived formula (not just `L/W/lift/feed_gap`); the
   `electrical_design.fractionated_bridge` sub-block needs to be filled;
   `learning_card.design_tokens` should include `"fractionated_dipole"` and
   mode-specific bridge tokens such as `"lumped_capacitive_bridges"` or
   `"lumped_inductive_bridges"` instead of `"regular_dipole"`.
4. **`CASE_MATRIX` resolution**: the module currently hardcodes
   `RD_case_matrix.csv`. It needs family-aware routing (read
   `FD_case_matrix.csv` when the row/CLI target is a `FD_*` id), e.g. try
   both files in `read_case_row()` or accept an explicit `--matrix` path.
5. **`update_manifest()`**: extend the shared `results_data_prep/manifest.csv`
   with FD-capable columns (`segment_count_total`, `seg_gap_mm`,
   `bridge_count_total`, `lt_bridge_mode`, `bridge_C_pF`, `bridge_L_nH`,
   `bridge_R_ohm`). Leave these blank/null for RD rows. Keep a single manifest
   rather than creating `manifest_fd.csv`.
6. Module docstring in `data_prep_dipole_complete_case.py` currently states
   "It intentionally handles only ... regular_dipole" — must be updated once
   FD support is added, or the FD build should live in a sibling script
   (`data_prep_fd_dipole_complete_case.py`) that imports the shared
   solve/export/postprocess helpers from the RD module. **Prefer the sibling
   script** to avoid destabilizing the already-validated RD engine.
7. **Pilot runner**: add a small FD runner or `--fd` control-plane surface only
   after the single-case FD script exists. It must read `FD_case_matrix.csv`
   directly and must not depend on `run_d1_regular_batch.py` selecting FD rows.

## 4. Per-Case Execution Order (FD)

Pilot recommendation: start with `FD_A01` because it is the center baseline
(`L_line_mm=300`, `strip_width_mm=10`, `coil_to_phantom_mm=40`,
`bridge_C_pF=1.5`) and exercises the exact bridge-capacitance interpolation
used by the expert-reviewed matrix.

1. Read the target row from `FD_case_matrix.csv`.
2. Build: parameters → units/background/boundary → phantom material/brick →
   `segment_count_total` PEC arm segments (per §1 formula) → discrete port at
   center → derived `bridge_count_total` lumped C or L bridges → field monitors
   → TD hex solver.
3. Save, solve TD hex, re-solve if volume monitors are missing (same as RD).
4. Export H-field, loss, and surface current (reuse RD's export helpers).
5. Read measured `p_accepted_W` and S-parameters (reuse RD's extractor).
6. Run native SAR scalar with `no rescale`.
7. Export native SAR HDF5 through `Result3D` + `AddToTree` (reuse RD's route).
8. Validate SAR HDF5 against `GetValue("max sar")`.
9. Run offline B1+/SAR/current postprocess (reuse `compute_case_metrics`).
10. Write `fom.json`, case record (with FD `geometry`/`fractionated_bridge`
    fields and FD `record_id` scheme), global record, and manifest.
11. Set QA flags and status (add FD-specific flags, §5).

## 5. FD-Specific QA Flags To Add

- `fd_segment_count_matches_matrix` (built segment count ==
  `segment_count_total`).
- `fd_bridge_count_matches_segment_count` (built bridge count ==
  `segment_count_total - 2`, i.e. 2 for the current two-arm/two-segment-per-arm
  matrix).
- `fd_bridge_mode_and_value_match_matrix` (`lumped_C` uses `bridge_C_pF`;
  `lumped_L` uses `bridge_L_nH`).
- `fd_no_substrate_solids_present` (explicit substrate-free confirmation,
  since the probe history shows an unused `PMMA` material definition that
  must not be accidentally instantiated).
- Reuse all RD SAR/B1+/current QA flags unchanged.

## 6. Resolved Decisions Before Writing The Engine

These decisions are now fixed for the first FD pilot and the current
`FD_case_matrix.csv`:

1. **Record id scheme**: use mode-specific ids:
   `cc_fd_L{L}_W{W}_lo{lo}_seg{segment_count_total}_g{seg_gap}_C{C}pF_direct_210`
   or
   `cc_fd_L{L}_W{W}_lo{lo}_seg{segment_count_total}_g{seg_gap}_L{L}nH_direct_210`.
2. **Implementation shape**: prefer a sibling script
   `data_prep_fd_dipole_complete_case.py` that imports reusable RD helpers for
   solve/export/postprocess/record mechanics, rather than editing the validated
   RD build path in place.
3. **Manifest strategy**: extend the shared `results_data_prep/manifest.csv`
   with FD columns and keep one manifest.
4. **Segment scope**: fixed at `segment_count_total=4` for every row in the
   first expert-reviewed FD matrix. Segment-count sweeps are deferred.
5. **Bridge mode scope**: `lumped_C` and `lumped_L` are both in scope because
   they are present in the expert-reviewed matrix. Disconnected `none` controls
   are out of scope.

## 7. Pilot Gates And Non-Goals

Before a case is considered a valid FD complete-case attempt:

- The FD build entry point must create `segment_count_total` PEC arm segments
  and the derived bridge count from the `FD_case_matrix.csv` row.
- The build manifest and record must include the FD-specific geometry and
  bridge fields.
- The output root must follow the D1 complete-case layout under
  `results_data_prep/<case_matrix_id>/`.
- The same SAR HDF5 validation gates used for RD must pass or the record must
  be marked `partial`/`needs_validation` with exact evidence paths.

Non-goals for the first pilot:

- Do not run the full FD matrix before one pilot case is complete or explicitly
  marked with a diagnosed failure mode.
- Do not introduce `none`, substrate/support solids, W sweeps, or segment-count
  sweeps.
- Do not revise `record_template_v1.json` unless implementation proves a field
  is genuinely missing; the current template already contains the required FD
  fields.
