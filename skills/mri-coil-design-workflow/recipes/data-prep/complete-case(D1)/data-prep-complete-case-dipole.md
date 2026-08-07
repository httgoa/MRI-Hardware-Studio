# Data Prep Complete Case - Dipole Module (D1)

Use this module when the user asks for official data-prep complete cases for
regular dipoles or expert-reviewed fractionated-dipole pilot cases. This module is
self-contained: the case matrix and record template live beside this recipe.

## Module Files

Read these files first, in this order:

1. `RD_case_matrix.csv` - canonical case list for `regular_dipole` (anchor,
   space_fill, perturbation, interaction roles).
2. `FD_case_matrix.csv` - expert-reviewed canonical case list for
   `fractionated_dipole` (anchor, space_fill roles). This file overrides older
   FD parameter plans and the legacy combined matrix.
3. `data-prep-complete-case-fd-sop.md` - FD-specific SOP: confirmed real
   topology, build/solve/export/record plan, implementation decisions, and
   pilot-case gates. Read this before touching FD.
4. `case_matrix_v1.csv` - legacy combined file, superseded by the two files
   above. Kept only as historical reference; scripts no longer read it.
5. `record_template_v1.json` - canonical output record schema, shared by both
   families.
6. `notes/data_prep/AGENT_BATCH_SIMULATION_PIPELINE.md` - upstream project SOP and
   the authority for this module's regular-dipole batch details, especially SAR
   3D HDF5 export.
7. `data_prep/dipole3_run/REFERENCE_CASE.md` - frozen dipole reference case for
   B1+/pipeline sanity comparisons. Do not modify `data_prep/dipole3_run/`.

Also obey the global skill rules in:

- `../../../driving/artifact-pipeline.md`
- `../../../foundations/cst-simulation-sop.md`
- `../../../driving/cst-operation-notes.md`
- `../../b1-sar/sar-field-export.md`

If a project-specific detail here or in
`notes/data_prep/AGENT_BATCH_SIMULATION_PIPELINE.md` conflicts with a generic
skill default, the data-prep module wins for this module.

## Scope And Starting Point

- Start official production with `regular_dipole` rows whose `source_seed=template`.
- `fractionated_dipole` is no longer on hold for SOP/engine work. Its
  parameters are locked by the expert-reviewed `FD_case_matrix.csv`, and its
  topology is locked to the real existing probe projects at
  `data_prep/frac_dipole/fd_seg_C1.cst` and `fd_seg_C2.cst`: two Y-directed
  arms, each split into 2 PEC conductor segments, direct-fed at the center,
  with one bridge gap per arm. This is `segment_count_total=4`,
  `seg_gap_mm=2`, derived `bridge_count_total=2`, `strip_width_mm=10`, and
  `lt_bridge_mode`/`bridge_C_pF`/`bridge_L_nH` values taken from
  `FD_case_matrix.csv`.
- Do not use the legacy "single 300 mm line / 4 equal segments / 3 bridges"
  interpretation for official FD records. That wording belongs to older drafts
  and is superseded by `FD_case_matrix.csv` plus the FD SOP.
- Existing probe rows (`FD_E00`/`FD_E01` in the legacy `case_matrix_v1.csv`)
  are diagnostic only (298 MHz, eps_r=34, substrate present). Copy them before
  opening; do not use them as numerical parents for official substrate-free
  anchor cases unless the user explicitly asks.
- `data_prep/dipole3_run/Dipole3_run.cst` is a frozen solved reference, not a
  template to edit or re-solve. Use it to compare expected 210 MHz B1+ pipeline
  behavior and result-tree naming.

## Layer 3/4 Roles (Perturbation And Interaction)

`RD_case_matrix.csv` carries `regular_dipole` rows with `role=perturbation`
(`RD_P01`-`RD_P24`) and `role=interaction` (`RD_I01`-`RD_I06`), built on top of
the anchor/space_fill layers per `notes/data_prep/analysis.md`'s four-layer
sampling plan:

- Perturbation rows are single-parameter neighbors (`L_line_mm` ±10%,
  `strip_width_mm` ±20%, `coil_to_phantom_mm` ±10 mm) around four anchors
  (`RD_A01` center, `RD_A06` near-phantom, `RD_A07` far-phantom, `RD_A08`
  weakest-performer corner), selected from the validated `results_data_prep`
  manifest, not arbitrarily.
