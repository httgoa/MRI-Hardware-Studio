# Pitfalls — Solver & Meshing

Traps around solver choice, meshing, and the steady-state limit. Rule version: `foundations/cst-red-lines.md#Solver Setup`; execution order: `foundations/cst-simulation-sop.md` §B; empirical steady-state-limit data: `foundations/cst-simulation-sop.md` §D.4.

### TD first solve often drops the volume-field monitors ("only appears on the second solve")
- **Symptom**: on a `cst.interface` session's first TD solve, only S-parameters + 1D power come out, **no 3D volume fields** (h-field/loss).
- **Workaround**: after solving, check for the field node; if missing, call `start_solver` once more (up to 3 times):
  ```python
  def has_fields(m):
      return any('H-Field' in str(i) and 'h-field' in str(i) for i in m.get_tree_items())
  ```
  Don't poll too aggressively: `is_solver_running()` can transiently return False during the transition, and starting again then collides with "Simulation already running" — poll interval ≥2s, and sleep 3-4s after it exits. Guard before starting: if still running, `abort_solver()` + sleep first.
- **Origin**: FD_Optimize M2.

### Native 10g SAR only supports hexahedral mesh
- **Symptom**: cannot compute native IEEE 10g SAR after an FD tetrahedral solve.
- **Root cause**: CST's native SAR post-processing only supports hexahedral meshes.
- **Workaround**: if SAR is needed → **must use HF Time Domain (hexahedral)**. Low-Q lossy loads (tissue-loaded dipoles) are also better suited to TD, and it matches most papers' FDTD.

### Steady-state limit −30dB speeds up high-Q mismatched points
- **Symptom**: large inductance + severe mismatch (P_acc as low as 0.002W) → long high-Q ringing → TD steady-state time explodes (up to 450s at −40dB for ind150).
- **Root cause**: high-Q resonant energy decays slowly.
- **Workaround**: change to `SteadyStateLimit "-30"`: sufficient accuracy for DFT-integrated frequency-domain field monitors (B₁⁺/SAR distribution) (residual 0.1%, FoM ratio even more stable since it's self-referential), ind150 450s→228s. **The entire sweep must use the same steady-state limit** (cases run under −40dB must be rerun). −40 vs −30 FoM difference <1.5%.
- **Origin**: FD_Optimize M3.

### Solver selection (MRI)
- Narrowband high-Q loaded coil → HF Frequency Domain (tetrahedral); finding mode frequencies → Eigenmode; wideband/needs SAR → Time Domain (hexahedral).
- **Don't blindly set a frequency range on every solver**: setting `Solver.FrequencyRange` for eigenmode can pop an interactive dialog.
- Always `save()` before solving; use async `start_solver`+polling for 3D, not the blocking `cst_run_solver_tool` (times out).
- `get_solver_run_info()` can **misreport `state=ERROR`** on this machine — cross-check `cst_project_info_tool`'s `messages_tail`: if it shows mesh convergence/sweep convergence/post-processing complete, it's a real success — don't blindly re-run.
- **Rule anchor**: → red-lines "Solver Setup".
