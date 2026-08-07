# L2 Error-Fixes — known CST execution errors → deterministic patch

This is the **L2 lookup table** in the artifact-first error ladder (L0 lint →
L1 batch capture → **L2 known-fix** → L3 bounded agent repair → L4 human). The
consumer of this table is `scripts/apply_error_fix.py` (`try_l2_fix`): when L1
captures a block failure it matches the exact CST error text (and/or the
offending `.bas` content) against the `match`/`content_match` patterns below,
then:
- **`.bas`-text-patchable kinds** (F1 rename_param, F2 replace_store_param,
  F4 trim_solver_setters, F10 offset_schematic_coord): rewrites the failing
  `.bas` **deterministically (zero LLM)** and returns `resume_index` so the
  caller re-runs `run_blocks(start_index=...)`.
- **match-only kinds** (F3, F5–F9, F11): the fix is a tool-arg / live-schematic
  / block-ordering change, NOT a file edit — the executor returns
  `patchable:false` + the `action` string for the caller (or L3 agent) to apply.
- **no match** → escalate to L3 (`scripts/prepare_l3_repair.py`: deterministic
  vba-knowledge selection + ≤2 retry budget; the main agent rewrites the block).

Distilled from the verified traps in `mcp-pitfalls.md`. Keep this file and
`mcp-pitfalls.md` in sync: pitfalls = human narrative, this = machine-consumable
signatures. Add a new row here every time a pitfall yields a mechanical fix.

## Human-readable table

