# Recipe: Reverse-Engineering an Unknown CST Project

**When to use**: the user points you at a `.cst` you didn't build (someone else's, or built long ago), and you need to figure out what it is and what can be run before deciding on next steps.

**Core principle**: don't improvise a dozen ad-hoc probe snippets. Get the full picture with one standard probe, then decide.

## Steps

### 1. Connect and locate the project
- `cst_connect_tool` (if no running instance and the user wants to execute, `launch_if_needed=true`)
- `cst_project_info_tool` — confirm the active/open project, type, message log (watch for "not writable" warnings)

### 2. If you need to modify/solve → copy to a writable copy first
Red line: never overwrite the user's source file. Copy the `.cst` **and its same-named companion folder** to `projects/<name>_run/`, and open the copy with `cst_open_project_tool`. A read-only inspection can skip this.

### 3. One-shot probe (key step)
Run the probe script with `cst_run_python_tool`:
```python
exec(open(r"D:\ght\SAIS\MRI_agent\.claude\skills\mri-coil-design-workflow\scripts\probe_project.py", encoding="utf-8").read())
```
The returned `result` is a structured summary containing:
- `identity` — file/folder
- `solver_type` — the 3D solver (e.g. HF Frequency Domain)
- `parameters` — parameter names + expressions
- `nav_tree` — the results navigation tree (3D fields, monitors, S-parameters, etc.)
- `sparameter_items` / `b1_table_items` / `sar_table_items` — readable 1D/0D results
- `interpretation` — **automatic interpretation hints** (whether circuit co-sim is needed, whether there's a phantom, whether the circuit has already been run)

### 4. Interpret and decide
Use `interpretation` and the tree contents to determine what kind of simulation this is:
- Lumped parameters like `Cp/Ct/Lp/Lt` present → the workflow involves **circuit co-simulation (AC task)**
- `x/y/z_plantom` present → a phantom load exists → B1+/SAR analysis is meaningful
- H-field only has `[1]`, no `[AC*]` → the 3D solve is done but circuit co-sim **hasn't run yet**
- A `B1+ and B1-` node exists → the B1+ post-processing template is installed

### 5. Hand off to the matching task recipe
Once the project's capabilities are clear, route to the specific task, e.g. → `../b1-sar/b1-field-pipeline.md`.

## Known API traps (already handled inside the probe script, don't repeat them)
- `Resulttree.GetFirstChildName("")` returns empty — you must start from a concrete node name; `GetNextItemName` does a DFS within that node's subtree.
- Read parameter values with `RestoreParameterExpression(name)` (`GetParameterSValue`/`NValue` throw for expression-valued parameters).
- `Mesh.GetNP` throws "hexahedral mesh invalid" on a tetrahedral (frequency-domain) solver — don't probe the hexahedral mesh.
- `cst.results`'s `get_tree_items()` only lists 0D/1D results, **not 3D fields**; 3D fields must be walked via VBA over the navigation tree.

## When you need to ask the user
- Multiple projects open at once, unclear target → stop and ask which one.
- Even after probing, the primary goal is still unclear (S11? B1+? Gain?) → ask once.
