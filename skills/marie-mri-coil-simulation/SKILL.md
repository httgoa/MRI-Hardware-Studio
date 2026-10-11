---
name: marie-mri-coil-simulation
description: Create, modify, run, validate, troubleshoot, postprocess, onboard, and maintain architecture records for MARIE 3.0 MRI coil simulations. Use for MARIE MATLAB projects, new-session initialization, workspace handoff, architecture/interface updates, JSON and Gmsh inputs, runner and TMD scripts, S-parameter diagnostics, field/SNR/UISNR/Tx-Rx assessment, source-code questions, operational safety, result management, or bundled MARIE guidance when the original workspace path is unavailable.
---

# MARIE MRI Coil Simulation

Build each design as an isolated, reproducible case. Preserve the original input and result files; never mutate a validated reference design in place.

Shared and built-in assets may remain under `data/`. A self-contained project may own inputs, coils, basis supports, and BASIS files under `runs/<ProjectCaseTag>/assets/` with the same internal layout. Current `load_inputs` resolves absolute paths, input-directory-relative paths, explicit or controlled auto-discovered `AssetRoot`, then legacy `data/` fallbacks. Auto-discovery applies only to `.../assets/inputs/` with a sibling `coils/` directory. Shared bodies may remain in `data/bodies/`; record their paths and hashes. Never remove legacy copies as part of an architecture switch without separate cleanup authorization.

A research program may instead own immutable definitions under `projects/<ProjectID>/cases/<CaseTag>/` and evidence under `projects/<ProjectID>/runs/<CaseTag>/<RunTag>/`. Use input-directory-relative asset paths or an explicit supported `AssetRoot`, freeze input/MSH/JSON/runner snapshots per RunTag, and keep toolkit `data/` plus repository-root `runs/` free of project outputs. When invoking a case script with MATLAB `run(...)`, resolve the repository root from `mfilename('fullpath')` before `startup`; do not assume the caller's `pwd` survives `run`.

## Storage Governance

Use the system SSD as the control plane and `/mnt/data/<user>/marie/` as the large-data plane. Keep code, cases, runners, manifests, documentation, metrics, and lightweight figures in the workspace; place large MAT/BASIS files, checkpoints, simulation outputs, and stable large bodies on the data disk. Project `runs/` and `artifacts/bases/` may be symlinks so logical paths remain stable. Read [references/storage-layout.md](references/storage-layout.md) before planning storage, migration, cleanup, or a high-cost run.

Before a high-cost run, resolve and record every output `realpath`, verify that its mount is writable and not `ro`, record filesystem/inode headroom, and require destination free space at least 2.5 times estimated persistent output. Preserve after-run reserves of `max(15%, 200 GiB)` on the system disk and `max(10%, 500 GiB)` on the data disk. If size is unknown, run a bounded resource probe; never delete other cases automatically to satisfy a capacity gate.

Migrate by copy, checksum, symlink switch, and read-only regression. Never delete the source in the migration operation; source cleanup needs a separate exact manifest and authorization. Do not rely on hardlinks across filesystems. Record logical path, physical path, realpath, filesystem, storage tier, size, hash, and link type in formal manifests.

## Documentation Lookup

Use the bundled snapshot instead of depending on an absolute workspace path:

- Read [references/upstream-and-license.md](references/upstream-and-license.md) before redistributing the skill or bundled MARIE-derived material.
- Read [references/document-index.md](references/document-index.md) to select the relevant document.
- Search `references/workspace-docs/` for detailed guidance. These files are self-contained copies of the MARIE workspace root documentation.
- Run `python scripts/query_marie_docs.py "<query>"` for full-text search, or add `--headings`, `--files`, `--regex`, or `--json` as needed.
- Read `references/workspace-docs/AGENTS.md` and `references/workspace-docs/MARIE_Agent_Harness.md` before modifying or running a MARIE project.
- Consult `references/bundle-manifest.json` for snapshot hashes and provenance.

Treat the bundle as a fallback snapshot. If an active MARIE workspace is available, inspect its current `AGENTS.md`, source, inputs, scripts, and results before acting; current code and runtime evidence override the snapshot. Never copy a bundled file over a live workspace without comparing it and obtaining any approval required by the active project rules.

