# Official Component Library Reproduction Learning

Use this recipe when replaying a CST official Component Library case as a
learning/reference case. The goal is not just to get a model to solve once; the
goal is to leave a replayable artifact set and a compact `notes/repro-*.md`
learning note that future Tier-B generation and repairs can consult.

## Scope

In scope:
- Read-only inspection of the official `.cst` source and companion folder.
- Extracting `Model/3D/ModelHistory.json`, `Model/Parameters.json`, and
  `Model/simulationproperties.json`.
- Producing raw `.bas` history artifacts under `results/<project_id>/artifacts/`.
- Replaying the case in a new writable project through the artifact-first
  pipeline.
- Running the configured solver when practical, then comparing result-tree
  evidence against the official source project.
- Writing a distilled note under `notes/repro-*.md`.

Out of scope unless explicitly requested:
- Optimizing the official design.
- Changing topology or retuning beyond the official parameter set.
- GUI click automation.

## Required References

Read before CST execution:
- `../../driving/artifact-pipeline.md`
- `../../driving/cst-operation-notes.md`
- `../../foundations/cst-simulation-sop.md`
- `../../building-blocks/vba-knowledge/geometry-primitives.md`
- `../../building-blocks/vba-knowledge/ports-monitors-mesh.md`
- `../../building-blocks/vba-knowledge/solvers.md`

For circular/planar cases, also consult:
- `../../notes/repro-04-patch-fd.md`
- `../../notes/repro-05-single-coil.md` if the case teaches loop-like feed/gap
  behavior.

## Output Layout

Use one stable project id per official case:

```text
results/<project_id>/
  artifacts/
    blocks.json
    blocks_safe.json
    <step>/*.bas
  log/
    source_inventory.md
    history_digest.md
    state.md
  output/
    REPORT.md
projects/<project_id>.cst
```

`blocks.json` is the raw official history manifest. `blocks_safe.json` is the
initial replay list: it excludes known high-risk full solver/mesh dump blocks
and includes a generated minimal solver block when one can be inferred.

## Workflow

### 1. Source inventory

Record:
- Official source path.
- CST version from `ModelHistory.json`.
- Unit/frequency range.
- Parameters from `Parameters.json`.
- Active solver from `simulationproperties.json`.
- History captions grouped by step.

Do this offline first; do not open CST until the source inventory exists.

### 2. Extract history artifacts

Run:

```powershell
python .agents\skills\mri-coil-design-workflow\scripts\extract_component_history.py `
  --source-dir references_cases\<case-folder> `
  --project-id <project_id>
```

This writes one `.bas` per official history item and emits both manifests.
If `Model/Parameters.json` contains parameters, the extractor also writes
`artifacts/parameters/000_define_parameters.bas`; replay it before any official
history block. This prevents CST modal "New Parameter" prompts when a later
recorded block references expressions such as `k*h`.
Run L0 lint immediately:

```powershell
python .agents\skills\mri-coil-design-workflow\scripts\lint_vba.py --fix results\<project_id>\artifacts
```

Any lint ERROR must be fixed before CST replay.

### 3. Replay in a writable project

Create a new MWS project and save it to `projects/<project_id>.cst`. Execute
`blocks_safe.json` first with `scripts/batch_execute.py` in `batch_quiet` mode.
If a block fails, follow the L0-L4 ladder in `artifact-pipeline.md`.

Never overwrite the official `.cst` source.

### 4. Solve and validate

Save before solving. Prefer async solve via `cst_run_python_tool`:

```python
project.save()
model3d.start_solver()
# poll model3d.is_solver_running()
```

After the solver stops, save, refresh, and compare:
- Result-tree items in the reproduced project.
- S-parameter minima or key curve samples, when both projects have readable
  1D results.
- Monitor presence for field/farfield cases.

If a full solve is not practical, mark the note `partial` and state the exact
validated boundary: for example "source extracted + geometry/ports replayed,
solver pending".

### 5. Distill the learning note

Write `notes/repro-XX-<case>.md` with:

```text
# Repro XX: <official case>

## Status
## Source
## What this case teaches
## Official answer
## Reproduction pipeline
## Results and comparison
## Traps found
## Promote to shared references
## Links
```

Promotion rule:
- Narrative/context stays in the repro note.
- Canonical reusable VBA snippets go to `building-blocks/vba-knowledge/`.
- Machine-actionable traps go to `pitfalls/mcp-pitfalls.md` or `pitfalls/error-fixes.md`.
- Update `notes/README.md` so future tasks can find the new note.

## Current Circular Batch

Use this order:

| Order | Source | Project id | Note |
|---|---|---|---|
| 1 | `references_cases/Circular Patch Antenna_2.cst` | `circular_patch_td_repro` | `notes/repro-07-circular-patch-td.md` |
| 2 | `references_cases/Circular Resonator.cst` | `circular_resonator_repro` | `notes/repro-08-circular-resonator.md` |
| 3 | `references_cases/Circular Patch Antenna.cst` | `circular_patch_multilayer_repro` | `notes/repro-09-circular-patch-multilayer.md` |

Reason: start with the TD circular patch, then the two-port resonator, then the
HF Multilayer patch variant whose solver setup is more version-sensitive.
