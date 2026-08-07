# CST Operation Notes — read BEFORE driving CST

Hard-won operational knowledge about *how CST actually behaves* through the MCP. Read this first; it prevents the trial-and-error that otherwise dominates a session.

## FIRST: read the bundled official API docs

The MCP ships the official CST references — **consult them instead of guessing API signatures**:
- `external/CST-MCP/vendor/cst-runtime-cli/devkit/references/cst-official-api-reference.md` (Python API: cst.interface, cst.results, Model3D, Result3D, …)
- `external/CST-MCP/vendor/cst-runtime-cli/devkit/references/vba-official-reference.md` (VBA object model)

When unsure how a call works (arg count, method name), grep these files first. Most of this session's errors ("Expecting N positional arguments", wrong method names) were avoidable by reading them.

## GUI live-repaint: depends on connection freshness (root cause found 2026-07-15)

Whether the CST front-end repaints in real time as the MCP builds depends on how the MCP
connected:

- **Fresh connection + new project → repaints LIVE (verified 2026-07-15 rehearsal).** Starting
  from a freshly-connected session and `cst_new_project_tool`, every `cst_add_to_history_tool`
  step showed up immediately in the tree + 3D viewport; schematic device adds showed live too.
  Front-end view control also works: `ResetViewToStructure` (3D VBA), and Python object methods
  `project.schematic.ActivateSchematicView()` / `ActivateAssemblyView()` / `ZoomToFit()`.
- **Stale connection (MCP attached to a long-open session) → may NOT repaint (seen 2026-07-14).**
  The already-open window showed empty tree / blank viewport even though the model was fully in
  memory and on disk. In that state in-process redraw commands didn't help the foreground window.
- **Note: closing a project drops the MCP session** (`cst_project_info` → `connected:false`).
  Reconnect with `cst.interface.DesignEnvironment.connect(<pid>)` (pid from `cst_detect_tool`),
  then `cst_new_project_tool` re-takes the session — this is exactly what makes the connection
  "fresh".

- **This is a display concern, NOT data loss.** Data is always in memory / on disk; confirm via
  `Solid.GetNumberOfShapes()` (3D) or `Block` iteration (schematic), and `project.save()`.
- **保底**: if a stale session won't repaint, `save()` then close+reopen the project in the GUI
  reloads the tree from the (correct) file.
- **For demo recording** (keep everything visually in sync): see `recipes/build/demo-recording-mode.md`.

## The GUI tree / result store is NOT refreshed after operations (READ-AFTER-WRITE)

Repeatedly this session, reads came back EMPTY right after an operation, then worked after a refresh. Rules:

- **After a solve / combine / template eval, the nav tree lags.** `Resulttree.GetFirstChildName(node)` returns "" and `SelectTreeItem(path)` returns False even though the data exists on disk.
- **`cst.results.ProjectFile` also caches** — re-open it (`cr.ProjectFile(path, allow_interactive=True)`) after `project.save()` to see new results. It lists only 0D/1D items, never 3D fields.
- **To force a refresh**: `project.save()` first; then for the 3D nav tree, `model3d.EvaluateResultTemplates()` or a full `Rebuild` can repopulate parent nodes; re-opening the project (close+open) reloads the tree from disk.
- **Verify before you act on a read**: check `SelectTreeItem(path) == True` before `ASCIIExport`; if a field read returns empty, save+refresh+re-read rather than concluding it's missing.
- **3D fields are reliably readable via `Result3D`, bypassing the tree**: `r = model3d.Result3D(""); r.Load(r"...\Result\<name>.m3t")`, then `r.GetArray("Xre"/"Xim"/…)`. This does NOT depend on tree refresh. (It does not give point coordinates, though.)

## AC circuit co-simulation Combine Results = PURE API (no GUI, no popup)

**Corrected 2026-07-13** (earlier notes wrongly called this GUI-only — see memory [[ac-combine-b1-template-are-api]]). Use the dedicated tool:
```
cst_configure_ac_combine_tool(task_name="AC1", fmin=..., fmax=..., unit="GHz",
                              port_name="1", block_name="MWSSCHEM1",
                              amplitude=10)
                              # monitor_filters default = [":hfield:"] — NEVER use "*"!
cst_run_circuit_cosimulation_tool("AC1")
```
Why no popup: the tool sets `SetProperty "docombineresults","True"` + `"blocknameforcombineresults","<MWS block>"` (the scripted equivalents of the GUI "Combine results" checkbox + "Block" dropdown) BEFORE `.Update`. The Abort/Retry/Ignore monitor-mismatch dialog ONLY fires in two scenarios: (1) combine not enabled before running, or (2) the filter matches a monitor with no combinable volume field (e.g. `surface-current`). The second is the real trap: `"*"` matches ALL monitors including surface-current which has no volume field → popup. **Always use `[":hfield:"]`** for B1+ (the default); for SAR add `["h-field (f=0.21)","loss (f=0.21)"]`. Excitation order matters: `SetComplexPortExcitation` MUST precede `SetPortSourceType("1","Signal")` (all handled inside the tool). Source: `simulationtaskobject.htm` in CST Online Help. After it runs, verify `[AC1]` H-field on disk / in tree, then compute B1+.

## B1+ post-processing = PURE API (no template install, no dialog)

**Corrected 2026-07-13.** The "Calc B1+" MRI-Toolbox template is just a VBA macro (`Library/Result Templates/MRI Toolbox/Calculate B1+ and B1-^+MWS+DS.rtp`) whose params are all `GetScriptSetting`. Rather than depend on it being installed, use the dedicated tool that transcribes its math directly:
```
cst_calc_b1_field_tool(h_monitor="H-Field\\h-field (f=0.21) [AC1]", mu_r=1.0, b0_plus_z=True)
```
It runs `Result3D.Combine` (component enum 0=Xre 1=Yre 2=Zre 3=Xim 4=Yim 5=Zim; B1+ lands in Z contour) and registers the node via `ResultOperator3D.AddToTree` under `2D/3D Results\B1+ and B1-\B1+ (f=...) [AC1]`. `mu_r=1.0` gives B in Tesla (×1e6 → µT). **Because it registers the tree node, this also fixes the old "3D field not tree-registered / no coords for ASCIIExport" gap** — SelectTreeItem+ASCIIExport works afterwards.
- Alternative when a project ALREADY has the template installed: `model3d.EvaluateResultTemplates()` (also yields 0D/1D template tables).
- Fallback (fully manual math): `Result3D.Load` the H-field + compute `(Hx+i·Hy)/2` in Python — but that path loses coords; prefer the tool.

## General discipline

- Read the official API doc for a call before using it.
- Prefer `Result3D.Load` for 3D field data over tree-dependent ASCIIExport.
- After any write, `save()` then refresh before reading; don't conclude "empty/missing" from a stale read.
- Keep only one project open when possible; with multiple open, `de.active_project()` is unreliable — use the handle returned by `open_project(path)`.
