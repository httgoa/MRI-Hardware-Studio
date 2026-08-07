# Reproduction 04: Patch Antenna (FD) (official Component Library)

> Phase 2, fourth case (situational; general antenna fundamentals, filling in the FD Tet + Waveguide Port + Boolean pipeline). Official reference (read-only): `references_cases/Patch Antenna (FD).cst`. Reproduction project: `results/patch_fd_repro/patch_fd_repro.cst`.
>
> **Result: numerically exact reproduction** — S11(f) matches the official case point-for-point |Δ| < 1e-9 dB (1001-point full band), resonance 2.400 GHz @ −7.72 dB exactly matches, Z_line=49.60Ω vs official 49.6Ω, peak Directivity=7.07 dBi @ +z. See `results/patch_fd_repro/output/REPORT.md` for detail.

## Variant identification (5-variant table on the tutorial's first page)
Patch Antenna has 5 official variants: **(TD)** / **(FD)** ← this one / Array / Array Combine / Array Simultan. TD and FD are **different solver branches of the same physical model** (the only geometry difference: the FD version changes the patch from an h=0.07mm cylinder to a zero-thickness PEC sheet; the solver switches from HF_TRANSIENT to HF Frequency Domain). See [[mcp-repro-pitfalls]]#5.

**The official FD case's "hidden teaching structure"**: under `1D Results\S-Parameters\` there are both `S1,1` (the FD Tet result) and `S1,1_(Mesh Pass=1)_TD` / `_(Mesh Pass=2)_TD` (retained TD Hex curves, from the tutorial section "Making a Copy of Transient Solver Results"). **Only align against `S1,1` (FD)**, not the TD curves.

## Reference answer (tutorial htm + official `Model.mod` + `Model.log`)
- **Physics**: circular patch (R=23.2 mm, original h=0.07 mm / the FD version is zero-thickness), coax feed offset 9.2 mm, Substrate 60×60×0.7 mm ε=2.33 lossless, PEC ground 2.1 mm thick. 2.4 GHz resonance, sweep 2–3 GHz.
- **Parameter table**: empty (`Parameters.json` = `{"parameters": null}`) — all dimensions hardcoded.
- **Port**: Waveguide (coax TEM mode), `Coordinates="Picks"` + `PortOnBound="True"`, Xrange −4..4 / Yrange 5.2..13.2 / Zrange −2.8..−2.8. **Z_line=49.6Ω is naturally close to 50Ω, no matching network needed**.
- **Boundaries**: X/Y open, Zmin **electric** (equivalent ground plane), Zmax expanded open.
- **Monitors**: `farfield (f=2.4)` @ 2.4 GHz.
- **Solver**: `FDSolver` Tet 2nd order (OrderTet Second), `Stimulation "All"`, `AccuracyTet=1e-4`, `MeshAdaptionTet=True`, `AddSampleInterval "2.4","2.4","1","Single","True"` (forces the monitor frequency into the sweep), `SweepMinimumSamples=3`. `MeshAdaption3D.SetType "HighFrequencyTet"` + ExpertSystem + MinPasses 3 / MaxPasses 20 / MaxDeltaS 0.02.
- **Official Model.log numerical anchors**: mesh cells=30433, DOF=180255, broadband sweep 7 samples, total solver time 31 s.

## Reproduction path (**passed**)
14 named `cst_add_to_history_tool` blocks → `start_solver()` async, completes in ~30 s → `cst.results.ProjectFile` reads the result tree → point-for-point alignment against the official .cst. Full block list in REPORT.md §"Reproduction pipeline".

