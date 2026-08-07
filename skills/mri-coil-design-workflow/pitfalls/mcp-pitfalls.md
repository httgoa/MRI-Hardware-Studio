# MCP Pitfalls — Verified traps when driving CST via the MCP

Read this file BEFORE reaching for a new VBA/Python object.method or a new MCP tool. Every entry below cost 5–60 min of dead-end debugging when first encountered; each has a documented workaround.

This is the skill-local mirror of the same content in the private auto-memory. Kept here so the skill is self-contained when distributed (memory is per-user, this file ships with the skill).

**Companion**: `SKILL.md` §"Iron rule: on ANY error or unknown API" — the iron rule that these traps enforce: **on any error or unknown API, consult docs FIRST, do not guess**.

## When to look here

| Symptom | Look at |
|---|---|
| MCP tool call fails with `InputValidationError` / unknown kwarg | #10 (save_project `path`), #13 (`cst_run_python_tool` `code`), or grep `external/CST-MCP/mcp_server.py` |
| VBA "Method or property not found" | #3 (FarfieldPlot), #11 (new-version solver setters), any "fabricated API" case — grep the official VBA reference |
| VBA "&H8000ffff Unable to create electrical net" | #16 (5+ pins per net), #17 (zombie nets) |
| VBA "&H8000ffff No ComponentPorts / Component port array" | #16 (differential MWSSCHEM connection failure), #15 (wrong 3D port type) |
| VBA popup "No such property or method / newer version" — non-modal, blocks history | #11 (official .mod solver blocks bring new-version APIs) |
| GUI dialog blocks all MCP calls | #10 (save-as popup from wrong kwarg), #11 (version-mismatch popup), #27 (`New Parameter` modal from missing `Parameters.json`) |
| Results "empty" right after solve | `cst-operation-notes.md` §"read-after-write" (save+refresh); also #2 (StoreDoubleParameter wiping run_id=0) |
| Bash command random denial | #12 (`python -c` sandbox, `cd` prefix) |
| Same-named example gave "wrong" number | #5 (example variant identification) |
| Need 10g SAR but on FD/tet mesh | #18 (native 10g SAR needs TD hexahedral) |
| SAR node not selectable / tree collapsed after `SAR.Create` | #19 (headless-invisible node → Result3D two-hop) |
| SAR value looks like it ignored matching | #20 (`scale accepted` silent fail → divide by P_acc) |
| SAR spatial map peaks at conductor ends (wrong) | #21 (E-proxy falsified) / #22 (use native SAR field) |
| `ASCIIExport` "not available for current view" | #24 (export H BEFORE SAR.Create) / #19 |
| 3D volume monitor missing after TD solve | #23 (TD first-solve drops volume fields → re-solve) |
| ASCIIExport all-zero / silent empty reads | #26 (zombie process COM saturation) |
| First demo history block fails with `Expecting 'All | Sub'` | #28 (terminal status header was sent as VBA) |

## The traps (1–17 = MCP/VBA & schematic; 18–26 = SAR / field-export / session, distilled from the FD reproduction)

### Modeling / VBA API

1. **Parameter names must not be Python/VBA reserved words**: `MakeSureParameterExists "lambda", ...` reports via MCP "must not be a VBA or Python keyword". Official history runs fine with `lambda`, but bridged through MCP it must be renamed (use `lambda0`), along with any expression depending on it.

2. **Warning: `StoreDoubleParameter` triggers a parameter-change event → deletes the run_id=0 solve results**. Using it to store an "analysis output value" causes subsequent result reads to report "ResultItem does not exist for run id=0".
   - Correctly report a VBA-computed value: `ReportInformationToWindow("KEY=" & CStr(val))` writes a message → read it back from `cst_project_info_tool`'s `messages_tail`. This read path doesn't contaminate the project.
   - If mistakenly stored, `DeleteParameter` + re-store, but the lost results need to be re-run.

