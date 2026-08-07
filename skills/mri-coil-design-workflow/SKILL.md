---
name: mri-coil-design-workflow
description: "Use this skill when driving CST Studio Suite through the CST MCP for MRI RF coil workflows: designing or inspecting coils, opening or understanding an existing .cst project, setting up geometry, materials, ports, boundaries, mesh, solvers, and monitors, running EM plus circuit co-simulation and post-processing pipelines, extracting and validating MRI results including S-parameters, resonance, B1+ field, homogeneity, and SAR, generating data-prep records, and producing reports. Routes each request to a task recipe under recipes/."
---

# MRI Coil Design Workflow

Use this skill as the workflow and decision layer. Use the **CST MCP** (server `cst-studio-suite`, source `external/CST-MCP`) as the execution layer: every live CST action goes through MCP tools or scripts invoked through MCP.

This final version uses the `skills_psh` layered architecture and the `skills_ght` artifact-first execution core. All paths below are relative to this skill root.

## Layout

| Layer | Directory | Role |
| --- | --- | --- |
| Foundations | `foundations/` | MRI physics, correctness rules, simulation SOP, result validation |
| Driving | `driving/` | CST/MCP operation rules, tool map, parameter policy, artifact-first pipeline |
| Recipes | `recipes/` | Executable task workflows: inspect, build, B1/SAR, data-prep, reproduction, optimization |
| Building blocks | `building-blocks/` | Verified VBA blocks and Tier-B few-shot VBA knowledge |
| Scripts | `scripts/` | Artifact rendering, linting, batch execution, repair, field/SAR/B1+ post-processing |
| Templates | `templates/` | Tier-A deterministic Jinja2 VBA templates |
| Pitfalls | `pitfalls/` | Known traps and deterministic error-fix signatures |
| Notes | `notes/` | Manual digests and verified reproduction logs |
| Design notes | `design-notes/` | Roadmap research notes, not executable recipes |

## Operating Modes

Classify the user request first:

| Mode | Use when | Action |
| --- | --- | --- |
| Plan only | user wants a scheme/outline | Do not run CST; produce setup plan and assumptions |
| Inspect existing | user points at a `.cst` you did not build | Read `recipes/inspect/inspect-unknown-project.md`; inspect before modifying |
| Run known pipeline | project is understood and standard analysis is wanted | Follow the matching recipe, usually `recipes/b1-sar/b1-field-pipeline.md` |
| Design from scratch | user wants a new coil/project | Use artifact-first modeling; start from templates when possible |
| Modify + re-run | user asks to change a parameter/topology | Work on a copy, change only what is requested, solve, validate |
| Demo / recording | request contains "demo", "recording", "screen capture", or "I want to see it happen live in CST" | Follow `recipes/build/demo-recording-mode.md`; keep the CST front-end visually synchronized |
| Reproduce a paper | user wants paper reproduction end-to-end | Start at `recipes/paper-reproduction/orchestrator.md` |
| Data-prep complete case | user is producing case-matrix records | Follow `recipes/data-prep/data-prep-complete-case.md`; for dipole D1 read `recipes/data-prep/complete-case(D1)/data-prep-complete-case-dipole.md` |
| Official component learning | user wants to replay/distill CST library components | Follow `recipes/reference-repro/official-component-repro-learning.md` |

When unsure what a project can do, always inspect first.

Paper-specific implementations live under `recipes/paper-reproduction/cases/`. After reading
the general paper-reproduction orchestrator, use a matching case bundle when one exists.

## Modeling Pipeline: Artifact First

For any from-scratch build or known-design replay, **do not drive CST live block-by-block by default**. Use the artifact-first contract in `driving/artifact-pipeline.md`: generate offline, lint, review, then execute in as few live CST round-trips as possible.

