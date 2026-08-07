# Stage 04 · Postprocessing — B1+ / SAR maps + paper Fig comparison

**Goal**: For the optimum sweep point (or baseline if no sweep), produce publication-style B1+ / SAR figures and compare to the paper's Figures.

## Inputs
- `stages/03_sweep_results.md` (or `stages/02_baseline_build.md` if no sweep)
- The optimum HDF5 file (or baseline HDF5)
- Paper figures for comparison (references_cases / target_paper PDFs; may need to look at figure image directly)

## Method

1. **B1+ maps** — use `scripts/compute_b1plus.py`:
   ```bash
   python <skill>/scripts/compute_b1plus.py \
       --h5 <optimum_h5> \
       --outroot results --project <project_id> \
       --b0-plus-z --norm-1w --p-accepted <W_from_1D_result> \
       --roi-zmax <phantom_top_mm> --roi-zmin <phantom_bottom_mm> \
       --sag-zrange "<z_min>,<z_max>"
   ```
   Produces `B1p_2D_maps.png` + `B1p_1D_profiles.png` + `stats.json` in `output/`.

2. **SAR maps** (if paper reports 10g SAR):
   - Use CST native IEEE 10g SAR, not an E-field point proxy.
   - Ensure TD hex + loss monitor if native SAR is required; export H-field before `SAR.Create`.
   - Use `scripts/export_native_sar.py` for scalar/HDF5 export through the verified `Result3D` + `AddToTree` route. For data-prep D1, use `export_data_prep_sar10g(...)` and the D1 phantom subvolume from the module recipe.
   - Normalize by measured accepted power unless the field has been proven to be correctly `scale accepted`.

3. **Compare to paper figure**:
   - Extract paper's figure caption values (from `01_paper_spec.md` anchors)
   - Read our peak / mean / CV from `stats.json`
   - Note agreement: exact numbers, factor-2 range, order-of-magnitude, or way off

4. **Save comparison figure** (side-by-side or overlay) at `output/paper_comparison.png` if practical (a subplot of our data + paper caption text)

## Do NOT invent
- Do not use `0.5*sigma*|E|^2/rho` as a replacement for the native SAR spatial distribution.
- Do not select the temporary `SAR.Create` node directly in headless mode; use `Result3D` + `AddToTree`.
- If native SAR export still fails, mark SAR `partial_native_scalar_only` or `partial` with the exact error and evidence paths.

## Handoff — write `stages/04_postproc.md`

Template:
```markdown
---
stage_id: 04_postproc
status: passed | partial
project: <project_id>
inputs:
  - stages/03_sweep_results.md (or 02_baseline_build.md)
outputs:
  - results/<project>/output/B1p_2D_maps.png
  - results/<project>/output/B1p_1D_profiles.png
  - results/<project>/output/stats.json
  - (optional) results/<project>/output/SAR_map.png
  - (optional) results/<project>/output/paper_comparison.png
stats:
  peak_b1p_ut_per_sqrtW: <val>
  b1p_at_10cm_depth_ut_per_sqrtW: <val>
  b1p_cv_at_roi: <val>
  peak_sar10g_W_per_kg: <val> | null (if not computed)
  ratio_b1p_sqrtSAR: <val> | null
  paper_reported_peak_b1p: <val>
  agreement_b1p: "matches | ~factor 2 | off"
  agreement_sar: "matches | not computed"
---

## What we made
Bullets: which PNG, from which HDF5, what was the ROI / normalization.

## Paper comparison
| Metric | Paper (Fig/Table) | Our reproduction | Agreement |
|--------|-------------------|------------------|-----------|
| ...    | ...               | ...              | ...       |

## Limitations / caveats
- E.g. "Native 10g SAR scalar succeeded, but HDF5 export failed after Result3D/AddToTree; SAR map omitted"
- E.g. "Paper's Fig 3 uses logarithmic scale, we plotted linear; comparable but not identical visually"

## What downstream needs
- Stage 99 audits every declared target, tolerance, trend, assumption, and evidence path before
  writing the final conclusion
- If SAR partial: user decision needed on whether to re-solve/export in a fresh post-solve CST session
```

## Return value to main loop
3–5 lines: B1+ peak, agreement with paper, SAR status.

## Related pitfalls
- `../../pitfalls/mcp-pitfalls.md` #12 (script files not `python -c`)
- `../../pitfalls/mcp-pitfalls.md` #14 (use `cst.results.ProjectFile(path, allow_interactive=True)` to read our own project's Power Accepted)
- `../../driving/cst-operation-notes.md` — Result3D.Load for 3D fields, read-after-write staleness
- `../b1-sar/sar-field-export.md` and `../../pitfalls/sar.md` — native 10g SAR scalar/HDF5 export