Use `assets/matlab-scripts/` as path-independent reference backups of the workspace-level MATLAB scripts. Copy a script to a new case/version before adapting it; do not edit the bundled backup in place during ordinary simulation work.

Use assets/marie-agent-phase1/ as the reference backup for preparation, preflight, runtime, and selftests. In an active workspace, prefer its current tools/marie-agent/ implementation. Legacy cases remain restricted to light, read-only geometry. The allowlisted training-closed-loop-v1 profile may expose geometry, Stage A, TMD, Stage C, and post for an isolated training CaseTag; high-cost or JSON-writing runs require an exact-run approval, TMD uses a canonical active-JSON lock and backup, requested process workers are enforced before the runner, total production workers are capped at 96, and GPU 0 is exclusive. Never broaden a production profile without a separate architecture update and authorization.

## Session Initialization

At the start of a new MARIE development session:

1. Read the active workspace `START_HERE.md`, `AGENTS.md`, and `MARIE_Agent_Harness.md` completely.
2. Run `bash tools/session_bootstrap.sh [CaseTag]` from the workspace root. If that interface is absent, run `bash scripts/session_init.sh [workspace] [CaseTag]` from this skill.
3. If the selected case contains a case-local `START_HERE.md`, read it before its status files; it is the case navigation/checklist layer, while live evidence remains authoritative.
3. Read the latest case `status.json`, `manifest.yaml`, `report.md`, and relevant logs selected by the bootstrap output.
4. Recheck live Git state, processes, hashes, resources, and task-specific assets. Do not treat a handoff summary as current proof.
5. Do not start MATLAB from the initialization interface. Record runtime `which -all` separately before a formal simulation.

Read [references/architecture-interfaces.md](references/architecture-interfaces.md) for callable interfaces, the current architecture handoff, and the mandatory update protocol.

## Architecture Maintenance

Treat architecture documentation and callable interfaces as part of every architecture-changing task. When changing directory ownership, case evidence layout, runner conventions, initialization, validation gates, deployment, or a public helper interface:

1. Update the active workspace documentation and interface.
2. Update `references/architecture-interfaces.md` with the effective date, change, affected paths, callable interface, compatibility impact, and evidence.
3. Refresh affected `references/workspace-docs/` snapshots, then run `python scripts/refresh_bundle_manifest.py`.
4. Update the repository skill source first, validate it, then deploy it to the installed skill directory and compare hashes.
5. Never claim the deployed skill is current without validation and source/deployment equality evidence.

Use `python scripts/record_architecture_update.py ...` for deterministic registry entries. This maintenance rule is prospective: apply it to each future architecture update rather than inventing undocumented behavior after the fact.

## Workflow

For the current WP7 receive-coil optimization architecture, candidate-specific TMD contract, Stage A cache invalidation rules, fixed-circuit Stage C, and evidence feedback loop, read `references/workspace-docs/MARIE_WP7优化框架架构与流程_v01.md`. Treat its case-local runners as demonstrated interfaces, not yet as a stable generic production API.

After TMD writes the active circuit, freeze a separate same-stem FixedCircuit MSH/JSON pair, set every `optim.boolean` to `0`, and point `TMD=0` Stage C at that frozen input. Do not run Stage C directly against a TMD-active JSON. Before formal MATLAB execution, remove archived handoff source snapshots from the active path or assert with `which ... -all` that the live repository implementation has precedence.


1. Inspect the existing project structure, MARIE version, body mesh resolution, and available coil templates.
2. Create versioned Gmsh wire geometry and a matching circuit JSON. Keep the element order identical: each physical Loop has one port followed by its tuning capacitors.
3. Use symmetry groups only when geometry, load, and desired circuit values are physically symmetric. Do not use a common symmetry group across geometrically different rows without first validating the array response.
4. Create a separate input JSON and runner. Set `TMD=1` for automatic tuning/matching. The output base name is derived from the input JSON, so use unique names.
5. Run geometry assembly before the full solve. Verify physical port count, coil-to-body clearance, overlap, row positions, and Larmor frequency.
6. Run the full MARIE runner. Treat a completed MAT file as a numerical result, not automatically a validated design.
7. Gate Rx designs using preamplifier-loaded `SP_p` and `figure_freq.SPm_plot_Rx`; use off-diagonal `SP_s` to assess coupling. Check field-map symmetry and SNR/UISNR separately.
   A project may define a documented two-grade policy: Grade A preserves the
   formal baseline gates, while Grade B permits only explicitly bounded adjacent-pair
   exceptions for an exploratory fixed-circuit Stage C. Record both verdicts;
   never label Grade B as a formal or research-validated baseline.
   A design failing both grades may enter a separately isolated
   `temporary_user_override` Stage C only after explicit user authorization for
   the exact case and source RunTag. Preserve the rejected Stage-B metrics and
   require both a structured override flag and an explicit runtime switch.