1. Classify each modeling step:
   - **Tier A**: deterministic Jinja2 render via `scripts/render_templates.py` + `templates/*.vba.j2`. Use this for known designs and setup/materials/ports/monitors/solver/export blocks.
   - **Tier B**: one bounded few-shot generation scaffolded by `scripts/prepare_tierb_gen.py`, using `building-blocks/vba-knowledge/*.md`.
   - **Tier C**: agent reasoning for genuine design decisions only, such as choosing topology or tuning direction.
2. Generate `.bas` artifacts offline into `results/<project>/artifacts/<step>/*.bas`.
3. Run L0 lint before CST: `python scripts/lint_vba.py --fix results/<project>/artifacts`.
4. Present a review/defaults card before expensive solves unless the user explicitly says to run directly.
5. Execute via `scripts/batch_execute.py` through the CST MCP:
   - `batch_quiet` is the production default.
   - `demo_stepwise` is used for recording/demo requests.
6. On block failure, walk L0-L4:
   - L1: `batch_execute.py` reports failed index, error, and `.bas` path.
   - L2: `scripts/apply_error_fix.py` consumes `pitfalls/error-fixes.md` for deterministic fixes.
   - L3: `scripts/prepare_l3_repair.py` builds a bounded single-block repair context from `building-blocks/vba-knowledge/`.
   - L4: ask the user if the failure cannot be repaired safely.

Solving, circuit co-simulation, AC combine, B1+, SAR, exports, and result reading still go through the CST MCP and the relevant recipe.

## Before Driving CST

Read only what is needed for the current task, but always obey these gates:

- Before any live CST action, check `driving/cst-operation-notes.md`, `driving/mcp-tool-map.md`, and the relevant recipe.
- Before any from-scratch or replay build, read `driving/artifact-pipeline.md`.
- Before any unfamiliar API, exact VBA method, solver choice, or GUI setting, consult official docs through `driving/cst-official-docs-map.md` and the paths listed in `driving/cst-operation-notes.md`.
- If an API/tool name is not verified in `driving/mcp-tool-map.md`, the MCP server source, official docs, or runtime introspection, do not fabricate it.
- If B1+/AC-combine helper tools exist in the current MCP build, use the route documented in `driving/mcp-tool-map.md`; if they do not, use the verified H-field export plus `scripts/compute_b1plus.py` route documented in `recipes/b1-sar/b1-field-pipeline.md`.

## Standard Workflow

1. Detect CST MCP and CST Design Environment status.
2. Choose the operating mode.
3. For existing projects, copy the `.cst` and companion folder before any write/solve.
4. Resolve missing inputs with `driving/parameter-policy.md`.
5. Build, modify, or inspect through the relevant recipe.
6. Save before solving; prefer async solver start + polling for 3D.
7. Run required stages in order: 3D solve, circuit co-sim/AC combine when needed, post-processing, field/SAR/B1+ export.
8. Validate using `foundations/result-validation.md` and `foundations/cst-red-lines.md`.
9. Write logs and outputs into the stable project folder under `results/<project_id>/`.

For **paper reproduction**, the visible and persisted lifecycle is mandatory:
`01 paper analysis/reproduction protocol → 02 baseline gate → 03 core evaluation →
04 post-processing → 99 validation and final scientific report`.
Do not open CST or start a sweep before showing the paper question, claim map, scope,
paper-to-CST translation, assumptions, case matrix, metrics/ROI/normalization, and acceptance
rules. Do not finish at figure generation; show the scorecard, discrepancies, limitations,
evidence inventory, and final verdict.

## Result And Data Rules

- Never overwrite the user's source `.cst`.
- Solver success is unverified until result-tree entries or exported data confirm it.
- Do not skip required pipeline stages: B1+ uses the circuit co-sim `[AC*]` field, not the raw `[1]` field, unless the recipe explicitly says otherwise.
- AC Combine filter: never use `"*"` blindly. Combine only needed monitors; see `driving/cst-operation-notes.md`.
- Export fields on a uniform physical mm grid with `.Mode "FixedWidth"` and `.Step 1` or `.Step 2`.
- S-parameters are dB via `20*log10(abs(S))`, never raw magnitude labeled as dB.
- B1+ is the CP transmit component `(Bx+i*By)/2`, not `|H|`; report units, plane, ROI, and normalization.
- SAR must state averaging mass and W/kg normalization.
- Include exact evidence paths and mark incomplete extraction as `needs_validation` or `partial`.

