# Recipe: Parameter sweep + FoM optimization (B1+/SAR trade-off)

**Goal**: sweep a geometric/component parameter (dipole length, inter-segment lumped element value, spacing, ...) and find the optimal design using the figure of merit
**FoM(d) = B1+(d)/sqrt(SAR_max)**. Verified end-to-end on the Raaijmakers 2016 fractionated dipole reproduction (FD_Optimize,
298MHz). Applicable to any "sweep one variable, compare deep transmit efficiency vs SAR" single-coil optimization.

Related: `recipes/build/dipole-from-scratch.md` (modeling), `building-blocks/vba-blocks/field-export.md` (field export),
`recipes/b1-sar/b1-field-pipeline.md` (B1+), `recipes/b1-sar/sar-field-export.md` (SAR computation/export),
`foundations/cst-simulation-sop.md` (mandatory SOP), `pitfalls/sar.md` (SAR pitfalls).
Memories `cst-sar-scale-accepted-fails-on-mismatch`, `b1-sar-optimization-no-per-case-matching`.

---

## 0. Normalization principle (think this through first, otherwise the conclusion will be wrong)

- **Both the numerator and denominator of the FoM are normalized to 1W accepted power**: B1+ prop-to 1/sqrt(P), SAR prop-to 1/P.
- **No need to re-match at every sweep point**: the antenna is linear, so a fixed accepted power => fixed feed-terminal current => fixed current distribution =>
  the B1+ and SAR distributions are determined, and their ratio depends only on geometry + load, not on the feed front-end. Normalizing by accepted power decouples the
  geometry being optimized from the matching. "Per-point matching + forward-power normalization" is equivalent to "no matching + accepted-power normalization", and the latter saves N matching runs.
- **Hard rule: measure the accepted power at every point individually** (`1D Results\Power\Excitation [1]\Power Accepted per Port\Port 1`
  @ the operating frequency), **never assume 1W excitation = 1W accepted**. Under severe mismatch, the two can differ by tens to thousands of times.

## 1. Solver: native 10g SAR requires Time Domain (hexahedral)

CST's native IEEE 10g SAR **only supports a hexahedral mesh**; HF Frequency Domain tetrahedral meshing cannot do SAR. A low-Q, lossy
load (a dipole against tissue, S11 ~ -0.8dB broadband) is also better suited to TD, and matches most papers' FDTD. Solver block:
```vba
ChangeSolverType "HF Time Domain"
Solver.FrequencyRange "freq-100", "freq+100"
With MeshSettings
    .SetMeshType "Hex"
    .Set "Version", 1
End With
With Solver
    .Method "Hexahedral" : .SteadyStateLimit "-40" : .StimulationMode "1"
End With
```

## 2. Per-case operation sequence (order must not be shuffled — every step here is a pitfall we hit)

For each sweep point, on an **independent project copy**:

1. **Model + change parameters**: inject the parameter override into the `define parameters` block (`StoreParameter`, force-assign),
   rather than modeling first then doing `add_to_history`+`full_history_rebuild` — the latter causes the first solve to miss the volume field monitor.
2. **Solve (async + guarded re-solve)**: `save()` -> `start_solver()` -> poll `is_solver_running()`.
   **The TD volume-field monitor only appears on the second solve**: in a `cst.interface` session, the first TD solve often only produces S-parameters+1D power,
   not the 3D volume field (h-field/loss). After solving, check for the field node, and **if missing, run `start_solver` once more**:
   ```python
   def solved_with_fields(m):
       return any('H-Field' in str(i) and 'h-field' in str(i) for i in m.get_tree_items())
   ```
   Don't poll too aggressively: `is_solver_running()` can transiently return False during the transition, and calling start again then hits "Simulation already
   running" — poll at intervals of >=2s, and sleep another 3-4s after exiting the loop.
3. **Export the H-field (must happen before computing SAR!)**: `SAR.Create` changes the active view, after which `ASCIIExport.Execute`
   reports "The ASCII export option is not available for the current view". Fixed order:
   **solve -> guarded re-solve -> export H-field -> then compute SAR**. For export use `project.model3d._execute_vba_code`
   (acts on the correct project object), which is more stable than the MCP `cst_execute_vba_tool` (the latter's active-project binding on the Python side
   gets out of sync after `open_project`). Remember to wrap multi-statement VBA in `Sub Main ... End Sub`.
4. **Compute 10g SAR** (see §3).
5. **Read the accepted power**: `cst.results` -> `get_3d().get_result_item(path, run_ids[-1]).get_data()`.
   **Must pass the run id**: `get_result_item(path, r3.get_all_run_ids()[-1])` (changing a parameter deletes the run id=0 results).
6. **Extract metrics**: read the H-field HDF5 in Python, compute the B1+(d) center-column profile (x 1/sqrt(P_acc)), SAR_max (normalized per §3),
   append a row to `cases.csv`.

## 3. 10g SAR computation — the `scale accepted` silent-failure-on-mismatch trap (the biggest pitfall in this recipe)

The CST SAR post-processing object (2024 API, not `SetLossMonitorName`):
```vba
With SAR
    .Reset
    .PowerlossMonitor "loss (f=freq) [1]"   ' note the run suffix [1]
    .AverageWeight "10"                      ' 10 g
    .SetOption "IEEE C95.3"                  ' averaging method ("IEEE 62704-1" reports invalid)
    .SetOption "no rescale"                  ' see below: don't trust "scale accepted"
    .SetOption "volaccuracy 0.05"
    .SetLabel "SAR10g"
    .Create
    StoreDoubleParameter "fd_sarmax", .GetValue("max sar")   ' W/kg per stimulation
End With
```
- **`SetOption "scale accepted"` silently fails to rescale under severe mismatch at a bare port**: the returned value is **exactly equal** to `no rescale`
  (it should differ by 1/P_acc). I.e. what you get is a per-stimulation value, not a per-1W-accepted value.