8. For Tx metrics, require a result that contains `h_field.Tx.b1p` and `e_field.Tx.e_b`; do not use Rx-only reciprocal fallback fields as formal SAR data.

## Design Rules

- A wire `.msh` and circuit `.json` must have the same channel count and the same lumped-element order.
- A project may generate fixed-channel Loop-to-dipole replacement geometries before the pure-Loop reference is accepted, but those assets are geometry-exploration candidates only. Preserve the physical channel count, document nested replacement sets, run independent static plus native geometry gates, prohibit performance ranking, and require a new Stage A YPn for every changed topology. Skipping further reference optimization changes execution order; it does not create an accepted baseline.
- Current `ProcessLoops` preserves one three-point WIE support per segment for a closed component and creates `N-2` supports for an `N`-segment open component. Mixed closed/open meshes are rebuilt component-by-component, and lumped port indices are remapped by their original spatial positions. Geometry gates must assert the resulting support count and port positions for both topologies.
- Preserve all previously validated files. Create new geometry, circuit, input, runner, and solution names for every topology or parameter sweep.
- With TMD enabled, MARIE may create temporary solve ports for all tunable elements. The final `SP_s` must return to the physical coil-port dimension.
- Use `SP_p` for a pure-Rx matching criterion. A poor diagonal `SP_s` does not by itself prove preamplifier-loaded matching failure.
- Validate resonance location, `SP_p`, worst off-diagonal `SP_s`, and rotational/row symmetry before investing in UISNR or high-resolution simulations.
- Double-row arrays add intra-row, inter-row aligned, and inter-row staggered coupling. Retune after any geometry change; do not reuse capacitor values from a single-row array as final values.

## Output and Postprocessing

Store postprocessing figures and numeric summaries next to the corresponding solution under a case-specific output folder. At minimum export S-parameter views, B1- per channel, SNR/UISNR maps and central profiles, and the Rx noise covariance matrix. Read [references/rx-array-validation.md](references/rx-array-validation.md) when writing or reviewing these checks.

When converting MARIE `solution.snr_field.SNR` to an acquisition-specific or
measured SNR, or when reporting absolute SNR error, read
[references/snr-measurement-normalization.md](references/snr-measurement-normalization.md).
Do not call the raw MARIE map a scanner-protocol SNR: first record the simulated
voxel volume, MARIE water-proton `M0` and temperature assumptions, acquisition
voxel volume, effective noise bandwidth, averages, sequence magnetization,
tissue proton density, receive-system efficiency, and reconstruction losses.
Use one independently defined global calibration factor when a residual system
scale must be estimated; never fit a separate factor per voxel or ROI.

For UISNR work, distinguish a `geo_flag=2` surface-support-constrained optimal
SNR from a `geo_flag=3` dipole-shell approximation to ultimate intrinsic SNR.
One converged basis may be shared by all finite-array topologies only when body,
materials, registration, grid/basis, frequency, electromagnetic boundaries,
source support, physics conventions, and numerical convergence contract are
identical. Changes to coil geometry or circuit values do not invalidate that
reference, but every array still needs its own frozen-circuit SNR/noise result.
Before a large BASIS run, require native geometry, mode/rank/resource probes,
disk and memory headroom, a case-local non-overwriting runner, checkpoint and
failure evidence, and explicit high-cost authorization. Never reuse a basis from
a different phantom, grid, support, or frequency.
For the 5 T 32-channel Loop/Dipole project, the first callable U1 engineering
probe is generated by `generate_head5t_uisnr_support_v01.py`, geometry-gated by
`RUN_HEAD5T_UISNR_GEOMETRY_ENGINEERING_v01.m`, and computed by
`RUN_HEAD5T_UISNR_BASIS_ENGINEERING_v01.m`. Its Hugo anonymous-material body and
432-triangle/648-RWG closed support make it an engineering resource probe only;
do not promote it to a qualified Head5T, converged UISNR, or research-validated
reference. The current loader requires the output `BasisFile` path to pre-exist,
so a zero-byte placeholder is allowed only while status is incomplete and must
be replaced and validated before the basis is consumed.

