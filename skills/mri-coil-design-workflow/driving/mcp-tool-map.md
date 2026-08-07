# CST MCP Tool Map

Maps workflow steps to the CST MCP's tool names. The MCP exposes ~53 tools total; below are the ones our MRI recipes actually use. The rest (Design-Studio circuit builders, parameter sweep, vendored runtime wrappers) exist but are used only when a recipe calls for them. Source of truth for all tool names/signatures: `external/CST-MCP/mcp_server.py`.

## Core tools

| Workflow need | Tool | Notes |
| --- | --- | --- |
| detect CST install, python, running instances | `cst_detect_tool` | no args |
| list running CST Design Environment PIDs | `cst_list_design_environments_tool` | no args; use before `cst_connect_tool` when multiple DEs may be running |
| connect (or launch) CST | `cst_connect_tool` | `launch_if_needed=false` by default; set true only to start a new CST |
| inspect active/open project + messages | `cst_project_info_tool` | returns JSON string |
| (re)bind this MCP session to the active project | `cst_active_project_tool` | no args; call again after switching schematic/3D views if a tool reports a stale binding |
| open a project | `cst_open_project_tool` | arg: `path` |
| create a project | `cst_new_project_tool` | arg: `project_type` (mws/ems/ds/…) |
| save project | `cst_save_project_tool` | optional `path` |
| add VBA/history block | `cst_add_to_history_tool` | args: `title`, `vba_code` — use small named blocks |
| run VBA immediately (no history) | `cst_execute_vba_tool` | arg: `vba_code`; wraps in `Sub Main` if absent |
| run the configured solver (blocking) | `cst_run_solver_tool` | Warning: blocks; risks timeout on long 3D solves — prefer async pattern below |
| run circuit co-simulation (AC task) | `cst_run_circuit_cosimulation_tool` | arg: `task_name` (e.g. `"AC1"`); back-substitutes tuned excitation into 3D |
| configure AC task + Combine Results (no popup) | `cst_configure_ac_combine_tool` | schematic tool; sets Signal excitation + `docombineresults`/`blocknameforcombineresults` + monitor filters + Update in one shot. Args: `task_name`(AC1), `fmin`/`fmax`/`unit`, `port_name`(1), `block_name`(MWSSCHEM1), `amplitude`(10), `monitor_filters`(**default `[":hfield:"]`**). Warning: NEVER pass `["*"]` — it hits non-combinable `surface-current` and triggers the Abort/Retry/Ignore popup even with combine enabled. B1+ → default; SAR → `["h-field (f=0.21)","loss (f=0.21)"]`. |
| compute B1+/B1- from AC H-field | `cst_calc_b1_field_tool` | 3D tool; runs CST's MRI-Toolbox "Calc B1+" math directly and registers `2D/3D Results\B1+ and B1-\B1+ …` — NO pre-installed template, NO dialog. Args: `h_monitor` (e.g. `"H-Field\h-field (f=0.21) [AC1]"`), `mu_r`(1.0→Tesla), `b0_plus_z`(true) |
| list result tree | `cst_list_results_tool` | optional `cst_file`, `module` (`3d`/`schematic`) |
| read a 1D result | `cst_read_1d_result_tool` | args: `tree_path`, optional `cst_file`, `module`, `max_points` |
| escape hatch: run python in MCP process | `cst_run_python_tool` | `de`/`project`/`model3d` in scope; assign `result` to return data |

## Schematic (Design Studio) COM binding — activate the view first (verified 2026-07-20)

The schematic MCP tools (`cst_add_inductor_tool`, `cst_add_external_port_tool`,
`cst_add_ground_tool`, `cst_configure_frequency_sweep_tool`,
`cst_configure_ac_combine_tool`, …) drive a **separate Design Studio COM
sub-instance**. If the schematic view has not been opened this session, they
fail with:

```
Could not determine destination address for message: execute_vba_code,
com.cst.DesignStudioInstance_0, /com/cst/DesignStudioInstance_0_public_api
```

**Fix (verified end-to-end):** open the DS view once, then do the schematic
work in the SAME `cst_run_python_tool` call so the binding holds:

```python
manager.active_project()                       # rebind manager.project to the active project
manager.project.schematic.ActivateSchematicView()
import sys; sys.path.insert(0, r"...\external\CST-MCP")
from cst_schematic import CSTSchematicVBA as C   # exact VBA the MCP tools emit
manager.schematic_execute_vba(C.inductor("Lt", 88, "nH", 49775, 50000))   # place
manager.schematic_execute_vba(C.frequency_sweep("SPara1", 0.15, 0.25, 101, "GHz"))  # task
manager.schematic_run_simulation("SPara1")       # run
```

- Element block **type** is the DS catalog path, e.g. `CircuitBasic\Inductor` —
  NOT the short word `"inductor"` (`.Type "inductor"` → "No block type is
  specified."). Use the `CSTSchematicVBA` generators so you never hand-type it.
- After activating the schematic view, the **3D modeler** tools
  (`cst_calc_b1_field_tool`, model3d VBA) may transiently fail with
  `ModelerInstance_0` "could not determine destination" — call
  `manager.active_project()` and retry; the binding recovers.
- Read schematic results with
  `cst.results.ProjectFile(path, allow_interactive=True).get_schematic()`.
- `.Position` origin is 50000 — pass `50000 + stored_coord` (see
  `../building-blocks/vba-blocks/dipole-schematic.md`).

## Async solver pattern (preferred for 3D)

`cst_run_solver_tool` blocks and can time out. Instead, via `cst_run_python_tool`:
- start: `model3d.start_solver()` (non-blocking)
- poll: `model3d.is_solver_running()` and `model3d.get_solver_run_info()` (state RUNNING/ERROR/…)

## Things only reachable via `cst_run_python_tool` (no native tool)

- Walking the 3D nav tree for field names: VBA `Resulttree.GetFirstChildName(node)` / `GetNextItemName(node)` (start from a concrete node, not `""`).
- Reading parameter expressions: `model3d.RestoreParameterExpression(name)`.
- Running post-processing templates: `model3d.EvaluateResultTemplates()`.
- ASCII-exporting a field: `SelectTreeItem(...)` + `ASCIIExport` VBA (see b1-field-pipeline recipe).
- **Reading 3D field data bypassing a stale/collapsed nav tree**: when `SelectTreeItem`/`cst_list_results_tool` can't see a node (e.g. after `SAR.Create` collapses the tree, `pitfalls/sar.md`), read the field directly instead of via the tree: `r = model3d.Result3D(""); r.Load(<result_id_or_path>); arr = r.GetArray(<component>)`. This avoids the tree entirely.
- The `scripts/probe_project.py` reconnaissance helper is exec'd here.

## History block naming

When modeling, use small named `cst_add_to_history_tool` calls so the CST history tree stays readable. Generic titles:

- `set units and background`
- `define materials`
- `create geometry`
- `define ports`
- `set boundaries`
- `set mesh`
- `set solver`
- `set monitors`

## Rules

- Prefer a native tool over `cst_run_python_tool`.
- When no native tool exists for a modeling op, send Macro-Recorder-style VBA through `cst_add_to_history_tool`.
- Do not invent tool names. If unsure what exists, the source of truth is `external/CST-MCP/mcp_server.py`.
- Result reading generally requires a saved `.cst`; the active project works if it has been saved.
