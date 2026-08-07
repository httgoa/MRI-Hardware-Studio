# Pitfalls — SAR Calculation & Export

SAR is where this project has hit the most traps. Full worked template: `recipes/b1-sar/sar-field-export.md` + script `scripts/export_native_sar.py`; field materialization prerequisite: `field-export.md`.

### `SAR.Create` node invisible headless (+ collapses the tree)
- **Symptom**: `SAR.Create` succeeds, `GetValue("max sar")` returns a correct value, but immediately afterward `SelectTreeItem("2D/3D Results\SAR\SAR10g")` = **False**; `get_tree_items()` item count drops sharply (185→99), `2D/3D Results` is left with only a root node, and even the previously-selectable H/E fields become unselectable; `ASCIIExport` reports "not available for current view"; VBA `Resulttree` enumeration writes an empty file.
- **Root cause**: the tree node `SAR.Create` registers is invisible to the headless channel, and the Create action itself collapses the 2D/3D tree enumeration.
- **Workaround**: **do not select the `SAR.Create` node**. Instead use the `Result3D` two-hop route: ① `Result3D("SAR (f=freq) [1] (10g)")` loads the on-disk `.m3d` (bypasses the tree; on the Python side `m.Result3D(name)` returns a RemoteObject directly, with `GetArray("xre")`/`GetNx/y/z`/`GetUnit`, the SAR scalar stored in `xre`); ② if you need coordinates for HDF5, re-register it into the tree with `res.AddToTree "2D/3D Results\SAR","<label>"` → the re-inserted node then has `SelectTreeItem` = True → normal `ASCIIExport` works.
- **Origin**: cracked on the ind150 case (2026-07-16), matching the previous day's GUI export point-for-point at 0.000% diff.
- **Rule anchor**: → red-lines "Native 10g SAR 3D field export".

### Data-prep D1 all-zero SAR HDF5 from the wrong subvolume
- **Symptom**: `sar10g_native_norescale_2mm.h5` exists and has `Mesh line x/y/z` + `SAR`, but `SAR.max()==0`, or the exported field obviously misses the phantom.
- **Root cause**: the export used an older generic surface box such as `z=-20..0` instead of the D1 phantom/loss non-zero region. In the D1 regular-dipole project, the required box is `[-135,135,-160,160,-120.5,-20.5]` mm. A second common trigger is looking for `f=210` labels when the CST result tree uses GHz project units (`f=0.21`).
- **Workaround**: for D1, call `export_data_prep_sar10g(...)` with its current defaults or explicitly pass `subvol=("-135","135","-160","160","-120.5","-20.5")`. Validate `SAR.max()>0` and raw HDF5 max against the no-rescale `SAR.GetValue("max sar")` before writing `validated_native_h5`.
- **Origin**: consolidated from `notes/data_prep/AGENT_BATCH_SIMULATION_PIPELINE.md` after the regular-dipole SAR export fix.

### `scale accepted` silently fails on severely mismatched bare ports
- **Symptom**: `SAR.SetOption "scale accepted"` raises no error, but the normalization doesn't take effect — the return value is **exactly equal** to `no rescale` (it should differ by 1/P_acc).
- **Root cause**: when a bare discrete port is severely mismatched (S11≈−0.8dB, P_acc only a few percent of the excitation), CST fails to derive accepted power from the port excitation and silently falls back to a per-stimulation reference.
- **Workaround**: **self-check** — on the same project, the ratio of `GetValue("max sar")` under `no rescale` vs `scale accepted` should be ≈ 1/P_acc; if it equals 1, the rescale has failed. Use `no rescale` to get the per-stimulation value and **manually divide by the measured P_acc** (same principle as dividing B₁⁺ by √P_acc). Violating this flips the direction of the SAR term in FoM entirely (once produced the paper-contradicting result "shorter antenna has lower SAR, optimum at L=50mm").
- **Origin**: FD_Optimize stage 1 (2026-07-15).
- **Rule anchor**: → red-lines; memory `cst-sar-scale-accepted-fails-on-mismatch`.

### E-field point proxy falsified (banned)
- **Symptom**: previously used `SAR ∝ 0.5·σ|E|²/ρ` derived from the E-field as a substitute SAR profile instead of the native SAR field.
- **Root cause**: `|E|²` peaks at the dipole conductor ends (charge accumulation), giving a spatial distribution **opposite** to the true 10g SAR (end peaks vs a center peak/two-wavelength double peak). The true 10g SAR is governed by near-field power deposition + mass averaging.
- **Workaround**: **never use the E-field proxy**. Quantitative comparison on ind150: native field shows a double peak at y=±112mm with a center dip of 0.56; the E-proxy peaks near y≈30mm close to center with no double peak. No amount of smoothing fixes this. It only coincidentally looks close in shape when the antenna is unsegmented and SAR is naturally single-peaked at center (the M2 length-sweep case, which is why this wasn't exposed earlier). For SAR spatial distribution → use the native field (the Result3D route above).
- **Origin**: FD_Optimize M3. Memory `cst-sar-line-eproxy-and-steadystate`.

### `max sar y`/`z` return sentinel values
- **Symptom**: `GetValue("max sar y")` / `"max sar z"` returns −1e102.
- **Workaround**: within a single Create call, only the `max sar` scalar is reliable; `max sar x` is sometimes usable. To get the location, you must `SetLabel`+`Load` before `GetValue` (and it's easily stale).

### Normalization: plot SAR profiles at absolute @1W, don't normalize each line by its own peak
- **Symptom**: normalizing each SAR longitudinal profile line to its own maximum erases the peak-height differences.
- **Root cause**: the peak height itself is physical (capacitors raise SAR, inductors lower SAR).
- **Workaround**: plot the absolute @1W values. Fields exported with `scale accepted` are already @1W — **do not divide by P_acc again** after reading them; self-check `field.max()` ≈ `GetValue("max sar")`@1W (diff <5%).
- **Origin**: FD_Optimize M3.