**Key reproduction techniques**:
- Solver parameters **don't copy** the official `.mod`'s full `With FDSolver/IESolver/MeshAdaption3D` setter dump (100+ properties) verbatim — only issue the necessary 15–20. This was the biggest lesson of this case (see pitfall #1).
- The official `.mod`'s `SetSolverType "HF_TRANSIENT"` + `With Solver ... TD parameters` section (leftover TD template) is harmless to keep in the FD reproduction, but can also be deleted.
- **Use `cst.results.ProjectFile(<path>, allow_interactive=True)`** to read the reference .cst's 1D results directly for numerical alignment — 8 orders of magnitude more precise than comparing screenshots.

## Key pitfalls (new to the knowledge base, all written back to [[mcp-repro-pitfalls]])
1. **Solver parameter blocks in the official .mod history bring in newer-version APIs → pops "No such property or method" and blocks execution**: the official Patch FD `.mod` was saved by CST 2024.0, and `IESolver.CalculateModalWeightingCMA` doesn't exist in older CST versions — replaying the whole `With IESolver` block pops a non-modal window that **blocks subsequent `add_to_history` calls**. **Rule: the official .mod's large solver parameter set is a "template dump" — only issue the necessary setters** (Method/Order/Stimulation/Accuracy/MeshAdaption on/AddSampleInterval), leave the rest at CST's default.

2. **`cst_save_project_tool`'s parameter is named `path`, not `save_as_path`**: passing the wrong name silently fails → the project just gets saved to a temporary `Untitled_N.cst` + a GUI "Save As" dialog pops, blocking subsequent MCP calls. **When save hangs, the first reaction should be to check the parameter name in mcp_server.py, not wait for the user**.

3. **`cst_run_python_tool`'s parameter is named `code`, not `python_code`**. Scope: `de` / `project` / `model3d`; `result = ...` is returned. To read the result tree of a non-active .cst: `cst.results.ProjectFile(path, allow_interactive=True)` (if that .cst is open in the CST GUI); use `False` only when it's purely on disk and CST isn't holding it open.

4. **Bash sandbox**: `python -c "long string"` is prone to being blocked; **always avoid a `cd` prefix**; use absolute paths + a short script file (write into `log/foo.py`, run `python "<absolute path>.py"`). This also matches the skill scripts directory's official approach.

5. **The official FD case is a teaching variant of "run TD → copy results → convert to FD"**: under `1D Results\S-Parameters\` there are both `S1,1` (FD Tet) and `S1,1_(Mesh Pass=*)_TD` (retained TD Hex curves). Numerical alignment should **only use `S1,1` (FD)**, don't mix in the TD pass curves.

6. **`FarfieldPlot` API pitfalls, reiterated**:
   - There is **no** `FarfieldPlot.GetValue(theta)` — I fabricated this → got "Method or property not found".
   - There is **no** `Plot.DrawArrows` / `Plot.CaptureCurrentPlot` — fabricated again. The screenshot API path hasn't been worked out and needs separate verification.
   - fieldComponent has **no** "Directivity" — (&H8000ffff) Invalid field component; `GetListItem(idx, "Point_T")` in the patch case returns **the angle value itself** (0/90/90), not a field value — meaning "Point_T"'s semantics differ from what I expected; the correct component to use still needs verification.
   - **The reliable farfield read method this time**: `SelectTreeItem("Farfields\farfield (f=2.4) [1]")` → `FarfieldPlot.Reset:.Plottype "3d":.SetPlotMode "Directivity":.SetFrequency 2.4:.Plot:.GetMax()` → **returns the 3D peak Directivity in dBi** (7.068 for this case).

7. **The official FD case's 3D farfield result was overwritten by the TD flow**: `Resulttree.GetFirstChildName("Farfields")` only returns `Farfields\Farfield Cuts`, with no `farfield (f=2.4) [1]` node → unable to get a peak-directivity numerical anchor from the official .cst. The tutorial text only guarantees "main lobe points +z" as a qualitative alignment point.

8. **`Solid.CreateShapeFromFaces "newname","component","material"`** parameter order: new name → component → material, paired with a preceding `Pick.PickFaceFromId "component1:patch","1"`. This is the key API for rebuilding the patch cylinder as a zero-thickness sheet in the FD version, worked out for the first time here.

## Results comparison (honest)
| | My reproduction | Official FD | Conclusion |
|---|---|---|---|
| S11 full band (1001 points) | reproduced | reference | **|Δ| < 1e-9 dB consistent across the full band** — matched |
| Resonance frequency | 2.400 GHz | 2.400 GHz | matched |
| min S11 | −7.7158 dB | −7.7158 dB | matched |
| Z_line | 49.60 Ω | 49.6 Ω | matched |
| Z_wave | 246.80 Ω | 247 Ω | matched |
| Broadband sweep sample count | 7 | 7 | matched |
| Sample-frequency order | fully consistent | | matched |
| Peak 3D Directivity | 7.068 dBi | not retained officially | qualitative +z check only |
| Rad. Efficiency | 1.010 | not retained officially | lossless model theoretical=1, matched |
| Tot. Efficiency | 0.839 | not retained officially | =1−\|S11\|², matched |

## Knowledge-base validation conclusion
- **HF-notes validation**: planar antenna = FD Tet 2nd order + Zmin electric ground + open Zmax + forced center-frequency sample — [[cst-hf-fundamentals]] needs supplementing if it doesn't yet cover the minimal FD Tet parameter set.
- **Help-index validation**: `Waveguide Port` / `FDSolver.AddSampleInterval` / `MeshAdaption3D.SetType HighFrequencyTet` should be added to [[cst-help-index]] §"Ports" / §"Solver".
- **Variant identification re-confirmed**: Patch Antenna has 5 variants, and the official FD case keeps the TD pass curves for teaching comparison → reinforces [[mcp-repro-pitfalls]]#5.
- **Solver-parameter-copying caution**: a general rule, not just for FD cases — all official .mod large solver parameter blocks (TD/FD/IESolver/MeshAdaption) may bring in newer-version APIs; replays should be trimmed down.

## Value for the MRI main line
- **First complete run of the FD Tetrahedral solver pipeline** — the correct solver choice for high-Q loaded MRI coils ([[cst-red-lines]] says "narrowband/high-Q loaded MRI coils" → use FD).
- **First successful run of Waveguide Port with Picks + PortOnBound** — the previous 3 cases all used discrete ports; this is an important API-surface addition.
- **First successful run of the Boolean pipeline (`Solid.Add` + `Solid.Insert` + auto-insert)** — MRI coil shield/cavity modeling often needs similar operations.
- **Numerically-exact reproduction methodology**: proves that "step-by-step history replay + trimmed solver setters + point-for-point `cst.results` diff" can reach official-grade numerical agreement (<1e-9 dB); a reference standard for future MRI paper-reproduction acceptance criteria.

Related: [[repro-01-dipole-antenna]] [[repro-02-dipole-array]] [[repro-03-mri-coil]] [[cst-hf-fundamentals]] [[cst-help-index]] [[textbook-case-readonly]] [[mcp-repro-pitfalls]].