## Output Layout

Use one stable result folder per project:

- `results/<project_id>/log/`: intermediate artifacts, raw field exports, solver probes, repair attempts, scratch notes.
- `results/<project_id>/artifacts/`: offline generated `.bas` blocks and manifests.
- `results/<project_id>/output/`: final deliverables only: figures, CSVs, `stats.json`, records, and reports.

Scripts accept `--outroot <results-root> --project <project_id>` where applicable. Respect an
explicit user-selected results root and keep every stage, artifact, log, project, and output
path beneath it.

## Reference Routing

Read the smallest relevant set:

- `driving/artifact-pipeline.md`: canonical artifact-first modeling contract.
- `driving/workflow.md`: end-to-end mode routing.
- `driving/parameter-policy.md`: defaults and clarification policy.
- `driving/cst-operation-notes.md`: CST/MCP behavior, read-after-write, AC combine, B1+, field export caveats.
- `driving/mcp-tool-map.md`: available MCP tool names and safe invocation patterns.
- `foundations/cst-simulation-sop.md`: the global per-case hard-order solve and data processing checklist.
- `recipes/data-prep/complete-case(D1)/data-prep-complete-case-dipole.md`: canonical data-prep dipole module, with colocated case matrix and record template.
- `notes/data_prep/AGENT_BATCH_SIMULATION_PIPELINE.md`: authoritative upstream SOP for data-prep D1 regular-dipole batch execution and SAR 3D HDF5 export; when it conflicts with generic defaults, the D1 module wins for that module.
- `foundations/cst-red-lines.md`: correctness and safety rules.
- `foundations/mri-physics.md`: Larmor, B1+, SAR, matching, solver choice.
- `foundations/result-validation.md`: evidence requirements and status values.
- `pitfalls/mcp-pitfalls.md`: verified CST/MCP traps.
- `pitfalls/error-fixes.md`: machine-readable L2 error signatures.
- `building-blocks/vba-blocks/`: verified dipole ground-truth blocks.
- `building-blocks/vba-knowledge/`: Tier-B reusable CST VBA snippets for geometry, ports, solvers, schematic matching, MRI setup, field export.
- `templates/`: Tier-A deterministic CST VBA templates.
- `notes/README.md`: index for manual digests and reproduction logs.

## Main Recipes

- Inspect unknown project: `recipes/inspect/inspect-unknown-project.md`
- From-scratch dipole: `recipes/build/dipole-from-scratch.md`
- Demo/recording: `recipes/build/demo-recording-mode.md`
- Smith matching: `recipes/build/smith-matching.md`
- B1+ field pipeline: `recipes/b1-sar/b1-field-pipeline.md`
- SAR native export legacy/reference route: `recipes/b1-sar/sar-field-export.md`
- Parameter sweep FoM optimization: `recipes/optimize/parameter-sweep-fom-optimization.md`
- Data-prep complete case router: `recipes/data-prep/data-prep-complete-case.md`
- Data-prep dipole complete case module: `recipes/data-prep/complete-case(D1)/data-prep-complete-case-dipole.md`
- Paper reproduction: `recipes/paper-reproduction/orchestrator.md`
- Paper figure device geometry: `recipes/reference-repro/paper-figure-device-geometry.md`
- Official component replay/learning: `recipes/reference-repro/official-component-repro-learning.md`

## Scope

Current verified emphasis: from-scratch and existing MRI coil projects in CST, artifact-first modeling, circuit co-simulation, B1+ extraction, SAR workflows, data-prep complete cases, paper/device reproduction, and reusable CST component-learning loops. Roadmap material remains in `design-notes/` and placeholder recipe folders until promoted by verified runs.