Before implementing, extracting, or comparing UISNR/ICP results, read
[references/uisnr-workflow-and-contracts.md](references/uisnr-workflow-and-contracts.md),
[references/uisnr-icp-complex-conventions.md](references/uisnr-icp-complex-conventions.md),
and [references/uisnr-convergence-validation.md](references/uisnr-convergence-validation.md).
Keep `Omega_support`, `Omega_primary`, and diagnostic masks distinct: native
UISNR optimizes each active voxel independently and does not produce one
ROI-average optimal current. Use the recorded physical MARIE coefficient
convention when mapping ICP weights back to current, and validate global phase,
mode-basis, blockwise, and voxel-order invariance. Use Cholesky/linear solves or
a recorded eigen/SVD pseudoinverse for scientific postprocessing; reserve
explicit `inv(Phi)` for labeled native-compatibility checks.

Adapt the non-overwriting templates under `assets/matlab-scripts/uisnr/` into a
new case/version rather than editing the bundled copies. Before trusting a
changed UISNR kernel, set `skillRoot`, run
`addpath(fullfile(skillRoot,'tests','uisnr'))`, then call
`RUN_ALL_UISNR_SKILL_TESTS(skillRoot)`. Project-specific ROIs, spatial
partitions, K budgets, network gates, and anatomical proxies remain case-local
unless independently validated as a generic contract.

When answering a documentation question, cite the bundled document name and section heading used. Distinguish current source-confirmed behavior from case history, recommended engineering gates, and unverified assumptions.

## TMD Hard-Bound Contract

Treat every circuit JSON `optim.minim/maxim` value as a persistent hard bound across tuning, matching, decoupling, and adaptive local searches. Intersect local search intervals with the declared bounds. Before JSON writeback, reject non-finite or out-of-bound values without opening or changing the active JSON. Expand a parameter domain only in a new versioned circuit JSON with a recorded physical rationale; never silently clip an optimizer result or widen a validated asset in place.

For mixed receive arrays whose ports use different matching-element types, keep
all matching and loss vectors aligned to the full physical-port dimension in the
joint cost function, preamplifier calibration, and final `match` calibration.
Never compress by element type and then index the compressed array by physical
port number. Normalize adaptive hard-bound vectors to one orientation before
intersection, and require scalar `all(...,'all')` assertions. Because `startup`
recursively adds archived case paths, formal TMD runners must also pin and record
the canonical `runner_T`, `runner_M_T`, and related Rx runner precedence.
Block-coordinate and focused refinements must derive each channel's optimizer
variable IDs from the detailed matching/tuning/mutual masks after fixed-row
compression. Never infer equal contiguous blocks from total variables divided by
physical ports; Loop/Dipole channels may own different variable counts and may
share symmetry variables.

For self-decoupled Loop candidates, a low off-diagonal S parameter at one
frequency is insufficient evidence. Treat the mode impedance, arm tuning, and
feed matching as separate roles; retune resonance and matching whenever scanning
the mode impedance. Record multi-frequency resonance and transmission-zero
locations using frequency-compatible raw networks, finite-Q component loss, and
robustness to load/component perturbations. Prefer a staged local design followed
by grouped and full-array minimax optimization. Preserve geometric overlap and
preamplifier decoupling where their neighbor classes require them, and decide
scientific value only from a frozen-circuit field/noise/SNR/g-factor comparison.

## Failure Handling

- If a MEX module reports `GLIBCXX` incompatibility, rebuild it with a MATLAB-supported compiler; do not change simulation inputs first.
- If automatic tuning produces nonphysical capacitor values, restore the versioned seed JSON, narrow bounds, and re-run. Do not retain an overwritten failed JSON as the only baseline.
- If the optimizer loses symmetry, check geometry indexing and `optim.symmetry` groups before widening optimization bounds.