- **Self-check**: on the same project, compute `GetValue("max sar")` with `no rescale` and with `scale accepted` separately; the ratio should be ~1/P_acc;
  if it equals 1, the "accepted" normalization has failed.
- **Correct approach**: use `no rescale` to get the per-stimulation SAR, and **manually divide by the measured P_acc** (same principle as dividing B1+ by sqrt(P_acc)).
  Violating this makes the direction of the FoM's SAR component entirely wrong (in practice this once produced the anti-paper result "short antenna has low SAR, optimum at L=50mm").
- **The `GetValue("max sar x/y/z")` location query** often returns a sentinel value (-1e102) right after a one-shot Create; only the `max sar`
  scalar is reliable. To get the location you must `SetLabel`+`Load` first, then GetValue (and even then it's prone to going stale).

## 4. FoM aggregation + paper-style figures

`FoM(d)=B1+(d)/sqrt(SAR_max)`, both B1+ and SAR @1W accepted. Method for reproducing paper-style figures (copy this to reproduce the Fig.3/Fig.4 style):
- **(a) Absolute depth profile**: overlay B1+(depth) for each sweep value.
- **(b) Relative to a reference**: divide by the profile of some reference design (the paper uses a mid-range value like a 25cm antenna), highlighting which depth is best.
- **(c/f) Some quantity vs. the swept variable**: three depth lines at 5/10/15cm, **each individually normalized to that line's own max value** (0-1),
  making it easy to compare "relative optimum points" on the same figure without being masked by absolute-magnitude differences.
- **(d) SAR longitudinal 1D profile**: identify single/double peaks (a short antenna's E-field is dominated by its two ends -> double peak).
- **Color scheme + axis conventions (readability)**: for a bundle of sweep curves, use **high-contrast discrete colors + a linestyle cycle** (e.g.
  red/orange/yellow/green/cyan/blue/purple/magenta/black x solid/dashed/dash-dot/dotted), **do not use a smooth gradient like viridis** —
  a gradient makes it hard to distinguish adjacent sweep values where curves converge at depth. Align the depth axis with the original paper: **fix it to 0-20cm, 5cm ticks**
  (`set_xlim(0,20)` + `set_xticks(0..20,5)`), don't let each case auto-scale its range (requires exporting the field out to -200mm to cover 20cm).
  Bold the reference antenna's curve to serve as an anchor baseline. `plot_fig3_full.py` already implements this convention and can be reused directly.

### 10g SAR longitudinal profile export (for (d))
SAR is a **real scalar field** (not the complex structure of the H-field). **Warning: do not go through `SAR.Create -> SelectTreeItem -> ASCIIExport`** — the node registered by `SAR.Create` is not visible to headless `SelectTreeItem`/`ASCIIExport` (and it collapses the tree), so this path always fails. **The correct approach** (verified in `recipes/b1-sar/sar-field-export.md`, script `scripts/export_native_sar.py`):
```
(within the same in-memory window after solving, do not reopen)
Result3D("SAR (f=freq) [1] (10g)")  ' Load from disk .m3d, bypassing the tree; on the Python side m.Result3D(name) returns the object directly
-> res.AddToTree "2D/3D Results\SAR","<label>"   ' re-register into the tree -- the key step
-> SelectTreeItem that node (now = True) -> ASCIIExport a shallow thin-layer HDF5 (z in [-20,0])
-> Python: sar.reshape((Nz,Ny,Nx),order='F'); take the surface z(max), then max along x -> SAR(y)
```
See `recipes/b1-sar/sar-field-export.md` for detail (including the "post-solve memory window" make-or-break rule + the E-field-proxy falsification) and `pitfalls/sar.md`.

## 5. Session/process hygiene
- Running parallel independent instances (`DesignEnvironment.new()`) works locally (CST supports 2 instances), but independent sessions have issues
  such as the TD first-solve missing fields, orphaned processes leaving `.lok` files, and the DC daemon holding a directory lock — **driving them sequentially through MCP is more stable**.
- case-id is **never reused** (to avoid a locked directory blocking `save()`); for orphaned DEs left behind by a crash, kill precisely by PID, keeping the MCP one.
- A read immediately following a write can go stale: the 3D navigation tree can collapse after `save()`, with `SelectTreeItem` returning False —
  export immediately after solving (don't save first), or close->reopen->`cst_active_project_tool` to rebind and refresh.


## 6. Reusable scripts (FD_Optimize/scripts/, directly transferable)
- `build_fd_project.py` — generates named history-block VBA from topology parameters (numeric knobs stay as CST parameters for sweeping).
- `extract_case_metrics.py` — H-field HDF5 -> B1+ (5/10/15cm) + SAR_max -> one cases.csv row (`--sarmax` scales by
  P_acc by default; `--sarmax-already-1w` only when the accepted-power normalization is confirmed to already be in effect).
- `fom_sweep.py` — cases.csv -> FoM summary + FoM-vs-sweep-quantity plot + optimum-point json.
- `plot_fig3_full.py` — paper-style multi-panel (a-f) plotting template.
