# Recipe: B1+ field simulation and 2D profile analysis

**Goal**: for an MRI project containing a 3D frequency-domain solve + circuit co-simulation + a B1+ post-processing template, run the full pipeline and export a 2D profile figure of the B1+ field + homogeneity metrics.

**Verified**: ran end-to-end on a dipole+phantom project on 2026-07-11 (see the [[dipole-b1-pipeline]] memory).

## Prerequisites (confirm first with the inspect recipe)
The project should have:
- A 3D solver (HF Frequency Domain)
- A circuit simulation task (an AC task, e.g. `AC1`)
- A phantom load (the `plantom` parameter)
- A B1+ post-processing template is **no longer a prerequisite**: a from-scratch project without a `Calc B1+` template can still compute it directly with `cst_calc_b1_field_tool` (Stage 3).

If either of the first two are missing -> this is not a "run directly" scenario, go back to inspect or ask the user.

## Three-stage pipeline (key: none can be skipped, order is fixed)

### Stage 0: safety preparation
- If working on the source file: copy to `projects/<name>_run/` first (hard rule: never overwrite the source file), then use `cst_open_project_tool` to open the copy.
- `cst_save_project_tool` before solving (hard rule: save first).

### Stage 1: 3D field solve (async, to avoid a blocking timeout)
Use `cst_run_python_tool`:
```python
project.save()
model3d.start_solver()          # non-blocking
```
Then poll (each call separate, with ordinary waiting in between):
```python
result = {"running": model3d.is_solver_running(),
          "info": model3d.get_solver_run_info()}
```
Done once `state` is no longer RUNNING. Output: `2D/3D Results\H-Field\h-field (f=0.21) [1]`.

> Warning: don't use the blocking `cst_run_solver_tool` — a frequency-domain full-wave solve can take minutes to tens of minutes and will time out.

### Stage 2: circuit co-simulation (AC1) + Combine Results — one shot, no popup
**Preferred**: use the dedicated tool to set up the Signal excitation + turn on Combine Results in one go (set before Update, so it never triggers Abort/Retry/Ignore):
```
cst_configure_ac_combine_tool(task_name="AC1", fmin=0.15, fmax=0.25, unit="GHz",
                              port_name="1", block_name="MWSSCHEM1", amplitude=10)
                              # monitor_filters defaults to [":hfield:"]; for SAR pass ["h-field (f=0.21)","loss (f=0.21)"]
cst_run_circuit_cosimulation_tool(task_name="AC1")
```
This feeds the circuit-optimized excitation back into the 3D solve, producing `h-field (f=0.21) [AC1]`.
**This is the field B1+ depends on (`[AC1]`, not `[1]`).** Verify by iterating `2D/3D Results\H-Field`, which should show both `[1]` and `[AC1]`.

> Warning: **never use `"*"` as the combine filter** (a lesson from Dipole(3)): the `surface-current` monitor has no combinable volume field, and `*` hitting it triggers Abort/Retry/Ignore (even when combine is correctly checked). This is the real root cause of the popup. The default `[":hfield:"]` combining just the H-field is sufficient.
> For the rest of the underlying principles see `../../building-blocks/vba-blocks/dipole-schematic.md`: `docombineresults`/`blocknameforcombineresults` must be set before `.Update`; `SetComplexPortExcitation` must come before `SetPortSourceType "Signal"`.
> Warning: skipping this step causes Stage 3 to report `H-Result not found: h-field (f=0.21) [AC1]`.