3. **Farfield list API** (don't fabricate it): there is no `GetListLength`/`GetListAngle`/`SetArrayScaling`/`GetValue`. Correct: `AddListEvaluationPoint theta,phi,r,"spherical","frequency",freq` → `CalculateList("")` → `GetList("Spherical linear theta abs")` (the component must include theta/phi, no generic "abs") / `GetMax`. Simplest way to get peak directivity: `FarfieldPlot.Reset:.SetPlotMode "Directivity":.Plottype "polar":.Vary "angle2":.Theta "90":.SetFrequency f:.Plot` then `.GetMax`.

4. **Discrete ports are more reliable with coordinates**: since the MCP has no interactivity, `.SetP1 "False"` + raw coordinates is more reliable than the official `Pick.PickCenterpointFromId`+`SetP1 "True"`, and gives the same result.

5. **The same-named example can have multiple variants**: e.g. "Dipole Antenna Array" is actually one of 4 variants (we downloaded variant 3, the Farfield Array Feature, which ignores mutual coupling); "Patch Antenna" has 5 variants (TD)/(FD)/Array/Array Combine/Array Simultan; the official (FD) case even keeps the TD pass curve for teaching comparison. Before reproducing, read the tutorial .htm first to confirm which variant you downloaded, or results won't match (variant 3's directivity of 7.5dBi vs the coupled variant's 8.6dBi is an expected difference).

6. **Cases whose geometry comes from external CAD** (e.g. MRI Coil's bodycoil.sat): the case folder ships a `Model/3D/<name>_1.sat` (the history may reference a different drive letter like `H:\` — use the shipped one instead). Parametric rebuilding is impractical; import directly with `SAT.FileName ... .Read`.

7. **`LumpedFaceElement.Create` must pick edges first**: even when given absolute coordinates via `SetP1/SetP2 "True",x,y,z`, you still need `Pick.PickEdgeFromId` to select 2 edges first, otherwise it reports "No edge picked for discrete face port creation". **Good news**: the official history's pick edge IDs remain valid on the same re-imported SAT → the official pick+lumped block can be replayed directly. Make each lumped element its own `add_to_history` block (with its own picks inside), don't cram multiple into one block.

8. **Copy lumped elements/shapes via transform using a fixed Vector + `UsePickedPoints "False"`**: the displacement is fixed by the vector and doesn't truly depend on picks, letting you bypass pick dependency for bulk copies (MRI Coil used this to translate 16 capacitors to the other end).

9. **Electrical-fidelity reproduction traps**: matching structure/S-parameter magnitude does not mean electrical detail matches. MRI Coil reproduction matched the official S11 magnitude (both ≈0 dB) but had a different phase — the official design has a port-matching network (M1/M2/MT1/MT2 parameters) that wasn't reproduced. For a body coil, S-parameters aren't the primary metric — **the rotating B1 field / B1+ is**.

### MCP tool signatures & CST GUI dialogs

10. **`cst_save_project_tool`'s parameter is named `path`, not `save_as_path`** (hit at the start of reproducing 04 Patch FD): correct call is `cst_save_project_tool(path="...\\project.cst")`. Passing the wrong name silently degrades to a no-arg save → the active_project just gets saved to a temporary `Untitled_N.cst`, and may also pop a GUI "Save As" dialog that blocks subsequent MCP calls. **When save hangs / a CST dialog pops up, the first reaction should be to check the parameter name, not wait for the user**. Source is in `external/CST-MCP/mcp_server.py`: `def cst_save_project_tool(path: str | None = None)`. Likewise, before any MCP tool call, if you're not 100% sure of the parameter name, grep `mcp_server.py` first.

11. **Warning: Solver parameter blocks in official .mod history can bring in newer-version APIs → pops "No such property or method" and blocks execution** (hit reproducing 04 Patch FD): the official Patch FD `.mod` was saved by CST 2024.0, and `IESolver.CalculateModalWeightingCMA` doesn't exist in older CST versions — replaying the whole `With IESolver` block pops "The file may be saved by a later version of CST MICROWAVE STUDIO", which is non-modal but **blocks subsequent `add_to_history` calls**.
   - **Rule**: **don't replay the entire parameter block of `With FDSolver/IESolver/MeshAdaption3D/Solver` from history verbatim**. These blocks have dozens to a hundred-plus setters, most of which are template defaults — only 5-10 are actually needed for this case (solver method / order / stimulation / accuracy / adaptation on/off / add sample interval).
   - **Approach**: only issue the **necessary** setters. CST leaves unset fields at the software default (safe), which is far better than "setting a field that doesn't exist" (popup). See `../building-blocks/vba-blocks/dipole-build.md`'s `With Solver` block, which is only ~10 lines.
   - Likewise, the official `.mod`'s `With Solver ... TD parameters` section (TD-S / SteadyStateLimit / MeshAdaption) is entirely unneeded in an FD reproduction — don't copy it.
   - If a popup is triggered: have the user close it manually; next time, trim the setter set for the same case.

12. **Bash sandbox: `python -c "long string"` gets randomly blocked — use a short script file instead**: write plotting/computation code into `results/<project>/log/foo.py` (via the Write tool), then run `python "<absolute path>.py"`, which passes reliably — this also matches the skill's official approach used by `plot_field.py` / `compute_b1plus.py`. Also **avoid any `cd` prefix** — always use absolute paths. For paths outside the project (e.g. `D:/ght/softwares/...` Online Help), use Read / Glob / Grep instead of Bash.

13. **`cst_run_python_tool`'s parameter is named `code`, not `python_code`** (hit on Patch FD): `def cst_run_python_tool(code: str)`, same source as mcp_server.py. Scope has `de` / `project` / `model3d`; assigning `result = ...` returns it. To read the result tree of a non-active .cst, use `cst.results.ProjectFile(path, allow_interactive=True)` (if that .cst is also open in the CST frontend, `allow_interactive=True` is required; use `False` only when it's purely on disk and CST isn't holding it open).

### Result reading & reference-case handling

14. **Note: the official FD case is a teaching variant of "run TD → copy results → convert to FD"** (hit on Patch FD): the official `Patch Antenna (FD).cst` keeps both `S1,1` (FD Tet) and `S1,1_(Mesh Pass=1)_TD` / `_(Mesh Pass=2)_TD` (retained TD Hex curves, from the tutorial section "Making a Copy of Transient Solver Results") under `1D Results\S-Parameters\`. Reproduction should only align to **`S1,1`** (the FD result), not the TD pass curves. For numerical alignment, **read the reference .cst directly with `cst.results.ProjectFile`** (`allow_interactive=True` if it's open in the GUI), get the f/S arrays, and do a point-by-point diff — far more precise than "comparing curve shapes by screenshot". The Patch FD reproduction achieved a min S11 diff < 1e-9 dB → step-by-step history replay can reach official-grade numerical agreement.

### Differential schematic (MRI coils)

15. **Important: The 3D port type automatically determines the schematic MWSSCHEM pin count** (discovered reproducing 05 Single Coil, important):
   - `DiscreteFacePort` (face-to-face differential pair) → **8-pin differential MWSSCHEM** (each 3D port expands into a signal pin + a reference pin)
   - `DiscretePort` (2-point port, fixed endpoints) → **4-pin single-ended MWSSCHEM** (each 3D port only exposes a signal pin; the reference implicitly connects to internal ground)
   - Detection method: `Block.Reset : Block.Name "MWSSCHEM1" : Block.GetNumberOfPins()` / `Block.GetDifferentialPorts()`
   - No need to explicitly call `Block.SetDifferentialPorts True`; even calling `Block.UpdateModel` reports "Unable to update model of block". CST automatically populates the MWSSCHEM based on the 3D port type.
   - **Rule**: to reproduce the official differential topology (each 3D port bridged by a lumped element), the 3D side must use `DiscreteFacePort`; for a simplified single-ended shunt topology use `DiscretePort`. **Once chosen, don't switch it** from start to finish — mixing them breaks the differential expansion path.

16. **Warning: `Net.AddComponentPorts` supports at most 4 pins per call** (hit reproducing 05 Single Coil, verified in a single-ended environment): 5+ pins in one call → "Unable to create electrical net". **A failed `.Apply` leaves behind a zombie net** (NNETS+1 after every failure), which must be cleaned up with `Net.Delete` before continuing — otherwise the zombie occupies pins and causes subsequent legitimate calls to fail too. **Rule**: when a logical net needs 5+ pins, split it into smaller subnets or merge with `Net.MergeSubNets`.
   - **Warning — unresolved**: `Net.AddComponentPorts + Apply` on an 8-pin differential MWSSCHEM fails regardless of pin count (even with just 2 pins); this may need a different API (`Block.SetReferenceBlock` / `Net.MergeSubNets` / manually extracted wiring VBA) — see `notes/repro-05-single-coil.md` for detail.

17. **Correct net-cleanup procedure**: `n = Net.GetNumberOfNets()` → collect `Net.GetNetNameByIndex(i)` into a list → loop `Net.Delete name`. **Note**: the initial NNETS with no networks defined is not 0 (CST auto-creates a default net for every isolated pin); after cleaning it becomes NNETS=0, and each subsequent `AddComponentPorts` call increments NNETS by 1 (even on failure).

### SAR & field export (distilled from reproducing the FD segmented dipole M2/M3, 2026-07-16)

> Source: the FD_Optimize M2/M3 reproduction from `mri-coil-agent-pack-716-psh`. All of the below are **CST-platform facts**, device-agnostic and independent of coil type, and hold for any MRI reproduction that needs 10g SAR / 3D field export.

18. **Warning: Native 10g SAR only supports hexahedral meshes → HF Time Domain is required when SAR is needed** (not an unconditional rule): CST's native IEEE 10g mass-averaged SAR post-processing is only available on **hexahedral** meshes; HF Frequency Domain's tetrahedral mesh **cannot produce** native 10g SAR.
   - **Rule**: **IF the paper/task requires native 10g SAR → HF Time Domain hexahedral**; **ELSE (only B1+ / S-parameters / narrowband fields needed) → choose the solver based on physics** (narrowband lossy loads can still use FD Tet — see the dipole/patch reproductions). Low-Q lossy loads are also better suited to TD, and it matches most papers' FDTD.
   - Don't hardcode "always TD-hex" into the general workflow — that's overfitting. TD-hex is a **conditional** requirement, only for SAR.

19. **Warning: The `SAR.Create` node is invisible headless + collapses the result tree**: `SAR.Create` succeeds and its `GetValue("max sar")` scalar **is reliable**, but its own tree node is **invisible** to the headless `SelectTreeItem`/`ASCIIExport` channel, and calling it **collapses the 2D/3D tree enumeration** (185→99 items, even H/E fields become unselectable).
   - **Rule**: **do not SelectTreeItem that `SAR.Create` node**. Use the two-hop method instead (see `scripts/export_native_sar.py`): ① the native SAR `.m3d` is already on disk in the same post-solve session → load it with `Result3D("SAR (f=freq) [1] (10g)")` (pure data read, bypasses the tree) → ② re-insert it into the tree with `res.AddToTree "2D/3D Results\SAR", "<label>"` → the re-inserted node **can be selected by `SelectTreeItem`** → normal ASCIIExport with coordinates.

20. **Warning: `SetOption "scale accepted"` silently fails on severely mismatched ports**: when a bare port is severely mismatched, SAR post-processing's `SetOption "scale accepted"` **silently returns a value exactly equal to `no rescale`** (it should differ by 1/P_acc). **This once produced a paper-contradicting result** (FoM optimum landed on the shortest antenna).
   - **Self-check**: on the same project, the ratio of `GetValue("max sar")` between no-rescale vs scale-accepted should be ≈ 1/P_acc; if it equals 1, the rescale has failed.
   - **Fix**: use `no rescale` (per-stimulation) + **manually divide by the measured P_acc** (B1+∝1/√P_acc, SAR∝1/P_acc).

21. **Wrong: Using the E-field point proxy `0.5·σ|E|²/ρ` to compute SAR has been falsified**: its |E|² peaks at the dipole's **conductor ends**, giving a spatial distribution **opposite** to the true 10g SAR (end peaks vs center/double peak); no amount of smoothing fixes this. It's only **coincidentally** usable when the antenna is unsegmented and SAR is naturally single-peaked at center.
   - **Rule**: **never** use the E-proxy for SAR **spatial distribution/profiles**; must use the native 10g SAR field (#19's two-hop method) or a GUI export (#22). The scalar max-SAR/FoM is reliable via `GetValue` (independent of field shape).

22. **SAR 3D field headless export is fragile → fall back to GUI for complex pipelines**: #19's two-hop method succeeds inside the window of "fresh post-solve session, export H-field first, then SAR immediately after, don't disturb the view, don't reopen" (M2's unsegmented sweep auto-exported all profiles this way). But when the pipeline gets complex (M3's segmented sweep: reading P_acc mid-case, lots of abort/reopen/multiple projects), session state degrades — `SelectTreeItem` becomes unreliable and `ASCIIExport` reports "not available for current view".
   - **Rule**: **scalars (FoM/SAR_max/B1+/P_acc) are reliably programmable throughout**; if the **SAR 3D field map** hits instability headless, fall back to **GUI MRI Toolbox → General SAR Result (no rescale, 10g, IEEE C95.3) → Export 3D Field Result (HDF5)**, then have the script read the file from disk. This isn't "impossible to export" — it's timing-fragile: simple pipelines can be automated, complex ones need the GUI as a fallback.

23. **Warning: TD's first solve often doesn't produce the 3D volume-field monitor → needs a re-solve guard**: in a `cst.interface` session (including MCP sessions), the first TD solve often produces **only S-parameters + 1D power, no 3D volume-field monitor**; **the second `start_solver` produces it** (deterministically).
   - **Rule**: after solving, check for the field node; if missing, call `start_solver` again (a guard, up to 3× max).

24. **Field export must happen before `SAR.Create`**: `SAR.Create` changes the active view, after which `ASCIIExport.Execute` reports "not available for current view".
   - **Fixed order**: solve → (re-solve guard) → **export H-field** → then compute SAR → read P_acc (use `run_ids[-1]`, since id=0 may have been deleted by a parameter change). Exporting via `project.model3d._execute_vba_code` (acting on the correct project object) is more stable than the MCP's `cst_execute_vba_tool`.

25. **SteadyStateLimit −30dB speed-up (key for high-Q mismatched points)**: large inductance + severe mismatch (P_acc as low as 0.002W) → long high-Q resonant ringing → TD steady-state time explodes (up to 450s at −40dB for one case). Changing `SteadyStateLimit "-40"`→`"-30"`: sufficient accuracy for frequency-domain field monitors (DFT-integrated B1+/SAR) (residual 0.1%, FoM difference <1.5%), time drops 450s→228s.
   - **Rule**: **all cases in a sweep must use the same steady-state limit** (re-run any cases done under a different limit for consistency).

### Session stability (distilled from reproducing dipole_scratch BUILD_NOTES, 2026-07-16)

26. **Warning: Zombie mcp_server / python processes saturate the COM channel → ASCIIExport all-zero / silent empty reads**: confirmed empirically reproducing dipole_scratch: ASCIIExport exported all-zero data (coordinates correct, field all 0, no error), root cause was **14 zombie python/mcp_server processes (12 from another workspace) saturating CST's COM channel**, especially zombies from different python envs. In severe cases the foreground DESIGN ENVIRONMENT crashes.
   - **Rule**: keep only the latest pair of MCP servers; `taskkill` the zombies. **But be precise when cleaning up** — this session's own MCP server was once accidentally killed (causing a disconnect requiring `/mcp` reconnect, which the agent cannot self-heal). After a CST crash, the MCP stdio pipe also breaks and needs reconnecting.
   - When checking for empty data, prefer reading `Result3D.Load(...).GetArray(...)` from disk rather than trusting the ASCIIExport file (the all-zero trap).

27. **Warning: Not replaying the official Component Library `Parameters.json` first → the `New Parameter` modal dialog blocks execution**: confirmed empirically reproducing `Circular Resonator` — the official history's port block uses `k*h` / `h`, but replaying step-by-step from an empty project without first `StoreParameter "k", "5.76"` and `StoreParameter "h", "0.635"` makes CST pop a `New Parameter` dialog (the UI may show it capitalized as `K`), asking for a manually-filled value/description; while the popup is unhandled, all MCP/COM calls appear to hang.
   - **Rule**: when reproducing an official Component Library case, first read `Model/Parameters.json` and generate/execute `000_define_parameters.bas`, then replay `ModelHistory.json`.
   - **Implementation**: `scripts/extract_component_history.py` already auto-converts `Parameters.json` into `artifacts/parameters/000_define_parameters.bas`.
   - **Recovery**: if the popup already appeared, fill in the values per `Parameters.json` (in this case `k=5.76`, `h=0.635`), close the popup, then replay from a clean project; don't keep stacking MCP calls while the modal is still open.

28. **Demo artifact transport: never pass terminal-rendered output as VBA**: a shell read can
   return a textual envelope beginning with `Exit code:`, `Wall time:`, and `Output:` before
   the actual `.bas` content. Passing that entire string to `cst_add_to_history_tool` makes
   CST reject the first token with `Expecting 'All | Sub'`, even though `lint_vba.py` reports
   zero errors for the file on disk.
   - **Rule**: in recording mode, read the `.bas` inside `cst_run_python_tool` with explicit
     UTF-8 and retrieve only `structuredContent.result.vba_code`.
   - **Gate**: before the visible history call, require non-empty content, reject the three
     transport prefixes, and verify/log the first line plus SHA-256 digest.
   - **Recovery**: the failed parse does not add a history node. Reload through the structured
     path and retry only that block; for a clean recording, discard the interrupted project
     and start again from a fresh empty MWS project.

## Related resources

- `notes/repro-01-dipole-antenna.md` through `repro-09-circular-patch-multilayer.md` — per-case detailed traps
- `cst-operation-notes.md` — GUI live-repaint, read-after-write, AC combine as pure API, B1+ as pure API
- `cst-red-lines.md` — the higher-level rules these traps enforce (safety, correctness, docs-first)
- `mcp-tool-map.md` — MCP tool names and signatures (source of truth for kwarg names)
- `mcp-setup.md` — prerequisites, environment vars, packages

Origin (private auto-memory): `mcp-repro-pitfalls.md` — this file is a distributable mirror kept in sync with the memory.