| # | Error signature (substring / regex, case-insensitive) | Root cause | Deterministic patch |
|---|---|---|---|
| F1 | `must not be a VBA or Python keyword` | param name collides with a reserved word (pitfall #1) | rename the offending param to `<name>0`; rewrite every expression that references it |
| F2 | `ResultItem does not exist for run id=0` after a `StoreDoubleParameter` block | `StoreDoubleParameter` wiped run_id=0 results (pitfall #2) | replace `StoreDoubleParameter "K",v` with `ReportInformationToWindow("K=" & CStr(v))`; read value from `messages_tail` |
| F3 | `Abort` / `Retry` / `Ignore` popup during AC combine, or `surface-current` in combine filter | combine filter hit a non-combinable field (pitfall, cst-operation-notes) | set `monitor_filters=[":hfield:"]` (B1+) or `["h-field (f=...)","loss (f=...)"]` (SAR); never `["*"]` |
| F4 | `No such property or method` / `saved by a later version of CST` popup inside `With FDSolver`/`IESolver`/`Solver`/`MeshAdaption3D` | official `.mod` solver block carries newer-version setters (pitfall #11) | strip the block down to the ~5–10 required setters (method/order/stimulation/accuracy/adaptation/sample-interval); drop all others so CST keeps defaults |
| F5 | `Unable to create electrical net` with `Net.AddComponentPorts` and ≥5 pins | one net given 5+ pins (pitfall #16) | split into ≤4-pin subnets; then `Net.MergeSubNets`; also `Net.Delete` any zombie net left by the failed `.Apply` |
| F6 | `Unable to create electrical net` after a prior net failure | zombie net occupying pins (pitfall #17) | enumerate `Net.GetNumberOfNets()` → `Net.GetNetNameByIndex(i)` → `Net.Delete` each, then retry |
| F7 | `No edge picked for discrete face port creation` on `LumpedFaceElement.Create` | face port needs picked edges first (pitfall #7) | prepend `Pick.PickEdgeFromId` for the 2 edges inside the SAME history block before `.Create` |
| F8 | save/history stalls or a "Save As" GUI dialog appears after a save call | wrong save kwarg silently degraded (pitfall #10) | call `cst_save_project_tool(path="...cst")` with the correct `path` kwarg |
| F9 | `not available for current view` on `ASCIIExport.Execute` | export attempted after `SAR.Create` changed the active view (pitfall #24) | reorder: export H/E field BEFORE `SAR.Create`; never SelectTreeItem the SAR.Create node (pitfall #19 two-hop) |
| F10 | schematic block layout scattered ~50000 units from MWSSCHEM1 | `.Position` origin is 50000, raw target coord passed (pitfall, dipole-schematic) | pass `50000 + <stored coord>` to `.Position` (electrical connection unaffected, layout only) |
| F11 | `Invalid instruction` on `ZoomToFit` / `ActivateSchematicView` / `ActivateAssemblyView` in VBA | schematic view ops are Python object methods, not VBA (demo-recording) | call via `cst_run_python_tool`: `project.schematic.ZoomToFit()` etc., not through VBA |
| F12 | `Expecting 'All | Sub'` on a lint-clean first history block | shell/terminal transport status (`Exit code:`, `Wall time:`, `Output:`) was prepended to otherwise-valid `.bas` text | reload the file as UTF-8 through `cst_run_python_tool`; validate first line/digest; pass only `structuredContent.result.vba_code` to `cst_add_to_history_tool` |

## Machine-readable signatures

```json
[
  {"id": "F1", "match": "must not be a VBA or Python keyword", "fix_kind": "rename_param", "auto": true,
   "action": "suffix offending param with '0'; rewrite dependent expressions"},
  {"id": "F2", "match": "ResultItem does not exist for run id=0", "fix_kind": "replace_store_param", "auto": true,
   "action": "swap StoreDoubleParameter -> ReportInformationToWindow"},
  {"id": "F3", "match": "(abort.*retry.*ignore|surface-current)", "regex": true, "fix_kind": "combine_filter", "auto": true,
   "action": "set monitor_filters to [':hfield:'] or explicit h-field/loss list; never ['*']"},
  {"id": "F4", "match": "(no such property or method|saved by a later version)", "regex": true, "fix_kind": "trim_solver_setters", "auto": false,
   "action": "reduce With FDSolver/IESolver/Solver block to required setters only"},
  {"id": "F5", "match": "unable to create electrical net", "fix_kind": "split_net", "auto": false,
   "action": "split net into <=4-pin subnets + MergeSubNets; delete zombie net"},
  {"id": "F6", "match": "unable to create electrical net", "fix_kind": "purge_zombie_nets", "auto": true,
   "action": "enumerate and Net.Delete all nets, then retry the block"},
  {"id": "F7", "match": "no edge picked for discrete face port", "fix_kind": "prepend_pick_edges", "auto": false,
   "action": "add Pick.PickEdgeFromId for the 2 edges before LumpedFaceElement.Create"},
  {"id": "F8", "match": "(save as|another project is open|save.*dialog)", "regex": true, "fix_kind": "fix_save_kwarg", "auto": true,
   "action": "use cst_save_project_tool(path=...)"},
  {"id": "F9", "match": "not available for current view", "fix_kind": "reorder_export_before_sar", "auto": false,
   "action": "export field before SAR.Create; use Result3D two-hop, do not SelectTreeItem SAR.Create node"},
  {"id": "F10", "match": null, "content_match": "\\.Position", "fix_kind": "offset_schematic_coord", "auto": true,
   "action": "add 50000 to schematic .Position coordinates"},
  {"id": "F11", "match": "invalid instruction", "content_match": "(ZoomToFit|ActivateSchematicView|ActivateAssemblyView)", "fix_kind": "route_to_python", "auto": true,
   "action": "call the schematic view method via cst_run_python_tool, not VBA"},
  {"id": "F12", "match": "Expecting 'All | Sub'", "fix_kind": "reload_history_payload", "auto": true,
   "action": "reload the lint-clean .bas via cst_run_python_tool UTF-8 structured result; reject shell status prefixes; pass only structuredContent.result.vba_code"}
]
```

### Field meaning
- `match`: case-insensitive substring of the CST error text; `regex:true` → treat as regex.
- `content_match`: additionally require this pattern in the failing `.bas` content (disambiguates same-text errors like F5/F6).
- `fix_kind`: stable id the repair module dispatches on.
- `auto`: `true` = safe to patch + retry without review; `false` = patch is heuristic, surface a one-line confirmation before retry (still zero-LLM).
- `action`: the deterministic transformation to apply.

> When a new mechanical fix is verified, add it to BOTH the table and the JSON
> block, and cross-reference the originating `mcp-pitfalls.md` entry.