- Interaction rows are two-parameter joint changes around `RD_A01`, using the
  same deltas as their matching perturbation rows so a joint delta can be
  compared against the sum of the two single-parameter deltas.
- `RD_P11` uses a reduced `+5mm` step instead of the standard `-10mm` because
  `-10mm` from `RD_A06` (20.5mm) would drop below the near-phantom safe
  standoff floor; verify with the geometry validator before building it.
- Four new trailing CSV columns carry lineage: `parent_case_matrix_id`,
  `action_type`, `changed_params`, `direction_label`. Older anchor/space_fill
  rows leave these blank; `csv.DictReader` fills missing trailing fields with
  `None`, so this is safe and requires no changes to existing rows.
- The record engine (`scripts/data_prep_dipole_complete_case.py`) reads these
  four columns and populates `record.lineage` (resolving
  `parent_record_id` via `record_id_for()` on the parent row) and appends
  `role` to `learning_card.design_tokens` when `role` is `perturbation` or
  `interaction`. No other schema or template change is needed — reuse
  `record_template_v1.json` as-is for these two layers.
- Record IDs are still derived purely from `(L_line_mm, strip_width_mm,
  coil_to_phantom_mm)`; any new perturbation/interaction row must use a unique
  geometry triple across the whole matrix to avoid record collisions.
- Run with the existing batch runner, e.g.
  `run_d1_regular_batch.py --init --roles perturbation` then
  `--roles interaction`; no runner code changes were needed since `--roles` is
  a free-form string filter.

## Fractionated Dipole (FD) Baseline

`FD_case_matrix.csv` holds 14 `anchor` + 12 `space_fill` rows for
`fractionated_dipole`. Full SOP (topology proof, build/solve/export/record
mapping, implementation decisions, and pilot gates) lives in
`data-prep-complete-case-fd-sop.md` — read that file before writing or running
any FD automation. Summary:

- Topology and first-layer parameters are locked by the expert-reviewed
  `FD_case_matrix.csv`: `segment_count_total=4`, `seg_gap_mm=2`,
  `strip_width_mm=10`, two arms, 2 conductor segments per arm, and one bridge
  gap per arm. Derive `bridge_count_total=2` for records and QA.
