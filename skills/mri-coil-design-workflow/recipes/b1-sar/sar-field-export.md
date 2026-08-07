# Recipe: 10g SAR computation and export template (scalar + 3D field, fully automated headless)

> When to use: when you need CST's native IEEE 10g SAR either as a **scalar** (max SAR, for a FoM) **or as a spatially distributed field** (for profiles/heat maps, e.g. a paper-style SAR longitudinal profile).
> **Core conclusion (cracked 2026-07-16 on ind150, point-by-point verification matches GUI export to 0.000%): both the 10g SAR scalar and the 3D field can be obtained fully automatically headless, no GUI required.**
> The key is to follow two timing/path rules (see §0), otherwise it degrades into the illusion that "it can't be exported."
> SOP-level timing constraints are in `foundations/cst-simulation-sop.md` §B.4-B.6, §E.1-E.3. Script: `scripts/export_native_sar.py`.

---

## 0. Two make-or-break rules (memorize these first, or you will fail)

### Rule 1: the 3D field can only be exported inside the "in-memory window right after solving"
By default CST 2024 packs the field into `Result/Storage.sdb`, **not onto disk as `.m3d`**; but reading the field via `Result3D("<name>")` requires a real `.m3d` on disk.
The field is only materialized as `.m3d` **within the same in-memory session right after solving** (and during GUI interaction).
- Correct: **export the field within the post-solve session, without reopening, without another project open concurrently** -> succeeds.
- Wrong: **export after close->reopen, or in a session degraded by an abort/multiple open projects** -> the `.m3d` has already been archived back into Storage.sdb -> `Result3D`/`SelectTreeItem`/`ASCIIExport` all fail ("file does not exist" / "not available for current view", even the H-field can't be selected).
- **To export a field from a reopened old project -> re-solve first** (re-solving re-materializes the `.m3d`).

### Rule 2: don't select the node registered by `SAR.Create` — go through Result3D in two hops instead
The tree node that `SAR.Create` registers itself **cannot be seen** by headless `SelectTreeItem`/`ASCIIExport` (and Create also collapses the 2D/3D tree enumeration).
- Wrong: `SAR.Create` -> `SelectTreeItem "2D/3D Results\SAR\SAR10g"` -> `ASCIIExport`: **always fails** (this was the root cause of M3 once misjudging that "the GUI is required").
- Correct: `Result3D("SAR (f=freq) [1] (10g)")` Load from disk `.m3d` (bypassing the tree) -> `AddToTree` re-register -> then `SelectTreeItem`+`ASCIIExport`.

---

## 1. Prerequisites (solver / monitors)
- Solver **HF Time Domain, hexahedral** (CST's native 10g SAR only supports hexahedral; FD tetrahedral can't do it).
- Define a **powerloss volume field monitor** `loss (f=freq)` during modeling (+ h-field for B1+; e-field for E-field diagnostics).
- After solving, **first check whether the volume field monitor exists** (the first TD solve often misses it); if missing, run `start_solver` once more.
- If the project has a **SAR post-processing template** configured, the solve itself writes out the SAR `.m3d` (this is the case for the local fd_seg project); otherwise, run `SAR.Create` once in the same window to write it out.

## 2. Scalar 10g SAR (fully automated, reliable) — for the FoM
Within a **fresh post-solve session** (not saved/closed), Create + read the value inside one VBA block:
```vba
With SAR
  .Reset
  .PowerlossMonitor "loss (f=freq) [1]"   ' note the run suffix [1]
  .AverageWeight "10"                       ' 10 g
  .SetOption "IEEE C95.3"                   ' the valid averaging-method name ("IEEE 62704-1" reports invalid)
  .SetOption "no rescale"                   ' get the per-stimulation value; normalize by P_acc yourself in post-processing
  .SetOption "volaccuracy 0.05"
  .Create
  StoreDoubleParameter "fd_sarmax", .GetValue("max sar")
End With
```
- `GetValue("max sar")` **is independent of view/tree state and always succeeds**. Read it back with `model3d.RestoreDoubleParameter("fd_sarmax")`.
- Normalization: `no rescale` gives the per-stimulation value -> manually compute `SARmax_1W = fd_sarmax / P_acc` (measure P_acc per case).
  - Warning: **don't trust `scale accepted`**: it **silently fails** under severe mismatch at a bare port (returned value == no-rescale, when it should differ by 1/P_acc). **Self-check**: the no-rescale vs. scale-accepted ratio should be ~1/P_acc; if it's 1, it has failed. See memory [[cst-sar-scale-accepted-fails-on-mismatch]].
- Other usable keys: `total sar` / `point sar` / `max sar x` (note: locally `max sar y/z` often returns a sentinel -1e102 and is unreliable).

## 3. 3D 10g SAR field (fully automated headless) — for profiles/hotspot distributions

**Script `scripts/export_native_sar.py` already wraps both methods** (inside `cst_run_python_tool`, `import export_native_sar as E`).

### 3.1 Prerequisite: make sure the SAR `.m3d` is on disk (within the post-solve window)
- If the project has a SAR template -> solving produces `Result/SAR (f=freq) [1] (10g).m3d` directly.
- If not -> within the same window, run `E.create_native_sar(de, rescale="no rescale")` once to trigger SAR.Create (default label, writes the `.m3d`), then normalize manually by measured accepted power.
- **Verify**: `ls Result/*.m3d` should show `SAR (f=freq) [1] (10g).m3d` (+ e/h/loss). If not visible, Rule 1's window wasn't right — re-solve first.

### 3.2 Method A: pure-Python read of the scalar array (no file, no coordinates)
```python
r = m.Result3D("SAR (f=freq) [1] (10g)")   # On the Python side this directly returns a RemoteObject, Loading the .m3d from disk
nx, ny, nz = r.GetNx(), r.GetNy(), r.GetNz()
import numpy as np
a = np.asarray(r.GetArray("xre"))          # scalar fields are stored in the xre component
sar = a.reshape((nz, ny, nx))              # index = ix + iy*nx + iz*nx*ny -> [iz,iy,ix]
# r.GetUnit()="W/kg", r.GetFrequency()=298, sar.max()=the peak value
```
- Use case: a quick read whenever you only need max/statistics, or can get coordinates some other way. **Native non-uniform hex mesh** (measured 79x98x80 on ind150).

### 3.3 Method B: AddToTree + ASCIIExport to a coordinate-carrying HDF5 (a direct replacement for GUI export)
```vba
Dim res As Object
Set res = Result3D("SAR (f=freq) [1] (10g)")
res.AddToTree "2D/3D Results\SAR", "SAR_auto"   ' the key step: re-register into the tree
```
```vba
SelectTreeItem "2D/3D Results\SAR\SAR (f=freq) [1] (10g)"  ' this node is now selectable = True
With ASCIIExport
  .Reset
  .FileName "<out>.h5"
  .SetFileType "hdf5"
  .Mode "FixedWidth"
  .Step 2
  .UseSubvolume "True"
  .SetSubvolume "-40", "40", "-240", "240", "-20", "0"
  .ExportCoordinatesInMeter "False"
  .Execute
End With
```
- One-shot: `E.export(de, out_h5)` (subvolume/step already set by default), or `E.full_pipeline(de, out_h5)` (wraps Create->AddToTree->Export entirely).
- Warning: after AddToTree, the node that gets selected is the **real node name on disk**, `SAR (f=freq) [1] (10g)`, not the `SAR_auto` label you gave it — the script already handles this.

### 3.4 Export subvolume range (mm, generic for a phantom-top longitudinal profile)
| Axis | min | max | Meaning |
|---|---|---|---|
| X (transverse) | -40 | 40 | the antenna is ~10mm wide, +/-40 is enough |
| Y (antenna long axis/longitudinal) | -240 | 240 | a 30cm antenna's ends are at +/-150, use +/-240 to include end-field |
| Z (depth, top surface = 0) | -20 | 0 | the surface layer (where SAR is highest); the profile only needs the surface layer |

Step size = 2 mm.

**Data-prep D1 exception:** regular-dipole complete cases use the project
phantom/loss non-zero box, not the generic surface profile above:

```text
X: -135 to 135 mm
Y: -160 to 160 mm
Z: -120.5 to -20.5 mm
```

`scripts/export_native_sar.py::export_data_prep_sar10g` defaults to this D1 box.
For 210 MHz data-prep projects it also tries CST result labels with `f=0.21`
before `f=210`, because the project unit is commonly GHz.

### 3.5 Normalization
- Production default is **`no rescale`**: exported field values are per stimulation, so read the HDF5 raw values and divide by measured `P_acc` to get W/kg @ 1 W accepted.
- Self-check: raw `field.max()` should match `GetValue("max sar")` from the same no-rescale SAR calculation within <5%; after normalization, `field.max()/P_acc` is the @1W accepted peak.
- `scale accepted` may be used only after the §2 mismatch self-check proves it works. If it is trustworthy, the exported field is already @1W accepted and must not be divided by `P_acc` again.
- Data-prep D1 always follows `no rescale` + manual `P_acc` division unless the user explicitly asks for a scale-accepted diagnostic comparison.

### 3.6 Reading (Python)
h5 structure = `SAR (Nz,Ny,Nx)` real scalar + `Mesh line x/y/z` (note: unlike the H-field's complex structure, SAR is a real scalar, read directly via `f["SAR"]`).
```python
import h5py, numpy as np
with h5py.File(path,"r") as f:
    my=np.asarray(f["Mesh line y"]).ravel(); mz=np.asarray(f["Mesh line z"]).ravel()
    sar=np.asarray(f["SAR"]).reshape((mz.size, my.size, -1), order="F")  # already @1W accepted
line = sar[int(np.argmax(mz))].max(axis=1)  # surface layer, take max along x -> the hottest longitudinal SAR(y) profile, @1W
```


## 4. A pitfall to avoid: E-field point-proxy is falsified (do not use)
**Do not** derive a SAR profile from the E-field via `SAR ~ 0.5*sigma*|E|^2/rho` — this has been falsified.
Measured comparison (ind150, E-proxy vs. native SAR):
- The spatial distribution is **opposite**: the native double peak is at y=+/-112mm with a central dip of 0.56; the E-proxy peak is at y~30mm near the center, with **no double peak** (`|E|^2` is strongest where charge accumulates at the conductor ends, whereas true 10g SAR is determined by near-field power deposition).
- Early on (in the M3 subset) the peak height was also off by ~100x in magnitude, with reversed ordering.
- Averaging over a 3D cube can't fix this (the end-peak is a genuine `|E|^2` distribution, not noise).
- The shapes only happen to be close when the antenna is **unsegmented, with a naturally single central SAR peak** (but magnitude/end behavior still deviate). **When you need the correct spatial SAR distribution -> use the native field from §3, never the E-field proxy.**

## 5. One-sentence decision guide
- Need **FoM / optimum point / max-SAR scalar** -> §2, fully automatic, reliable, run it without hesitation.
- Need **spatial SAR distribution/profile figure** -> §3's native SAR field, exported fully automatically (follow Rules 1 and 2: within the post-solve window + Result3D.Load+AddToTree). Script: `E.full_pipeline`. **Never use the E-field proxy** (§4).
- Manual GUI export (MRI Toolbox -> General SAR Result -> Export 3D Field Result) is still a **reliable fallback**, but is no longer the only path.

## 6. GUI fallback steps (when headless truly can't be made to work)
1. Open the `.cst` (containing the loss field; if not, run the solver first).
2. **Post-Processing -> Result Templates -> MRI Toolbox -> General SAR Result**: Power loss=`loss (f=freq) [1]`; Weight=10g; Method=IEEE C95.3; Rescaling=**scale accepted**; remember the Label. Evaluate -> the SAR field appears under the tree at `2D/3D Results\SAR\`.
3. **Result Templates -> 2D and 3D Field Results -> Export 3D Field Result**: select that SAR field; **3D Export in Volume**; check Use Subvolume (range per §3.4); format **HDF5**.
4. File-name convention: `log/SAR (f=freq) [1] (10g)_<suffix>.h5`.

Related: [[b1-field-pipeline]], [[cst-sar-scale-accepted-fails-on-mismatch]], memory [[cst-sar-line-eproxy-and-steadystate]], `foundations/cst-simulation-sop.md`.