### Stage 3: B1+ computation — dedicated tool, no pre-installed template or dialog needed
**Preferred**: use the dedicated tool (it runs CST's built-in MRI-Toolbox "Calc B1+" macro algorithm verbatim, and registers the result-tree node):
```
cst_calc_b1_field_tool(h_monitor="H-Field\\h-field (f=0.21) [AC1]", mu_r=1.0, b0_plus_z=True)
```
Output: `2D/3D Results\B1+ and B1-\B1+ (f=0.21) [AC1]` (Tesla, B=mu0*mu_r*H), `B1- (f=0.21) [AC1]`.
- `mu_r=1.0` -> directly gives the B field (mu_r~=1 in tissue), in Tesla; multiply by 1e6 after export to get µT.
- `b0_plus_z=True` -> B0 along +z (CST's default).
- This tool registers the node using `Result3D.Combine` + `ResultOperator3D.AddToTree`, which **incidentally solves the old from-scratch problem of "the 3D field never got registered into the tree, coordinates can't be exported"** — once registered, Stage 4's `SelectTreeItem`+ASCIIExport works.

> **Alternative (when the project already has a template)**: if the project already has a Calc B1+ / Mix 3D Fields template, you can call `model3d.EvaluateResultTemplates()` directly, which also produces 0D/1D template tables (`B1_Coronal`, `B1_Sagittal`, `_Abs (Y)/(Z)` profiles) for comparison in Stage 4b. A from-scratch project has no such templates, so use the dedicated tool above.

## Stage 4: export the field -> post-process (choose the route per case, don't fight the template)

**Expert conclusion (adopted 2026-07-14)**: exports should uniformly use a **fixed physical step size, `FixedWidth` + `.Step 1` (1-2mm), uniform mesh** (not the old `FixedNumber`+point-count-per-axis). The root cause of precision loss is "the export was too coarse", independent of which script is used — after a 1-2mm export, both scripts are high-fidelity.

**Choose one route per project case (not an arbitrary choice):**

| Case | Route | Script | Why |
|------|------|------|--------|
| **Already has a post-processing template** (Calc B1+ / Mix 3D Fields) | Route 1 | `plot_b1_profiles.py` | need to **overlay our own computed curve onto CST's native template curve** for comparison/calibration; the ASCII route supports `--native-y/-z` overlay |
| **No pre-installed template (from-scratch project, default)** | Route 2 | `compute_b1plus.py` | computes B1+ directly from the raw H-field in pure Python, **no B1+ tree node/template/dialog needed**, most faithful, zero dependencies |

> When a template is pre-installed, the most faithful quantitative curve is still the result of `model3d.EvaluateResultTemplates()` evaluated on CST's native sub-millimeter mesh (see Stage 3's alternative, Stage 4b); Route 1's role is to **overlay our exported curve on top of it** for comparison.

The unified export macro template is in `../../building-blocks/vba-blocks/field-export.md` (candidate-path loop + `ASCIIExport`).

### Route 1 (only for the "already has a template" case): ASCII export -> `plot_b1_profiles.py` (overlaid with the native curve)

Three export targets (YZ coronal plane / XZ sagittal plane / full-domain statistics), the export mechanism uses `FixedWidth .Step 1`:

```python
# Export A: Y-Z coronal plane (thin X slice) -- for the 1D profile + coronal 2D figure
export_yz = r"D:\ght\SAIS\MRI_agent\results\B1p_plane_yz.txt"
vba = ('Sub Main\n'
       'SelectTreeItem("2D/3D Results\\B1+ and B1-\\B1+ (f=0.21) [AC1]")\n'
       'With ASCIIExport\n'
       '  .Reset\n'
       f'  .FileName "{export_yz}"\n'
       '  .Mode "FixedWidth"\n'
       '  .Step 1\n'                        # 1-2mm uniform step (a physical width, not a point count)
       '  .SetfileType "ascii"\n'
       '  .UseSubvolume "True"\n'
       '  .SetSubvolume "-2", "2", "-325", "325", "-55", "2"\n'
       '  .ExportCoordinatesInMeter "False"\n'
       '  .Execute\n'
       'End With\nEnd Sub\n')
model3d._execute_vba_code(vba)


# Export B: X-Z sagittal plane (thin Y slice) -- for the sagittal 2D figure
export_xz = r"D:\ght\SAIS\MRI_agent\results\B1p_plane_xz.txt"
vba = ('Sub Main\n'
       'SelectTreeItem("2D/3D Results\\B1+ and B1-\\B1+ (f=0.21) [AC1]")\n'
       'With ASCIIExport\n'
       '  .Reset\n'
       f'  .FileName "{export_xz}"\n'
       '  .Mode "FixedWidth"\n'
       '  .Step 1\n'
       '  .SetfileType "ascii"\n'
       '  .UseSubvolume "True"\n'
       '  .SetSubvolume "-135", "135", "-2", "2", "-55", "2"\n'
       '  .ExportCoordinatesInMeter "False"\n'
       '  .Execute\n'
       'End With\nEnd Sub\n')
model3d._execute_vba_code(vba)

# Export C (optional): ROI/full-domain volume -- for peak/mean/CV statistics
export_full = r"D:\ght\SAIS\MRI_agent\results\B1plus_field.txt"
vba = ('Sub Main\n'
       'SelectTreeItem("2D/3D Results\\B1+ and B1-\\B1+ (f=0.21) [AC1]")\n'
       'With ASCIIExport\n'
       '  .Reset\n'
       f'  .FileName "{export_full}"\n'
       '  .Mode "FixedWidth"\n'
       '  .Step 2\n'                        # use 2mm for the full domain to control file size
       '  .SetfileType "ascii"\n'
       '  .ExportCoordinatesInMeter "False"\n'
       '  .Execute\n'
       'End With\nEnd Sub\n')
model3d._execute_vba_code(vba)
```

> Warning: under `FixedWidth`, `.Step` is a **step size (mm)**, applied uniformly across all three axes; it is no longer the old `FixedNumber`'s "points per axis". 1-2mm is straightforward and reliable.
> Warning: in the exported ASCII, the B1+ scalar value is in the Bz column (Bx=By=0); `plot_b1_profiles.py`/`plot_field.py --comp auto` automatically pick the non-zero column.
> Warning: `SetSubvolume` parameter order: xmin, xmax, ymin, ymax, zmin, zmax; coordinates stay in mm (`ExportCoordinatesInMeter False`).

### Route 2 (no pre-installed template / from-scratch project, default): HDF5-export the raw H-field -> `compute_b1plus.py`

```vba
With ASCIIExport
  .Reset
  .SetfileType "hdf5"
  .FileName "D:\ght\SAIS\MRI_agent\results\hfield_ac.h5"
  .Mode "FixedWidth"
  .Step 1                                  ' 1 or 2mm uniform
  .UseSubvolume True
  .SetSubvolume -60, 60, -150, 150, -120.5, -20.5
  .ExportCoordinatesInMeter False
  .Execute
End With
```
```
python <skill>/scripts/compute_b1plus.py     # first change H5_FILE / B0_PLUS_Z per CONFIG
```
> Warning: **when exporting the H-field**, `compute_b1plus.py`'s `B0_PLUS_Z` must match Stage 3's `cst_calc_b1_field_tool(b0_plus_z=...)` (default True=+z), otherwise B1+/B1- get computed swapped. Formula: `|B1+| = mu0*mu_r*|Hx - i*Hy|/2` (take -i for +z).
> Warning: HDF5 is a **structured array**, in **Fortran order** `(Nz,Ny,Nx)` — see `../../building-blocks/vba-blocks/field-export.md` for the reading hard rules.

### 1D profile evaluation coordinates (matching the CST template)
CST's `1e6XYZMag` template evaluates at the B1+ field's peak point. For the dipole project:
- **Y curve**: scan along Y at (X~0, Z~-11mm), range [-200, +200]mm. Z=-11 is within the substrate layer (just above the phantom surface), where the field varies gently, symmetrically, and approaches 0 at both ends.
- **Z curve**: scan along Z at (X~0, Y~-12mm), range [-50, 0]mm. Z=0 is the antenna conductor surface (an extremely strong near-field), Z=-20.5 is the phantom surface, -50 is 30mm deep inside the phantom. The curve rises monotonically to a sharp peak at Z=0.

> Warning: **a previous mistake**: the "peak point" Z=-5.9mm found from a coarse full-domain export lands in air (between the antenna and the phantom), which is not a valid evaluation location. The correct approach is to fix Z~-11mm (the substrate layer) for the Y curve, and set the Z curve's range to [-50, 0].

## Stage 4b (optional): export CST's native 1D template curves for comparison/calibration
The project typically already has a computed 1D profile in its templates (`Tables\1D Results\...(Y)`, `...(Z)`). Export as CSV for overlay comparison:
```python
import cst.results as cr, os
pf = cr.ProjectFile(project.filename(), allow_interactive=True); r3d = pf.get_3d()
def dump(tp, fn):
    with open(fn,"w") as f:
        for x,y in r3d.get_result_item(tp).get_data(): f.write(f"{x},{y}\n")
dump(r"Tables\1D Results\1e6XYZMag(B1+ (f=0.21) (AC1))_Abs (Y)", r"...\native_Y.csv")
dump(r"Tables\1D Results\1e6XYZMag(B1+ (f=0.21) (AC1))_Abs (Z)", r"...\native_Z.csv")
```
> Note: CST often has multiple Z curves: `_Abs (Z)` (wide range) and `_Abs (Z)_1` (localized to the phantom, fine, high peak). Choose the one matching your profile location for comparison, otherwise they will be mismatched.

## Stage 5: visualization + metrics (high-fidelity script)
```
python <skill>/scripts/plot_b1_profiles.py \
  --plane-yz results/B1p_plane_yz.txt \
  --plane-xz results/B1p_plane_xz.txt \
  --input results/B1plus_field.txt \
  --outroot results --name "B1+" --tag <project name> --unit uT --comp auto --scale 1e6 \
  --line-x 0 --line-y -12 --line-z -11 \
  --yrange "-200,200" --zrange "-50,0" \
  --native-y results/.../native_Y.csv --native-z results/.../native_Z.csv
```
- **Automatically creates a subfolder** `results/B1p_<tag>_NN/`.
- The 2D figures come from a high-resolution plane export (smooth, no pixelation), no longer the coarse 60^3 full-domain interpolation.
- The 1D profiles are evaluated at the correct locations (Z=-11mm for the Y curve, Z=[-50,0] for the Z curve) at sub-millimeter resolution, **matching the CST template's shape**:
  - Y curve: a symmetric peak approaching 0 at both ends (peak ~1.5µT)
  - Z curve: rises monotonically from ~0.8µT to a sharp peak of ~17µT at the antenna surface
- **The 1D curve's Y-axis starts at 0** (`set_ylim(bottom=0)`).
- Output: `*_2D_maps.png`, `*_1D_profiles.png`, `*_1D_alongY/Z.csv`, `stats.json`.

### Power normalization
The AC1 excitation is amplitude=10V into 50 Ohm. The B1+ produced by `cst_calc_b1_field_tool` is the absolute value (Tesla) at that excitation power.
- If the excitation = 50W (10V/50 Ohm = P=V^2/2R), normalizing to 1W gives `--scale = 1e6/sqrt(P_accepted/1W)`
- Reference value: P_accepted ~= 49.86W -> scale = 141621.5 -> peak B1+ ~= 1.91 µT @1W

### On the Tables tree being empty (normal for a from-scratch project)
`cst_calc_b1_field_tool` registers a 3D result node, and does not create a Post-Processing template. The Tables tree requires a pre-installed `.rtp` template. We compute the 1D profile ourselves via high-resolution export + `plot_b1_profiles.py`, achieving the same precision and curve shape as the CST template.

## Stage 6: report
Produce a report following `result-validation.md`, saved to the same subfolder: project path, tool/stage, evidence (result tree items + png/csv), metrics, validation status, **limitations**.

## Export strategy (uniformly use a `FixedWidth` fixed step size, pick clearly one of the two options, don't mix them)
- **Standard comparison figure (default)**: full computational domain + uniform `.Mode "FixedWidth"` / `.Step 2` (2mm), **no subvolume added**. Comparable with the reference (Dipole(3) verification = dipole_01: peak 1.93µT/CV 66%). Uses a fixed 1-2mm step rather than the old "60 points/axis".
- **Shallow-surface quantification**: use a phantom-focused sub-volume + `.Step 1` (1mm) high-resolution export (first read `x/y/z_plantom` to locate the phantom bbox). In this case **the 1D profile must be placed inside the phantom** (e.g. Z~-11mm), **and must not land on the PEC dipole plane** (Z~0/-1mm), otherwise the metal-edge singularity causes violent oscillation in the Y curve.

## Known limitations (must be reported honestly)
- **Step size determines fidelity**: an overly large `FixedWidth` step (e.g. >=4mm) undersamples the strong-gradient region near the phantom surface — the along-Y amplitude may be off, and the along-Z peak cannot be reproduced (the native peak can reach ~13-18 µT). **This is an export-resolution issue, not a physics error.** The expert recommendation is that **1-2mm** is sufficient; use 1mm when matching CST's native template curve. Use the native template curve as the quantitative reference.

## Reproduction summary
1 save -> 2 `start_solver`+poll -> 3 `cst_configure_ac_combine_tool` + `cst_run_circuit_cosimulation_tool("AC1")` -> 4 `cst_calc_b1_field_tool` (or `EvaluateResultTemplates` if a template is already installed) -> 5 export the field with `FixedWidth .Step 1/2`, choosing per case: **template installed** -> ASCII->`plot_b1_profiles.py` (+4b native curve overlay); **from-scratch, no template** -> HDF5->`compute_b1plus.py` -> 6 produce 1D+2D+CV -> 7 report.