- Anchors mirror the RD anchor design for length and standoff, and add bridge
  sweeps: `L_line_mm` in {200,250,300,350}, capacitive `bridge_C_pF` in
  {1.0,1.5,2.0,5.0}, inductive `bridge_L_nH` in {50,75,100,125,150}, and
  `coil_to_phantom_mm` in
  {20.5,40,80} (near/center/far, matching RD's convention), all at `W=10`
  since only `W=10` was probed — do not add a `W=5` FD anchor without new
  justification, since that widens the design beyond the probed topology.
- Materials/frequency/phantom follow the same substrate-free, 210 MHz,
  `eps_r=78` production policy as regular_dipole (2026-07-23 policy override).
  This differs from the literal probe environment (298 MHz, `eps_r=34`,
  no substrate but different phantom) — the probe only supplies the
  conductor/bridge topology, not the electrical environment.
- **Engine gap and start condition**: unlike `regular_dipole`, there is no
  generalized live-build engine for `fractionated_dipole` yet.
  `scripts/data_prep_dipole_complete_case.py` is regular_dipole-only (see its
  module docstring). The next allowed step is to implement the FD sibling
  script described in the FD SOP and run one FD pilot complete case, preferably
  `FD_A01` for the capacitive baseline, before expanding to the full FD matrix.
  Do not send FD rows through
  `run_d1_regular_batch.py` or the RD `live_build_case` function.

## Geometry Policy

Official complete cases are substrate-free:

- Model only coil conductors, ports/necessary lumped elements, and the phantom.
- Do not create or retain FR-4 boards, polycarbonate holders, foam spacers,
  dielectric support stacks, substrate boards, slabs, or visual carrier solids.
- After every `Rebuild`, delete legacy solids matching:


```text
substrate, board, FR4, polycarbonate, foam, spacer, support, slab
```

The record must reflect this:

```text
geometry.model_variant = substrate_free_coil_phantom
geometry.include_substrate = false
geometry.support_stack = none
learning_card.design_tokens += ["coil_and_phantom_only"]
```

## Record And Output Layout

Use one output root per case:

```text
results_data_prep/<case_matrix_id>/
  log/
  artifacts/
  cases/<record_id>/
  output/record.json
results_data_prep/records/<record_id>.json
results_data_prep/manifest.csv
```

Rules:

1. Never write official data-prep records under legacy `results/`.
2. For `source_seed=template`, build in a new CST project under
   `projects/data_prep_<case_matrix_id>/`.
3. Direct-port records do not require schematic data; set
   `source.schematic_snapshot_path=null`.
4. Write identical records to the case output and global records folder.
5. Update `results_data_prep/manifest.csv` last, with last-wins behavior by
   `record_id`.
6. Unrun or unsupported rows get placeholder records with measured outputs kept
   as `null`; never fabricate metrics.

Record id for regular direct-port cases:

```text
cc_rd_L<L_line>_W<strip_width>_lo<coil_to_phantom>_direct_210
```

Example:

```text
cc_rd_L200_W5_lo60_direct_210
```

Record id for fractionated direct-port cases:

```text
cc_fd_L<L_line>_W<strip_width>_lo<coil_to_phantom>_seg<segment_count_total>_g<seg_gap>_C<bridge_C_pF>pF_direct_210
cc_fd_L<L_line>_W<strip_width>_lo<coil_to_phantom>_seg<segment_count_total>_g<seg_gap>_L<bridge_L_nH>nH_direct_210
```

Example:

```text
cc_fd_L300_W10_lo40_seg4_g2_C1p5pF_direct_210
cc_fd_L300_W10_lo40_seg4_g2_L50nH_direct_210
```

## Solver And Monitors

For native 10g SAR complete cases:

- Solver: HF Time Domain, hexahedral/Hex-PBA.
- Frequency: 0.21 GHz.
- Monitors before solve: H-field, E-field, power loss/loss.
- Direct-port field source: `[1]`.
- If the first TD solve has no H/loss volume field on disk or in the result tree,
  solve again, up to three attempts.
- Do not treat "solver ok" as field-export success; verify output files or result
  directory entries.

## Fixed Phantom Export Box

For this module, export H/loss/SAR over the phantom non-zero region:

```text
X: -135 to 135 mm
Y: -160 to 160 mm
Z: -120.5 to -20.5 mm
```

Do not use the generic SAR profile default `z=-20..0`; it can produce all-zero
SAR HDF5 for this project.

Recommended files:

```text
cases/<record_id>/hfield_1mm.h5
cases/<record_id>/loss_2mm.txt
cases/<record_id>/surfcurrent_raw.txt
cases/<record_id>/surfcurrent_conductor_clean.txt
cases/<record_id>/sar10g_native_norescale_2mm.h5
cases/<record_id>/fom.json
```

Surface-current export ignores subvolume in CST; export the full model and then
filter to the conductor bounding box.

## B1+ Postprocess

Read `hfield_1mm.h5` as CST's structured HDF5 field. Use Fortran order and the
CP transmit component for B0 along `+z`:

```python
B1p_uT = mu0 * abs(Hx - 1j * Hy) / 2 * 1e6
B1p_uT_per_sqrtW = B1p_uT / sqrt(p_accepted_W)
```

Required B1+ outputs include peak, surface mean, 30/60/100 mm means, 10 cm ROI
stats, ROI CoV, half-value depth, depth/lateral profiles, and 48x48 slices.

## Native SAR10g 3D Export - Hard Route

This is the authoritative route for the previously failing SAR 3D field export.
Follow it exactly.

1. Stay in the same fresh post-solve CST session. Do not close/reopen before SAR
   export unless you re-solve afterward.
2. Export H-field/loss/current before any `SAR.Create`.
3. Use the actual loss monitor name. For regular direct-port data-prep cases this
   is normally:

```text
loss (f=0.21) [1]
```

Do not blindly use `loss (f=freq) [1]`; probe candidates first.

4. Compute native SAR with `no rescale` and record the scalar:

```vba
With SAR
  .Reset
  .PowerlossMonitor "loss (f=0.21) [1]"
  .AverageWeight "10"
  .SetOption "IEEE C95.3"
  .SetOption "no rescale"
  .SetOption "volaccuracy 0.05"
  .Create
  StoreDoubleParameter "sarmax_norescale", .GetValue("max sar")
End With
```

5. Confirm the native SAR `.m3d` exists or is loadable. If
   `Result3D("SAR ...")` reports `file does not exist` immediately after
   `SAR.Create`, wait 1-2 seconds and probe `Result/SAR*.m3d` or the true
   result label before declaring failure.
6. Do not select the temporary `SAR.Create` node. Export through the two-hop
   route implemented by
   `../../../scripts/export_native_sar.py::export_data_prep_sar10g`:

```text
Result3D("SAR (f=0.21) [1] (10g)")
res.AddToTree "2D/3D Results\SAR", "<case_id>_SAR10g_export"
SelectTreeItem "2D/3D Results\SAR\<case_id>_SAR10g_export"
ASCIIExport HDF5, FixedWidth, Step 2, subvolume [-135,135,-160,160,-120.5,-20.5]
```

7. Normalize manually after reading:

```python
sar_W_per_kg_per_W = sar_raw_norescale / p_accepted_W
```

Do not use E-field proxy SAR for the spatial distribution, and do not trust
`scale accepted` in mismatched direct-port cases unless a no-rescale/scale
self-check proves it works.

## SAR HDF5 Validation

The SAR HDF5 must contain:

```text
Mesh line x
Mesh line y
Mesh line z
SAR
```

Validation gates:

- `SAR.max() > 0`.
- Raw HDF5 max is within 5% of `SAR.GetValue("max sar")` from the same
  no-rescale SAR calculation.
- `field_artifacts.sar10g_h5` points at the validated HDF5.
- `sar_signature.sar_status = validated_native_h5`.
- Manifest `sar10g_native_status = validated_native_h5`.

Verified regular-dipole example from the upstream SOP:

```text
record_id: cc_rd_L200_W5_lo60_direct_210
sarmax_norescale_GetValue: 0.000694732
sarmax_norescale_HDF5: 0.0006942227482795715
relative_error: 0.0733%
sar10g_max_W_per_kg_per_W: 0.7266406493800993
hotspot_xyz_mm: [-1.0, 0.0, -68.5]
```

Status values:

```text
validated_native_h5
partial_native_scalar_only
partial
needs_validation
```

Use `partial_native_scalar_only` only when `SAR.GetValue("max sar")` succeeded
but HDF5 export did not. Use `partial` for loss proxy or incomplete SAR.

## SAR Learning Artifacts

After SAR HDF5 validation, generate learning artifacts instead of leaving the
record fields null:

```text
dataset/learning/profiles/<record_id>_sar_depth.csv
dataset/learning/slices/<record_id>_sar_slices_48x48.npz
```

Use:

```text
surface_z_mm = -20.5
depth_mm = surface_z_mm - z_mm
depths_mm = [30, 60, 100]
ROI: abs(x) <= 40 mm and abs(y) <= 40 mm
```

`sar_hotspot_distance_to_conductor_mm` may be estimated from
`surfcurrent_conductor_clean.txt`. If that file is absent, keep the field `null`.
`sar_hotspot_concentration` is:

```python
sar10g_max_W_per_kg_per_W / sar10g_volume_mean_W_per_kg_per_W
```

## Per-Case Execution Order

1. Read the target row from `RD_case_matrix.csv` (regular_dipole) or
   `FD_case_matrix.csv` (fractionated_dipole).
2. Copy/open the template or probe project.
3. Build/update parameters and delete substrate/support solids after rebuild.
4. Save, solve TD hex, and re-solve if volume monitors are missing.
5. Export H-field, loss, and surface current.
6. Read measured `p_accepted_W` and S-parameters.
7. Run native SAR scalar with `no rescale`.
8. Export native SAR HDF5 through `Result3D` + `AddToTree`.
9. Validate SAR HDF5 against `GetValue("max sar")`.
10. Run offline B1+/SAR/current postprocess.
11. Write `fom.json`, case record, global record, and manifest.
12. Set QA flags and status.

## QA Flags

Add relevant flags when completed:

```text
coil_and_phantom_only
native_sar10g_scalar_exported
native_sar10g_h5_exported
native_sar10g_h5_validated_against_getvalue
sar_export_subvolume_corrected_to_project_phantom_box
native_sar10g_depth_profile_generated
native_sar10g_slices_48x48_generated
native_sar10g_hotspot_distance_estimated_from_surface_current
```

`FD_A03` and `FD_A04` remain validated pipeline tests only. Their geometry is
superseded for official data, but their completed runs are still useful for
testing TD hex, H/E/loss/current/SAR export, accepted-power normalization, record
writing, and manifest update mechanics.
