# MARIE Architecture and Callable Interfaces

## Purpose

Use this file as the concise, append-only registry for architecture changes and public development interfaces. Verify every entry against the active workspace; bundled information is a fallback snapshot.

## Ownership model

| Area | Authoritative location | Purpose |
|---|---|---|
| Governance | `AGENTS.md`, `MARIE_Agent_Harness.md` | Safety, permissions, scientific gates |
| Session entry | `START_HERE.md` | Current handoff and minimum reading order |
| Dynamic inventory | `tools/session_bootstrap.sh` | Read-only live snapshot; never starts MATLAB |
| Topic documentation | `docs/` | Guides, architecture, operations, validation, case history |
| Case evidence | `runs/<CaseTag>/` | Status, manifest, scripts, logs, snapshots, validation, reports |
| Simulation assets | `data/` | Inputs, bodies, coils, bases, raw solutions |
| Large-data plane | `/mnt/data/<user>/marie/projects/<ProjectID>/` | Large MAT/BASIS, checkpoints, project runs and archives; exposed through recorded project symlinks |
| Skill source | `marie-mri-coil-simulation skills/` | Version maintained with the workspace |
| Installed skill | `/home/<user>/.codex/skills/marie-mri-coil-simulation/` | Runtime deployment; mirror validated source |

## Callable interfaces

### Initialize a workspace session

```bash
cd /home/<user>/marie-tools
bash tools/session_bootstrap.sh [CaseTag]
```

Portable skill wrapper:

```bash
bash scripts/session_init.sh [workspace] [CaseTag]
```

Output is diagnostic evidence only. It does not prove MATLAB runtime precedence, Windows/Linux synchronization, or scientific validation.

### Inspect and prepare a case execution (Phase 1)

Run from the active workspace root:

```bash
bash tools/marie-agent/inspect.sh [CaseTag]
bash tools/marie-agent/prepare.sh <CaseTag> <stage>
bash tools/marie-agent/status.sh <CaseTag>
bash tools/marie-agent/tail.sh <CaseTag> [RunID]
bash tools/marie-agent/approve.sh <CaseTag> <RunID> "<explicit statement>"
bash tools/marie-agent/launch.sh <CaseTag> <RunID> --check
```

As of 2026-08-11, legacy production cases remain restricted to light, read-only geometry. The explicit training-closed-loop-v1 profile supports geometry, stage_a, tmd, stage_c, and post for isolated training cases. High-cost or JSON-writing stages require exact-run approval; requested workers are enforced before load_inputs, total production workers are capped at 96, GPU 0 is exclusive, and TMD uses a canonical active-JSON lock plus backup.

agent-case.json is the explicit per-case mapping for artifacts, resources, production profile, stage runners, and upstream dependencies. prepare.sh freezes source hashes and resolves only successful upstream artifacts. launch.sh rechecks drift and consumes protected approvals once. production_worker.py enforces case/resource/GPU/active-JSON locks and exposes MARIE_RUN_DIR plus MARIE_DEP_<LABEL> to frozen runners. Process state and scientific case state remain separate.

### Query bundled documentation

```bash
python scripts/query_marie_docs.py "<query>"
python scripts/query_marie_docs.py --files
python scripts/query_marie_docs.py --headings "<term>"
```

### Record an architecture update

Run from the skill source directory:

```bash
python scripts/record_architecture_update.py \
  --date YYYY-MM-DD \
  --title "short title" \
  --summary "what changed and why" \
  --paths "path1, path2" \
  --interfaces "command or API" \
  --compatibility "migration or compatibility impact" \
  --evidence "tests, reports, hashes"
```

The script appends to this file. Review the diff, refresh affected snapshots and manifest, run skill validation, deploy, and compare source/deployed hashes.

### Validate and deploy the skill

```bash
python /home/<user>/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  "marie-mri-coil-simulation skills"
```

Refresh snapshot hashes before validation:

```bash
python "marie-mri-coil-simulation skills/scripts/refresh_bundle_manifest.py" \
  --skill-root "marie-mri-coil-simulation skills" \
  --source-workspace /home/<user>/marie-tools
```

After validation, synchronize the complete source directory to the installed skill location without deleting unrelated files, then compare recursive file hashes. Deployment outside the workspace may require approval.

### MATLAB runtime path gate

From the MARIE repository root after `startup`:

```matlab
which load_inputs -all
which geo_assembly -all
which solver_wsvie -all
which co_simulation -all
which np_compute -all
```

Static `find` output does not replace this runtime check.

## Current handoff baseline

### 2026-08-23 — Case-local migration regression contract

- Scope: `runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/assets/migration/verification/`.
- Interface: the isolated P4 regression freezes the TMD-written circuit into a separate same-stem FixedCircuit MSH/JSON pair, disables every `optim.boolean`, and uses that input for `TMD=0` Stage C.
- Runtime rule: archived handoff source snapshots must not precede the live repository `src` tree; formal runners assert implementation resolution. Process pools may use isolated `CustomProcesses` job storage when the default local port allocation is unavailable, while MEX-dependent work must not use thread workers.
- Compatibility: case-local and additive; it does not change public `src/` APIs or authorize removal of legacy `data/` copies.
- Evidence: four-channel and three-channel isolated TMD plus frozen-circuit Stage C completed with finite arrays, reciprocal S matrices, Hermitian positive-semidefinite noise matrices, and all configured network gates passing. See `assets/migration/P4正式回归报告_v01.md`.

### 2026-08-23 — Recoverable isolation of legacy project assets

- Scope: the frozen 3T RF-coil migration map contains 723 project-owned sources and 2 shared-body keep records.
- Interface: `tools/isolate_3t_coilopt_p6_legacy_assets.py` defaults to dry-run; execution requires an exact token and timestamp, verifies source and case-local target hashes, then atomically moves only allowlisted sources into `data/_trash/<timestamp>/3T_RFCoilOpt_migration/` while preserving relative paths.
- Failure behavior: any failed post-move hash check triggers reverse-order rollback of files moved by that invocation.
- Compatibility: shared bodies remain in `data/bodies/`; case-local inputs remain authoritative. Empty legacy directory shells may remain. Isolation is recoverable and does not authorize permanent deletion.
- Evidence: `assets/migration/verification/p6_isolation_20260823T214303.json` records all 723 source/target/isolated paths and hashes; case-only four-channel and three-channel geometry checks passed after isolation.

### 2026-08-24 — Allowlisted purge after migration validation

- Scope: only the 723 isolated paths recorded by the P6 receipt, after a post-migration case-local full Stage C reproduced the pre-migration network result.
- Interface: `tools/purge_3t_coilopt_p6_isolated_assets.py` is dry-run by default, rejects extra or missing trash content and missing authoritative targets, and requires an exact execution token before unlinking individual allowlisted files.
- Safety boundary: no recursive broad deletion; shared bodies, case-local authoritative assets, migration manifests and simulation evidence remain. Only empty directories derived from recorded legacy source parents are removed separately.
- Evidence: `assets/migration/verification/p6_purge_20260824.json` records 723 permanently deleted files and 3,298,063,058 bytes; `p6_empty_directory_cleanup_20260824.json` records 193 removed empty directory shells.

### 2026-08-24 — E2 three-coil handoff package v02

- Scope: `runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/handoff_packages/E2_ThreeCoil_Handoff_20260824_v02/` and its independent tar.zst archive; v01 remains immutable.
- Interface: the portable workspace now carries the current E2 tree plus case-local `runs/.../assets/{inputs,coils}`. Shared Hugo body remains under `workspace/data/bodies`; multi-GB UISNR BASIS remains optional.
- Runtime contract: candidate-specific Stage A, TMD backup/lock/seed/attempt, network gate, separate all-disabled FixedCircuit, process-based Stage C, noise/SNR gates. Archived source snapshots are comparison-only and must not enter the formal MATLAB path.
- Status boundary: Grid Search 1, Gradient 1, Grid Search 2 and first-three-stage Figure 17/18-style SNR figures are included; Gradient 2 and strict UISNR are not complete.
- Evidence: 1,397 content files plus inventory were hashed successfully; archive SHA-256 is `c66fcc2f245fdd52aaefb06f350513f26b473435337e20f5d861228ebd08c71c`, and `zstd -t` passed.

- As of 2026-08-11, the latest executed 8-channel reproduction is `runs/5T_1H_Sphere200_8Ch_LoopRx_1Row_R115_H140_Span50_v01/reproductions/repro_20260811_1828/`.
- Its WSVIE/TMD/field/postprocessing workflow completed and is recorded as `em-solved`; the network gate failed because worst off-diagonal `SP_s=-10.544 dB` did not meet the project `-12 dB` gate.
- The active workspace is dirty and contains user/history assets. Preserve them.
- Windows/Linux synchronization is not inferred from names; prove it with evidence from both sides.
- Phase 1 execution preparation is available through `tools/marie-agent/`; the first no-launch evidence is `runs/5T_1H_Sphere200_8Ch_LoopRx_1Row_R115_H140_Span50_v01/executions/20260811_193535_geometry/`.

## Architecture update registry

### 2026-08-11 — New-session initialization and evidence handoff

- Summary: Added a stable `START_HERE.md` entry point and a dynamic read-only bootstrap so a new session can recover live context without relying on chat history.
- Paths: `START_HERE.md`, `tools/session_bootstrap.sh`, `docs/operations/MARIE_新会话初始化机制.md`, `AGENTS.md`, `docs/README.md`.
- Interfaces: `bash tools/session_bootstrap.sh [CaseTag]`; portable wrapper `bash scripts/session_init.sh [workspace] [CaseTag]`.
- Compatibility: Additive. Does not start MATLAB or alter simulation assets. Existing cases remain valid.
- Evidence: Bash syntax check, global invocation, case-scoped invocation, and post-test process check passed on 2026-08-11.

### 2026-08-11 — Skill-governed architecture maintenance

- Summary: Made session initialization, interface lookup, architecture registration, snapshot refresh, validation, and source/deployment equality part of the MARIE skill workflow.
- Paths: `SKILL.md`, `references/architecture-interfaces.md`, `references/document-index.md`, `scripts/session_init.sh`, `scripts/record_architecture_update.py`.
- Interfaces: See the callable interfaces above.
- Compatibility: Additive; repository skill source becomes the maintenance authority and the installed skill is a validated deployment mirror.
- Evidence: Record script and session wrapper tests plus `quick_validate.py`; deployment hashes are checked during installation.

### 2026-08-11 — Phase 1 execution preparation interface

- Summary: Updated the remote-development guide to v1.2 and added explicit per-case configuration, two-level execution evidence, and no-launch inspect/prepare/status/tail interfaces.
- Paths: docs/operations/MARIE_Codex远程开发具体实施指南.md, tools/marie-agent/, tools/session_bootstrap.sh, runs/5T_1H_Sphere200_8Ch_LoopRx_1Row_R115_H140_Span50_v01/agent-case.json, runs/5T_1H_Sphere200_8Ch_LoopRx_1Row_R115_H140_Span50_v01/executions/20260811_193535_geometry/.
- Interfaces: bash tools/marie-agent/inspect.sh [CaseTag]; bash tools/marie-agent/prepare.sh <CaseTag> <stage>; bash tools/marie-agent/status.sh <CaseTag>; bash tools/marie-agent/tail.sh <CaseTag> [RunID].
- Compatibility: Additive. Existing logs, reproductions, and scientific status remain in place. prepare creates evidence only; launch/execute is unavailable. EM and post stages are disabled for the completed 8-channel reproduction to avoid overwriting evidence..
- Evidence: bash -n, Python compile, JSON parse, inspect/prepare/status/tail smoke tests, disabled-stage refusal RC=5, prepared execution state with launch_available=false, and no MATLAB/TMD/MRGF process observed after testing..

### 2026-08-11 — Phase 2A fail-closed launch preflight

- Summary: Added frozen runner/config snapshots, schema-v2 gate digest, case-level preparation lock, exact-run expiring approval records, and source-drift launch preflight while keeping real tmux/MATLAB submission disabled.
- Paths: tools/marie-agent/prepare.py, tools/marie-agent/approve.py, tools/marie-agent/launch.py, docs/operations/MARIE_Codex远程开发具体实施指南.md, START_HERE.md, runs/5T_1H_Sphere200_8Ch_LoopRx_1Row_R115_H140_Span50_v01/executions/20260811_195711_geometry/.
- Interfaces: bash tools/marie-agent/approve.sh <CaseTag> <RunID> <statement>; bash tools/marie-agent/launch.sh <CaseTag> <RunID> --check.
- Compatibility: Additive schema v2 for new preparations. Existing schema-v1 evidence remains immutable. Real submission without --check fails closed with RC=11; launch/execute is not yet enabled..
- Evidence: Bash and Python syntax checks passed; geometry prepare created frozen runner/config snapshots and gate digest; launch --check RC=0; real launch RC=11; no exitcode created and no MATLAB/TMD/MRGF process observed..

### 2026-08-11 — Phase 2B isolated runtime foundation

- Summary: Added a test-only atomic state/event runtime with lifecycle case locks, canonical active-JSON locks, split exit codes, signal handling, detached tmux tests, and a strict temporary-root SHA-256 executable allowlist.
- Paths: tools/marie-agent/runtime.py, tools/marie-agent/tests/, docs/operations/MARIE_Phase2B_fake_selftest_20260811.md, docs/operations/MARIE_Codex远程开发具体实施指南.md, START_HERE.md.
- Interfaces: python tools/marie-agent/tests/selftest.py; production launch remains bash tools/marie-agent/launch.sh <CaseTag> <RunID> --check only.
- Compatibility: Test-only and additive. It does not read production commands and is not connected to launch.py. Production submission without --check remains disabled with RC=11..
- Evidence: Initial selftest exposed and corrected a missing temporary lock directory. Final suite passed exit0, exit42, SIGTERM, forbidden executable, case lock, canonical JSON symlink alias lock, detached tmux, and event revision tests. Precise process-name check found no MATLAB/TMD/MRGF..

### 2026-08-11 — Phase 2B approval and recovery completion

- Summary: Completed isolated approval single-use consumption and startup_unknown/orphan recovery classification, raising the fake-runner matrix to eleven passing cases.
- Paths: tools/marie-agent/runtime.py, tools/marie-agent/tests/selftest.py, docs/operations/MARIE_Phase2B_fake_selftest_20260811.md, START_HERE.md.
- Interfaces: python tools/marie-agent/tests/selftest.py; production launch remains disabled with RC=11.
- Compatibility: Test-only additions. No production MATLAB submission was enabled and scientific status is unchanged..
- Evidence: Eleven isolated cases passed; production launch RC=11; no MATLAB/TMD/MRGF executable process observed..

### 2026-08-11 — Restricted production geometry worker

- Summary: Enabled the production tmux worker only for light, read-only geometry executions and completed the first real 8-channel geometry-only acceptance run.
- Paths: tools/marie-agent/launch.py, tools/marie-agent/production_worker.py, runs/5T_1H_Sphere200_8Ch_LoopRx_1Row_R115_H140_Span50_v01/executions/20260811_204548_geometry/, START_HERE.md.
- Interfaces: bash tools/marie-agent/launch.sh <CaseTag> <RunID>; permitted only for stage=geometry, cost=light, writes_active_json=false.
- Compatibility: All non-geometry, non-light, or JSON-writing stages fail closed with RC=12. Scientific status is not automatically changed..
- Evidence: MATLAB R2025b geometry run succeeded in detached tmux; process and wrapper exitcode files are 0; GEOMETRY_GATE=PASS; frequency 212.887392590 MHz; N_WIE=640; active JSON before/snapshot hashes match; tmux ended; no MATLAB workers remained..

### 2026-08-11 — Enforced workers and training closed-loop profile

- Summary: Added exact per-run MATLAB process-pool enforcement, a 96-worker global production budget, GPU and canonical JSON locking, immutable upstream dependency resolution, and an allowlisted isolated training profile for geometry, Stage A, TMD, Stage C, and post.
- Paths: tools/marie-agent/, runs/5T_1H_Sphere200_8Ch_LoopRx_Training_v01/, onboarding/MARIE_Agent_Quickstart_8Ch_v01/, START_HERE.md, docs/operations/MARIE_Agent训练闭环与并发资源治理.md.
- Interfaces: bash tools/marie-agent/prepare.sh <CaseTag> <stage>; bash tools/marie-agent/approve.sh <CaseTag> <RunID> <statement>; bash tools/marie-agent/launch.sh <CaseTag> <RunID> [--check]; MATLAB marie_agent_configure_pool(workers).
- Compatibility: Legacy cases remain geometry-only. Full stages are enabled only for agent-case.json production_profile=training-closed-loop-v1; high-cost and JSON-writing stages remain exact-run approval gated..
- Evidence: 11 fake-runner tests passed; Python/Bash/JSON checks passed; MATLAB checkcode reported zero findings for five runners; Training geometry RunID 20260811_231346_geometry passed with requested=actual=16, RC 0/0, 212.887392590 MHz, N_WIE=640; unapproved Stage A check refused with RC=6..

### 2026-08-14 — TMD declared hard-bound and fail-closed JSON writeback

- Summary: Local tuning/matching/decoupling intervals now intersect persistent JSON optim.minim/maxim bounds; non-finite or out-of-bound final values are rejected before JSON open/write.
- Paths: src/src_physics/src_electronics/**/co_simulation_matching_tuning_settings.m; runner_M_T_D.m; runner_M_T_PD.m; src/src_geometry/scoil_geometry/ports_geo/geo_scoil_print_lumped_elements.m; docs/architecture/MARIE_src源码模块与算法详解.md; marie-mri-coil-simulation skills/.
- Interfaces: MARIE:TMD:EmptyHardBoundIntersection; MARIE:TMD:InvalidHardBounds; MARIE:TMD:HardBoundViolation; geo_scoil_print_lumped_elements fail-closed writeback contract.
- Compatibility: Stricter safety behavior: previously accepted out-of-bound TMD values now fail before JSON mutation. Valid in-bound workflows are unchanged..
- Evidence: MATLAB checkcode zero findings on both duplicated settings/M_T_D/M_T_PD implementations and writer; TEST_WP6_TMD_HARD_BOUNDS_v01 PASS including rejected-write hash invariance; WP6 candidate02 fail-closed; WP6 Stage B v06 and Stage C v04 passed..

### 2026-08-18 — WP7 receive-coil optimization pipeline v02

- Summary: Documented the four-layer WP7 optimization architecture and candidate-specific Stage A/TMD/Stage C feedback contract; added a versioned pipeline diagram and detailed milestone report.
- Paths: docs/architecture/MARIE_WP7优化框架架构与流程_v01.md, docs/architecture/assets/MARIE_WP7_Optimization_Pipeline_v02.{mmd,svg,png}, runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/wp7_optimizer/reports/WP7_基础优化框架阶段性设计报告_v01.md, docs/operations/MARIE_Codex远程开发具体实施指南.md, marie-mri-coil-simulation skills/.
- Interfaces: Current case-local PRECOMPUTE_WP7_FOUR_STAGE_A_v01; RUN_WP6_TMD_TRUST25_v02(rawFile,coilJson,out,seed); FINALIZE_WP7_*; POST_WP7_*; generic production API remains future work.
- Compatibility: Documentation and diagram update only; no solver, input, threshold, runner behavior, or validated simulation asset changed. Replaces a stale reference to missing mri_rf_coil_agent_pipeline_design.md..
- Evidence: WP7 controller pytest 12/12 PASS; final comparison and SNR summary JSON parsed; architecture/report links and PNG/SVG assets validated..

### 2026-08-22 — Case-local AssetRoot and 3T reproduction asset migration

- Summary: Added case-local asset resolution and migrated project-owned 3T reproduction inputs, coils, support surfaces, and BASIS into the case tree while retaining shared bodies and legacy source copies.
- Paths: `src/src_utils/src_loaders/marie_resolve_asset.m`, `load_inputs.m`, `geo_assembly.m`, duplicated electronics settings loaders, `runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/assets/`, active 3T case scripts/configs, workspace governance documents, and this skill.
- Interfaces: optional input JSON `AssetRoot`; controlled `runs/<ProjectCaseTag>/assets/inputs/` auto-discovery; resolved `inputs.input_file`, `asset_root`, `rhbm_file`, `coil_file`, `wire_file`, `shield_file`, `basis_support_file`, and `basis_file` fields.
- Compatibility: Additive with legacy `data/` fallback. Existing JSON files remain valid. Shared Hugo bodies remain in `data/bodies/`. Historical reports and handoff packages remain immutable. Removing legacy project copies is a separate authorized cleanup phase.
- Evidence: 723 files / 3,298,063,058 bytes copied and source/target SHA-256 verified; three-pair asset-resolution unit test passed; 76 Python and 4 shell scripts passed syntax checks; 149 MATLAB scripts passed checkcode; migrated 4-channel v25 and 3-channel v07 geometry/visualization gates passed.

### 2026-08-26 — Case-local 3T project re-entry checklist

- Summary: Made the 3T RF-coil optimization case START_HERE the explicit post-bootstrap recovery interface, corrected the active handoff from stale WP7 to WP8-R2, and defined evidence priority, R2 geometry gates, permissions, and init completion criteria.
- Paths: START_HERE.md, runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/START_HERE.md, marie-mri-coil-simulation skills/.
- Interfaces: bash tools/session_bootstrap.sh 3T_1H_Duke5mm_RFCoilOpt_Repro_v01; read runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/START_HERE.md.
- Compatibility: Additive documentation interface; no runner, solver, input, asset, threshold, or scientific result changed. The 2026-08-21 WP7 handoff remains archived in place but is explicitly non-current..
- Evidence: Read-only session bootstrap on 2026-08-26; status.json and manifest WP8 state; wp8_latest_evidence_audit_20260825.md; WP8_R1_selected_branch_repeatability_completion_v20.md..

### 2026-08-26 — Non-destructive E2 three-coil evidence view

- Summary: Added a case-local user-facing organization layer for prior three-coil optimization configurations, raw MAT/log evidence, structured metrics, figures, and reports without moving or duplicating authoritative simulation assets.
- Paths: runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/wp8_experiments/e2_three_coil/README.md, runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/wp8_experiments/e2_three_coil/整理视图_v01/, runs/3T_1H_Duke5mm_RFCoilOpt_Repro_v01/START_HERE.md, marie-mri-coil-simulation skills/.
- Interfaces: Read e2_three_coil/README.md or e2_three_coil/整理视图_v01/README.md; use generated CSV inventories for discovery; follow relative symlinks to authoritative originals..
- Compatibility: Additive, read-only browsing contract. Existing runner paths, MAT/log/JSON assets, hashes, gates, and scientific status are unchanged. The view must not be used as a MATLAB execution root..
- Evidence: All relative links resolved; inventory and summary files created; source metrics reconciled against stage CSV/JSON; no MATLAB process launched and no original asset moved..

### 2026-09-01 — 5T 32-channel Loop-dipole project documentation authority

- Summary: Moved the five uploaded 5T Loop-dipole planning documents into the project-owned docs tree, retired the upload directory, corrected live AssetRoot compatibility status, and added a source-backed feasibility review.
- Paths: projects/5t_32ch_loop_dipole_rx/docs/, projects/5t_32ch_loop_dipole_rx/runs/_bootstrap/, marie-mri-coil-simulation skills/references/architecture-interfaces.md.
- Interfaces: Read projects/5t_32ch_loop_dipole_rx/docs/README.md; start with docs/40_validation/PROJECT_FEASIBILITY_REVIEW_v01.md.
- Compatibility: Project-local additive authority change; former linux_upload_5T_32Ch_Loop_Dipole_Project_Docs path is retired. No solver, runner, input, shared asset, threshold, or source API changed..
- Evidence: Pre-migration and post-migration SHA-256 comparison for five files; link/path audit; Session 0 environment, asset and IC-v1.1 source audit..

### 2026-09-01 — 5T Loop-dipole core simulation plan and log feedback contract

- Summary: Established a project-core staged MARIE implementation plan with frozen initial conditions, source-confirmed call chains, project-local data paths, Stage A/B/C gates, resource/authorization rules, and an append-only logging protocol that controls evidence-based plan revisions.
- Paths: projects/5t_32ch_loop_dipole_rx/docs/30_simulation/CORE_MARIE_SIMULATION_IMPLEMENTATION_PLAN_v01.md, projects/5t_32ch_loop_dipole_rx/docs/00_governance/SIMULATION_LOG_AND_PLAN_REVISION_PROTOCOL_v01.md, projects/5t_32ch_loop_dipole_rx/logs/, projects/5t_32ch_loop_dipole_rx/docs/README.md, marie-mri-coil-simulation skills/references/architecture-interfaces.md.
- Interfaces: Read the current CORE_MARIE_SIMULATION_IMPLEMENTATION_PLAN_vNN before work; create each run log from logs/templates/run_log_template.md; use PlanImpact and ADR flow before revising the core plan..
- Compatibility: Project-local additive workflow contract. Default MARIE_runner and CO_SIMULATION_runner remain unchanged and are not project output interfaces. No solver, input, threshold, shared asset, or runtime source was modified..
- Evidence: Current-source review of load_inputs, marie_resolve_asset, geo_assembly, MARIE/BASIS/CO_SIMULATION runners and training Stage A/B/C/post runners; document heading/path checks; initial development log..

### 2026-09-01 — Project-owned case and RunTag geometry interface

- Summary: Established the 5T Loop-dipole project-owned immutable case and evidence layout, deterministic M0 generator/static gate, case-local geometry runner, and log-driven plan correction contract.
- Paths: projects/5t_32ch_loop_dipole_rx/{cases,runs,tools,logs,docs}; marie-mri-coil-simulation skills/.
- Interfaces: python projects/5t_32ch_loop_dipole_rx/tools/geometry_generation/generate_m0_loop_case.py --project-root projects/5t_32ch_loop_dipole_rx; python projects/5t_32ch_loop_dipole_rx/tools/validation/check_m0_loop_case.py --project-root ... --report ...; MATLAB case-local CHECK_*_GEOMETRY.m with MARIE_RUN_DIR.
- Compatibility: Additive project-local layout. Shared body remains read-only; toolkit data/ and root runs/ are unchanged. MATLAB run(...) callers must not assume pwd remains the repository root..
- Evidence: Static gate passed 18/18; geometry RunTag 20260901T213822+0800_geometry_retry2 exited 0 with 2/2 workers, 212.887392590 MHz, 72 WIE segments, one physical port, 15 mm clearance, PNG/metrics/log hashes recorded; no solver/BASIS/TMD executed..

### 2026-09-01 — 5T project Stage A cache and diagnostics interface

- Summary: Added a project-owned TMD=1 Stage A input, raw-network precompute runner, checkpoint/metrics outputs, read-only YPn diagnostics, and evidence-driven resource rebaseline for the M0 one-channel case.
- Paths: projects/5t_32ch_loop_dipole_rx/cases/5T_1H_Sphere240_1Ch_LoopRx_M0_ICv11_v01/{inputs,scripts,status.json}; projects/5t_32ch_loop_dipole_rx/runs/.../20260901T214543+0800_stage_a_probe/; projects/5t_32ch_loop_dipole_rx/docs/30_simulation/CORE_MARIE_SIMULATION_IMPLEMENTATION_PLAN_v01.md.
- Interfaces: MATLAB PRECOMPUTE_*_STAGE_A.m with MARIE_RUN_DIR; MATLAB VALIDATE_*_STAGE_A.m; outputs YPn_<CaseTag>.mat, MREDM_preTMD_<CaseTag>.mat, stage_a_metrics.json, stage_a_validation.json.
- Compatibility: Additive and case-local. No source, shared asset, root runs/, TMD JSON, or threshold changed. Cache is valid only for the frozen body, geometry, frequency, PWC basis, port topology, and code state..
- Evidence: RunTag 20260901T214543+0800_stage_a_probe exited 0: 4x4 finite YPn, reciprocity 0, minimum Hermitian-part eigenvalue 3.9757671541e-07, rcond 0.181138054357, 20:05 wall, 3.38 GiB peak RSS, active circuit hash invariant..

### 2026-09-01 — 5T Phase 1 remaining geometry cases and open-wire blocker

- Summary: Added deterministic D110, D170, and four-channel Loop/Dipole M0 case generation, shared static/geometry gates, and documented a source-confirmed ProcessLoops open-chain dimension defect that blocks Phase 1 completion.
- Paths: projects/5t_32ch_loop_dipole_rx/{cases,tools,status.json,docs/40_validation/PHASE1_COMPLETION_GATE_v01.md,runs/_bootstrap/phase1_remaining_static_validation.json}.
- Interfaces: python tools/geometry_generation/generate_phase1_remaining_cases.py; python tools/validation/check_phase1_remaining_cases.py; MATLAB run_phase1_geometry_case(caseTag,expectedSegments,expectedElements,expectedPorts).
- Compatibility: Additive project files only. No MARIE src repair was made. D110/D170/four-channel MATLAB geometry remains blocked until separately authorized ProcessLoops repair and regression..
- Evidence: All three remaining static cases passed. D110 RunTag 20260901T222100+0800_geometry failed before solve at ProcessLoops line 23 with 56x3 destination versus 54x3 source; no TMD or JSON write occurred..

### 2026-09-01 — Open and mixed WIE component reconstruction

- Summary: Repaired ProcessLoops to rebuild closed and open wire components without unequal-size assignment, remap lumped ports by original spatial position, and expose the N-to-N-2 open-support contract; closed/open/mixed Phase-1 regressions passed.
- Paths: src/src_geometry/scoil_geometry/triangle_geo/ProcessLoops.m; projects/5t_32ch_loop_dipole_rx/docs/40_validation/PHASE1_COMPLETION_GATE_v01.md; Phase-1 case runs; marie-mri-coil-simulation skills/.
- Interfaces: ProcessLoops(wire): closed N segments -> N supports; open N segments -> N-2 supports; mixed component loop_start/loop_end and port.t are rebuilt.
- Compatibility: Behavioral bug fix authorized by user. Closed-loop geometry remains 72 supports. Open-chain inputs that previously failed now assemble; invalid ranges, short chains, or unmappable/final ports fail closed with MARIE:WIE identifiers..
- Evidence: Before hash 12a4f381...; after 8ddc675b...; MATLAB checkcode clean; D110 54, D170 54, mixed 252, closed Loop 72 supports; all geometry runs exited 0 at 212.887392590 MHz and 15 mm clearance; no solve/TMD/JSON write..

### 2026-09-02 — Mixed-port Rx TMD alignment and Phase-2 isolated A/B/C interface

- Summary: Added project-local resumable A/B/C automation, pinned canonical TMD runners, and repaired mixed matching-type alignment across Rx joint cost, adaptive bounds, preamplifier calibration, and final match calibration.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/matlab/run_phase2_abc_case.m; projects/5t_32ch_loop_dipole_rx/runs/*/20260901T233806+0800_phase2_abc; src/src_physics/src_electronics/co_simulation/{co_sim_cost_functions/matching_and_tuning_and_preamplifierdecoupling.m,co_sim_runners/runner_M_T_PD.m,co_sim_calibration/preamplifier_match.m,co_sim_calibration/match.m}; marie-mri-coil-simulation skills/..
- Interfaces: run_phase2_abc_case with MARIE_CASE_TAG/MARIE_RUN_DIR/MARIE_WORKERS/MARIE_PHYSICAL_PORTS/MARIE_TEMPORARY_PORTS; mixed-port matching vectors remain full physical-port length; adaptive bounds are column vectors and scalar asserted; canonical runner_T/runner_M_T precedence is mandatory..
- Compatibility: Authorized behavioral bug fixes for mixed Rx matching topologies. Homogeneous Loop path remains accepted. Hard bounds remain unchanged and fail closed; D110/D170/mixed v01 are rejected rather than clipped or widened..
- Evidence: MATLAB checkcode clean; Loop A/B/C accepted at SP_p=-24.3575 dB and B/C network relerr 0; D110/D170 finite chains rejected near 0 dB; mixed 14x14 Stage A finite/reciprocal, four sequential first-error stacks closed until hard-bound guard correctly rejected the circuit; Phase2 report..

### 2026-09-02 — 5T dipole topology Stage-B fail-closed comparison

- Summary: Added three controlled one-channel dipole topology cases and a project-local Phase-2 runner gate that refuses Stage C whenever tuning and matching fail, preventing invalid field and SNR evidence.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/matlab/run_phase2_abc_case.m, projects/5t_32ch_loop_dipole_rx/tools/automation/prepare_dipole_topology_comparison_runs.py, projects/5t_32ch_loop_dipole_rx/tools/geometry_generation/generate_dipole_topology_comparison.py, projects/5t_32ch_loop_dipole_rx/docs/40_validation/DIPOLE_TOPOLOGY_COMPARISON_{SETUP,RESULTS}_v01.md.
- Interfaces: python projects/5t_32ch_loop_dipole_rx/tools/automation/prepare_dipole_topology_comparison_runs.py; MATLAB run_phase2_abc_case reads MARIE_PROJECT_ROOT, MARIE_CASE_TAG, MARIE_RUN_TAG, MARIE_ACTIVE_INPUT, MARIE_ACTIVE_COIL_JSON and MARIE_NUM_WORKERS.
- Compatibility: Project-local additive safety tightening; no public src API or scientific threshold changed. Runs whose Stage B gate fails now stop before Stage C instead of emitting diagnostic fields that could be mistaken for accepted SNR..
- Evidence: All three geometry gates passed; isolated RunTag 20260902T150000+0800_topology_abc completed finite reciprocal Stage A matrices, then failed Stage B at SP_p=-0.005081/-0.005057/-0.005307 dB and produced no Stage C files; details in DIPOLE_TOPOLOGY_COMPARISON_RESULTS_v01.md.

### 2026-09-02 — Cached-YPn dipole matching feasibility scanner

- Summary: Added a deterministic read-only fixed-frequency matching-network screen for the three D170 cached YPn matrices, preserving component hard bounds and separating provisional impedance feasibility from MARIE Stage B acceptance.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/validation/scan_cached_dipole_matching.py, projects/5t_32ch_loop_dipole_rx/runs/_bootstrap/dipole_matching_feasibility_20260902/, projects/5t_32ch_loop_dipole_rx/status.json, projects/5t_32ch_loop_dipole_rx/docs/40_validation/DIPOLE_TOPOLOGY_COMPARISON_RESULTS_v01.md.
- Interfaces: python projects/5t_32ch_loop_dipole_rx/tools/validation/scan_cached_dipole_matching.py.
- Compatibility: Additive project-local read-only diagnostic; it does not mutate circuit JSON, change hard bounds, replace TMD, or authorize Stage C..
- Evidence: Python compile passed; deterministic 3-case by 9-network scan completed; original CCC network failed while two mixed C/L networks produced provisional in-bound 50-ohm solutions recorded in JSON and CSV..

### 2026-09-02 — C3 cached-YPn Stage-B-only candidate interface

- Summary: Added versioned mixed-network candidate preparation and a fail-closed MATLAB runner that reuses unchanged-geometry raw YPn, records TMD JSON snapshots and metrics, and always stops before Stage C.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/automation/prepare_c3_mixed_match_stage_b.py, projects/5t_32ch_loop_dipole_rx/tools/matlab/run_cached_stage_b_candidate.m, projects/5t_32ch_loop_dipole_rx/docs/40_validation/C3_MIXED_MATCH_STAGEB_RESULTS_v01.md, projects/5t_32ch_loop_dipole_rx/status.json.
- Interfaces: python projects/5t_32ch_loop_dipole_rx/tools/automation/prepare_c3_mixed_match_stage_b.py --variant c-l-c|l-c-l --stamp RunTag; MATLAB run_cached_stage_b_candidate with MARIE_CASE_TAG and MARIE_RUN_DIR.
- Compatibility: Project-local additive; cached YPn reuse is permitted only for unchanged body, geometry, frequency, basis and temporary-port topology. The runner cannot execute Stage C..
- Evidence: v03 and v04 reused byte-identical parent MSH and finite reciprocal 3x3 YPn; Stage B returned SP_p=-5.707973 and -3.664959 dB, both rejected, with stage_c_executed=false and preserved before/after JSON snapshots..

### 2026-09-02 — C3-v05 lengthened-fold geometry and selective Stage-A preparation

- Summary: Added a C3-derived dipole with 45 mm folds at both ends, increasing the conductor path from 206 to 260 mm, plus selective preparation of a single isolated topology run.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/geometry_generation/generate_c3_lengthened_candidate.py, projects/5t_32ch_loop_dipole_rx/tools/geometry_generation/generate_dipole_topology_comparison.py, projects/5t_32ch_loop_dipole_rx/tools/automation/prepare_dipole_topology_comparison_runs.py, projects/5t_32ch_loop_dipole_rx/cases/5T_1H_Sphere240_1Ch_DipoleRx_D170_C3_Fold45_End2L_MixedMatch_M0_ICv11_v05, projects/5t_32ch_loop_dipole_rx/status.json.
- Interfaces: python projects/5t_32ch_loop_dipole_rx/tools/geometry_generation/generate_c3_lengthened_candidate.py --project-root projects/5t_32ch_loop_dipole_rx; prepare_dipole_topology_comparison_runs.py --case CaseTag --stamp RunTag.
- Compatibility: New versioned geometry; parent assets are unchanged. Its prior YPn is invalid and cannot be reused. Stage A is prepared but not launched..
- Evidence: Python compile and JSON parsing passed; engineering 3D view inspected; MATLAB geometry-only gate passed at 212.88739259 MHz with 82 WIE supports, 3 temporary elements, one physical port and 15 mm clearance; frozen Stage-A manifest records input/MSH/circuit hashes..

### 2026-09-02 — Project Phase-2 Stage-A stop control

- Summary: Added a fail-closed MARIE_STOP_AFTER_STAGE_A control to the project Phase-2 runner so newly versioned geometry can complete and validate raw YPn without automatically entering JSON-writing TMD or Stage C.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/matlab/run_phase2_abc_case.m, projects/5t_32ch_loop_dipole_rx/docs/40_validation/C3_V05_STAGEA_RESULT_v01.md, projects/5t_32ch_loop_dipole_rx/status.json.
- Interfaces: Set MARIE_STOP_AFTER_STAGE_A=1 when invoking run_phase2_abc_case.
- Compatibility: Additive opt-in stop; unset behavior retains the existing gated A/B/C chain. It does not change solver equations, thresholds, or input assets..
- Evidence: C3-v05 RunTag 20260902T174000+0800_topology_abc completed finite reciprocal 3x3 YPn with GMRES 233/231/277 and logged PHASE2_STOP_AFTER_STAGE_A=1; no TMD or Stage C artifacts were created..

### 2026-09-02 — Project Phase-2 Stage-B stop control and C3-v05 result

- Summary: Added an opt-in MARIE_STOP_AFTER_STAGE_B control that records TMD metrics and snapshots then prohibits Stage C regardless of network acceptance; used it for C3-v05.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/matlab/run_phase2_abc_case.m, projects/5t_32ch_loop_dipole_rx/docs/40_validation/C3_V05_STAGEA_RESULT_v01.md, projects/5t_32ch_loop_dipole_rx/status.json.
- Interfaces: Set MARIE_STOP_AFTER_STAGE_B=1 when invoking run_phase2_abc_case.
- Compatibility: Additive opt-in stop; unset behavior retains the existing fail-closed A/B/C chain. Stage-B metrics and JSON snapshots are preserved before return..
- Evidence: C3-v05 resumed its finite reciprocal Stage-A cache, completed TMD in 3.582 s, recorded SP_p=-13.381609 dB and accepted_for_stage_c=false, logged Stage C not executed, and preserved TMD before/after circuit snapshots..

### 2026-09-02 — Parameterized C3 lengthened-fold v06 Stage-A workflow

- Summary: Parameterized the C3 lengthened-fold generator for 45/60 mm folds and v05/v06 candidates, then completed geometry and a fresh Stage A for the 290 mm total-path v06.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/geometry_generation/generate_c3_lengthened_candidate.py, projects/5t_32ch_loop_dipole_rx/tools/automation/prepare_dipole_topology_comparison_runs.py, projects/5t_32ch_loop_dipole_rx/cases/5T_1H_Sphere240_1Ch_DipoleRx_D170_C3_Fold60_End2L_MixedMatch_M0_ICv11_v06, projects/5t_32ch_loop_dipole_rx/docs/40_validation/C3_V06_STAGEA_RESULT_v01.md, projects/5t_32ch_loop_dipole_rx/status.json.
- Interfaces: generate_c3_lengthened_candidate.py --project-root PATH --fold-mm 45|60 --version 5|6.
- Compatibility: Versioned additive geometry; v05 remains unchanged. v06 invalidates parent YPn and uses a fresh Stage A. Hard bounds and solver interfaces are unchanged..
- Evidence: v06 geometry gate passed with 82 WIE supports and 15 mm clearance; fresh 8-worker Stage A produced finite reciprocal 3x3 YPn, GMRES 297/344/275, assembly 1104.846 s and solve 128.409 s; Stage B/C not executed..

### 2026-09-02 — RunTag-safe cached Stage-B rebinding and v05 repeatability diagnosis

- Summary: Rebound copied Stage-A checkpoints to their isolated RunTag working input, geometry and RLC before TMD writeback; added deterministic v05 cached-YPn repeat preparation and documented that canonical TMD runners reset RNG internally.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/matlab/run_phase2_abc_case.m, projects/5t_32ch_loop_dipole_rx/tools/automation/prepare_v05_tmd_seed_repeats.py, projects/5t_32ch_loop_dipole_rx/docs/40_validation/C3_V05_TMD_REPEATABILITY_v01.md, projects/5t_32ch_loop_dipole_rx/status.json.
- Interfaces: prepare_v05_tmd_seed_repeats.py --project PATH --stamp RunTag --seeds N...; MARIE_TMD_SEED records the outer request but does not override canonical internal rng resets.
- Compatibility: Project-local fail-closed safety improvement; source TMD runners are unchanged. Copied caches must retain identical body, geometry, frequency, basis and temporary-port topology..
- Evidence: Three isolated v05 repeats used identical YPn/circuit hashes and returned identical SP_p=-13.381608807 dB plus identical final circuit hash; source inspection confirmed rng(counter_repeat) in runner_T, runner_M_T and runner_M_T_PD; Stage C remained disabled..

### 2026-09-02 — Canonical TMD seed-offset interface and recoverable redundant-cache isolation

- Summary: Added a backward-compatible canonical TMD repeat-seed offset and an exact-allowlist workflow for isolating hash-identical Stage-A cache copies while preserving authoritative and unique evidence
- Paths: src/src_physics/src_electronics/{co_simulation,src_electronics/co_simulation}/co_sim_runners/{runner_T.m,runner_M_T.m,runner_M_T_PD.m,co_simulation_seed_for_repeat.m}; projects/5t_32ch_loop_dipole_rx/tools/{matlab/TEST_TMD_SEED_OFFSET_v01.m,automation/prepare_v05_tmd_seed_repeats.py,automation/isolate_redundant_cached_stage_a.py}; projects/5t_32ch_loop_dipole_rx/docs/40_validation/C3_V05_TRUE_MULTISTART_AND_CLEANUP_v01.md; projects/5t_32ch_loop_dipole_rx/status.json.
- Interfaces: Set MARIE_TMD_SEED_OFFSET to a finite nonnegative integer to add it to counter_repeat; leave it unset for exact legacy behavior. Run isolate_redundant_cached_stage_a.py without --execute for dry-run and with --execute only for its fixed hash-checked allowlist.
- Compatibility: Unset or zero seed offset reproduces rng(counter_repeat); both duplicate electronics trees remain synchronized; cleanup is recoverable and retains authoritative Stage-A plus unique scientific evidence.
- Evidence: TEST_TMD_SEED_OFFSET_v01 PASS; offset 0/1000/2000 SP_p=-13.381608807/-13.295444344/-13.137753754 dB; cleanup receipt verifies 16 files and 2362856298 bytes with post-move SHA-256 equality.

### 2026-09-02 — Opt-in finite-Q-aware Rx TMD and post-TMD-safe Stage-C continuation

- Summary: Added an opt-in finite-Q-aware Rx objective, enabled its optimization for a single physical port, and made Stage-C continuation require a calibrated post-TMD MREDM checkpoint
- Paths: src/src_physics/src_electronics/co_simulation/co_simulation.m; src/src_physics/src_electronics/co_simulation/co_sim_cost_functions/matching_and_tuning_and_preamplifierdecoupling_loss_aware.m; src/src_physics/src_electronics/co_simulation/co_sim_runners/runner_M_T_PD_loss_aware.m; src/src_physics/src_electronics/co_simulation/co_sim_master_files/co_simulation_Rx_optim_loss_aware.m; projects/5t_32ch_loop_dipole_rx/tools/matlab/{DIAG_V05_FINITE_Q_MATCH_v01.m,run_phase2_abc_case.m}; projects/5t_32ch_loop_dipole_rx/docs/40_validation/C3_V05_LOSS_AWARE_STAGEBC_RESULT_v01.md.
- Interfaces: MARIE_RX_TMD_LOSS_AWARE=1 enables the finite-Q-aware Rx objective; MARIE_TMD_DEBUG_RETHROW=1 exposes its first optimizer exception; MARIE_RESUME_AFTER_STAGE_B=1 requires accepted metrics, an identical active-circuit snapshot, and MREDM_postTMD_<CaseTag>.mat.
- Compatibility: All switches default off; ordinary canonical behavior is unchanged. Loss-aware optimization keeps declared JSON hard bounds. Pre-TMD raw YPn cannot be used as a Stage-C resume checkpoint.
- Evidence: v05 finite-Q decomposition changed ideal 50-j0 ohm to 35.283-j11.087 ohm under the legacy solution; corrected loss-aware Stage B reproducibly achieved SP_p=-109.496484230 dB; continuous FixedCircuit Stage C completed with network consistency 0 and finite SNR.

### 2026-09-03 — Common-grid M0 Loop-versus-dipole geometric-ROI SNR comparison

- Summary: Added deterministic same-grid Stage-C SNR comparison for the accepted M0 single Loop and loss-aware v05 dipole, with explicit geometric ROI labels and a fail-closed UISNR compatibility statement
- Paths: projects/5t_32ch_loop_dipole_rx/tools/matlab/POST_COMPARE_M0_LOOP_V05_v01.m; projects/5t_32ch_loop_dipole_rx/runs/_bootstrap/m0_loop_v05_comparison_20260903T000000+0800/{metrics.json,central_slice_comparison.png}; projects/5t_32ch_loop_dipole_rx/docs/40_validation/M0_LOOP_V05_SNR_COMPARISON_v01.md; projects/5t_32ch_loop_dipole_rx/status.json.
- Interfaces: Run POST_COMPARE_M0_LOOP_V05_v01 from repository-root MATLAB after startup; it defines deep radius <=40 mm, middle 40-105 mm, and a 15 mm outer geometric shell on the common RHBM.idxS support.
- Compatibility: The metrics apply only to the unlabeled Sphere240 M0 phantom and must not be called anatomical cortex/deep-brain results. UISNR remains false because the available Sphere200 basis is incompatible.
- Evidence: Both Stage-C arrays are finite 121^3 grids at 212.88739259 MHz; v05/Loop median-SNR ratios are 0.669 deep, 0.835 middle, 0.888 surface shell, and 0.836 whole; MATLAB checkcode is zero.

### 2026-09-03 — Project review navigation and gated WP3-WP6 implementation roadmap

- Summary: Integrated the post-single-channel execution plan into the authoritative simulation guidance and added an evidence-oriented directory review guide that distinguishes live directories from the target governance tree
- Paths: projects/5t_32ch_loop_dipole_rx/{README.md,status.json}; projects/5t_32ch_loop_dipole_rx/docs/{README.md,00_governance/PROJECT_DIRECTORY_AND_REVIEW_GUIDE_v01.md,00_governance/5T_Loop偶极子项目_文件组织与资产治理规则.md,30_simulation/CORE_MARIE_SIMULATION_IMPLEMENTATION_PLAN_v01.md,30_simulation/MARIE_Loop偶极子混合头部接收阵列_仿真与性能评估规划.md}.
- Interfaces: Review starts at PROJECT_DIRECTORY_AND_REVIEW_GUIDE_v01.md then status.json, validation report, exact RunTag metrics/snapshots/MAT/logs; execution follows core-plan section 10 WP3A-WP6 and section 11 current tasks.
- Compatibility: Documentation-only navigation update; no simulation inputs, source, thresholds or results changed. Historical failure evidence remains preserved, while stale status navigation fields were corrected to the accepted loss-aware v05 evidence.
- Evidence: JSON parse passed; headings normalized to sections 9-12; document links and nonempty targets checked; guide records authoritative Loop/v05 RunTags, cleanup receipt, unimplemented target directories and incomplete deliverables.

### 2026-09-03 — WP3 comparison contract and controlled pair-case interface

- Summary: Added a frozen Sphere240 M0 ROI/comparison contract, deterministic P0/P1/P2 pair-case generation, and case-local geometry evidence conventions; recorded the native visualization failure as fail-closed evidence.
- Paths: projects/5t_32ch_loop_dipole_rx/assets/roi/; projects/5t_32ch_loop_dipole_rx/tools/geometry_generation/generate_wp3_pair_cases.py; projects/5t_32ch_loop_dipole_rx/cases/5T_1H_Sphere240_2Ch_*; projects/5t_32ch_loop_dipole_rx/docs/40_validation/WP3A_WP3B_GEOMETRY_GATE_v01.md.
- Interfaces: python projects/5t_32ch_loop_dipole_rx/tools/geometry_generation/generate_wp3_pair_cases.py --project-root projects/5t_32ch_loop_dipole_rx [--pair P0|P1|P2]; MATLAB FREEZE_M0_COMPARISON_CONTRACT_v01.
- Compatibility: Additive. Existing single-channel assets and accepted results are unchanged. P2 remains fail-closed until native visualization succeeds..
- Evidence: WP3A ROI masks partition 904089 support voxels; P0 and P1 geometry_metrics.json passed; P2 N_wie/port/clearance checks passed but visualize_geometry terminated without exception for independent 90- and 80-degree cases..

### 2026-09-03 — High-resolution body geometry visualization surface reduction

- Summary: Changed visualize_geometry to remove strictly interior body voxels before the 3-D boundary triangulation, preventing uncaught Qhull process termination on Sphere240/2 mm while preserving solver geometry.
- Paths: src/src_visualizer/visualize_geometry.m; docs/guides/MARIE_可视化脚本使用指南.md; docs/architecture/MARIE_src源码模块与算法详解.md; projects/5t_32ch_loop_dipole_rx/docs/40_validation/WP3A_WP3B_GEOMETRY_GATE_v01.md.
- Interfaces: visualize_geometry(MREDM); new explicit error MARIE:visualize_geometry:InsufficientBodySurface.
- Compatibility: Visualization-only behavioral change. Electromagnetic grids, WIE/SIE geometry, fields, and numerical solutions are unchanged. Existing callers keep the same function signature..
- Evidence: The pre-fix isolated boundary(P,1) test terminated after B1 with 904089 input points and no MATLAB exception. Post-fix P0, P1, canonical P2-90, and diagnostic P2-80 all emitted PHASE1_GEOMETRY_PASS and geometry_metrics.json..

### 2026-09-03 — Multi-channel fixed-circuit Stage C post-TMD resume contract

- Summary: Corrected the project A/B/C runner so multi-channel Stage C freezes the accepted circuit and reuses the exact accepted post-TMD calibrated physical-channel currents, network, and finite-Q losses instead of incorrectly recalibrating physical YP against temporary-port Jcb.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/matlab/run_phase2_abc_case.m; projects/5t_32ch_loop_dipole_rx/tools/matlab/POST_WP3_PAIR_NOISE_SUBSPACE_v01.m; docs/operations/MARIE_Codex远程开发具体实施指南.md; docs/guides/MARIE_Runner算法与使用指南.md.
- Interfaces: MARIE_RESUME_AFTER_STAGE_B=1 requires stage_b_metrics.json, active_circuit_after_tmd.json, and MREDM_postTMD_<CaseTag>.mat; Stage C requires finite JcbRx/JcbTx physical-channel columns and exact SP_s continuity.
- Compatibility: The Stage A/B interface is unchanged. Single-channel accepted evidence remains valid. Multi-channel Stage C now fails closed on missing calibrated currents or network drift and no longer enters the dimensionally invalid matching-only recalibration..
- Evidence: Initial P1 Stage C failed at Jcb(2712421x7)*M_cal(2x2). Post-TMD inspection showed JcbRx 2712421x2 and physical YP/SP 2x2. After correction P1 and P2 completed Stage C with network_consistency_rel=0 and finite SNR..

### 2026-09-03 — WP3 P0 multistart recovery and three-topology comparison

- Summary: Added isolated cached-Stage-A P0 multistart preparation and a common-contract P0/P1/P2 total-noise, whitened-mode, and ROI-SNR comparison; selected P2-90 for WP3C.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/automation/prepare_p0_tmd_seed_repeats.py; projects/5t_32ch_loop_dipole_rx/tools/matlab/POST_WP3_P0P1P2_NOISE_SUBSPACE_v02.m; projects/5t_32ch_loop_dipole_rx/runs/_bootstrap/wp3_p0p1p2_noise_subspace_20260903T220000+0800/; projects/5t_32ch_loop_dipole_rx/docs/40_validation/WP3_PAIR_ABC_AND_NOISE_SUBSPACE_RESULT_v01.md; projects/5t_32ch_loop_dipole_rx/status.json.
- Interfaces: prepare_p0_tmd_seed_repeats.py --project PATH --stamp RunTag --offsets N... creates isolated work copies bound to a hash-identical authoritative YPn; POST_WP3_P0P1P2_NOISE_SUBSPACE_v02 consumes the accepted P0 offset-2000 and canonical P1/P2 final MAT files.
- Compatibility: Additive project-local tooling. Canonical input JSON files and raw YPn are unchanged; failed seed evidence remains preserved. Results apply only to the frozen Sphere240 M0 comparison contract.
- Evidence: P0 offsets 1000/2000 passed at worst SPp/S21 = -39.44/-35.46 and -44.46/-38.19 dB, while 3000 failed at -14.32/-11.32 dB. Accepted P0 Stage C had network consistency 0. P2/P0 median SNR ratios were 1.054 deep, 1.141 middle, 1.031 surface, and 1.123 support; max noise correlation was 0.0595 versus P0 0.1621.

### 2026-09-03 — WP3C controlled four-channel geometry interface

- Summary: Added deterministic same-coverage four-channel 4Loop and P2-derived 2Loop+2Dipole case generation, with case-local manifests, mappings, geometry runners, hashes, and native geometry evidence.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/geometry_generation/generate_wp3c_four_channel_cases.py; projects/5t_32ch_loop_dipole_rx/cases/5T_1H_Sphere240_4Ch_{4LoopRx,2Loop2DipoleRx_P2}_M0_ICv11_v01/; projects/5t_32ch_loop_dipole_rx/docs/40_validation/WP3C_FOUR_CHANNEL_GEOMETRY_GATE_v01.md; projects/5t_32ch_loop_dipole_rx/status.json.
- Interfaces: python projects/5t_32ch_loop_dipole_rx/tools/geometry_generation/generate_wp3c_four_channel_cases.py --project-root PATH [--topology L2_4Loop|L2_2Loop2Dipole_P2].
- Compatibility: Additive project-local cases. Both use four physical channels and azimuths 0/90/180/270 degrees; the mixed case replaces the 90/270-degree Loops with v05 dipoles. Geometry changes invalidate all WP3B YPn.
- Evidence: Both cases passed load_inputs, geo_assembly, native visualization, exact WIE segment/port checks, and 15 mm body clearance under RunTag 20260903T230000+0800_geometry_only. No Stage A/B/C was executed.

### 2026-09-03 — WP3C isolated four-channel Stage-A preparation

- Summary: Added hash-gated isolated Stage-A preparation for both accepted WP3C four-channel geometries and recorded their independent raw-network evidence.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/automation/prepare_wp3c_stage_a.py; projects/5t_32ch_loop_dipole_rx/runs/_bootstrap/wp3c_stage_a_manifest_20260903T234000+0800.json; projects/5t_32ch_loop_dipole_rx/docs/40_validation/WP3C_FOUR_CHANNEL_GEOMETRY_GATE_v01.md; projects/5t_32ch_loop_dipole_rx/status.json.
- Interfaces: python projects/5t_32ch_loop_dipole_rx/tools/automation/prepare_wp3c_stage_a.py --repo PATH --stamp RunTag [--workers 2..32] requires a frozen passed geometry manifest and exact canonical MSH/JSON hashes.
- Compatibility: Additive project-local preparation. Each new geometry uses its own YPn and pre-TMD checkpoint; no WP3B cache is reused. Stage B/C remain separate gated continuations.
- Evidence: RunTag 20260903T234000+0800_wp3c_joint_stage_a produced finite reciprocal 16x16 4Loop and 14x14 mixed YPn with reciprocity_rel=0. Assembly/solve times were 717.73/354.91 s and 711.87/558.62 s respectively; all GMRES columns converged.

### 2026-09-04 — WP3C cached-Stage-A finite-Q multistart interface

- Summary: Added isolated multistart preparation for both WP3C raw networks and selected accepted offset-1000 circuits without running Stage C.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/automation/prepare_wp3c_tmd_seed_repeats.py; projects/5t_32ch_loop_dipole_rx/runs/_bootstrap/wp3c_tmd_seed_repeats_20260904T003000+0800.json; projects/5t_32ch_loop_dipole_rx/docs/40_validation/WP3C_FOUR_CHANNEL_GEOMETRY_GATE_v01.md; projects/5t_32ch_loop_dipole_rx/status.json.
- Interfaces: python projects/5t_32ch_loop_dipole_rx/tools/automation/prepare_wp3c_tmd_seed_repeats.py --project PATH --stamp RunTag [--offsets N...]; each output RunTag contains private cached Stage-A artifacts and a private active circuit JSON.
- Compatibility: Additive project-local interface. Canonical cases and authoritative Stage-A runs remain unchanged. Rejected Stage-B runs cannot enter Stage C.
- Evidence: 4Loop offsets 0/1000/2000 all passed, with offset 1000 at worst SPp/coupling -59.94/-55.77 dB. Mixed offsets 0 and 2000 failed matching; offset 1000 passed at -16.53/-34.38 dB. All reciprocity errors were below 4.9e-16.

### 2026-09-04 — WP3C Stage-C closure and full-coil fast-track decision

- Summary: Added the accepted four-channel total-noise/SNR comparison and closed further sparse-array optimization; redirected active work to complete formal-helmet 32-channel geometry because 90-degree four-channel spacing makes low coupling unrepresentative.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/matlab/POST_WP3C_4CH_COMPARE_v01.m; projects/5t_32ch_loop_dipole_rx/runs/_bootstrap/wp3c_4ch_compare_20260904T013000+0800/; projects/5t_32ch_loop_dipole_rx/docs/40_validation/WP3C_FOUR_CHANNEL_GEOMETRY_GATE_v01.md; projects/5t_32ch_loop_dipole_rx/status.json.
- Interfaces: POST_WP3C_4CH_COMPARE_v01 consumes only the two accepted offset-1000 Stage-C MAT files and the frozen M0 ROI; it reports total-noise eigenspectra, correlations, whitened modes, ROI SNR ratios, and the mixed-case conditional dipole block.
- Compatibility: No solver or canonical input changed. WP3C remains evidence for pipeline and direction only, not formal full-coil ranking. Full 32-channel ranking still requires the formal helmet, compatible Head5T, ROI, and UISNR contract.
- Evidence: Both Stage C networks had exact continuity and finite SNR. Mixed/4Loop median SNR was 1.012 deep, 0.910 middle, 0.906 surface, and 0.906 support; max noise correlation rose from 0.0200 to 0.1117 and noise condition from 1.483 to 12.229.

### 2026-09-04 — Full-geometry-first planning and gate interface

- Summary: Unified project planning around immediate complete formal-helmet geometry modeling, closed sparse four-channel expansion, and removed the sphere eight-port superarray as a mandatory intermediate stage.
- Paths: projects/5t_32ch_loop_dipole_rx/docs/{00_governance/LINUX_CODEX_5T_32CH_LOOP_DIPOLE_PROJECT_START.md,00_governance/5T_Loop偶极子项目_文件组织与资产治理规则.md,20_design/5T_32通道基准仅接收Loop阵列_文献调研与建模规划.md,30_simulation/CORE_MARIE_SIMULATION_IMPLEMENTATION_PLAN_v01.md,30_simulation/MARIE_Loop偶极子混合头部接收阵列_仿真与性能评估规划.md,50_ai_optimization/高场MRI头部Loop-偶极子混合接收阵列_难点与AI优化任务报告.md}.
- Interfaces: Generate and statically validate complete Seed-P 9+9+9+5 A0 geometry first, then fixed-32-channel R2/R4 and subsequently R6/R8 geometry candidates; run local fragments only when needed for diagnosis or calibration. Head5T, anatomical ROI, and compatible UISNR remain mandatory before formal 32-channel Stage A/B/C performance ranking.
- Compatibility: Planning and governance only. Existing inputs, solver outputs, WP3C evidence, numerical thresholds, and high-cost authorization requirements are unchanged.
- Evidence: The authoritative plans now identify complete geometry as the next executable work, label WP3C closed, state that sparse four-channel coupling is nonrepresentative, and consistently separate geometry permission from formal-solve permission.

### 2026-09-04 — Literature-constrained formal helmet asset interface

- Summary: Added a deterministic project-owned generator and versioned nonconductive formal-helmet seed using the frozen 190×222×231 mm inner envelope and a lower elliptical-cylinder/upper half-ellipsoid surface.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/geometry_generation/generate_formal_helmet_v01.py; projects/5t_32ch_loop_dipole_rx/assets/formers/FormalHelmet_LR190_AP222_HF231_EllipticDome_v01/; projects/5t_32ch_loop_dipole_rx/docs/40_validation/FORMAL_HELMET_SEED_V01.md; projects/5t_32ch_loop_dipole_rx/status.json.
- Interfaces: python projects/5t_32ch_loop_dipole_rx/tools/geometry_generation/generate_formal_helmet_v01.py --project-root projects/5t_32ch_loop_dipole_rx emits parameter JSON, OBJ, ASCII STL, preview PNG and hash-bearing validation JSON.
- Compatibility: Additive project-local geometry asset. It is not a MARIE CoilFile/WireFile, does not supply a Head5T body or ROI, and does not authorize Stage A/B/C. Subsequent loop geometries must reference the exact asset tag and hash.
- Evidence: Deterministic static validation measured LR/AP/HF 0.190/0.222/0.231 m on a 17281-vertex, 34416-triangle open-inferior mesh; finite, nondegenerate, envelope, row-centre and 9+9+9+5 partition checks passed.

### 2026-09-04 — Complete Seed-P 32-loop WIE geometry interface

- Summary: Added deterministic generation of the complete 9+9+9+5 Seed-P WIE array, including matched circuit JSON, channel/element maps, equal-arc placement, adjacency/overlap tables, conservative insulated-crossover layers, collision checks and three-view preview.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/geometry_generation/generate_seed_p_32loop_v01.py; projects/5t_32ch_loop_dipole_rx/cases/5T_1H_Head5T_32Ch_LoopRx_A0_9x9x9x5_ICv11_v01/; projects/5t_32ch_loop_dipole_rx/docs/40_validation/SEED_P_32LOOP_WIE_GEOMETRY_V01.md; projects/5t_32ch_loop_dipole_rx/status.json.
- Interfaces: python projects/5t_32ch_loop_dipole_rx/tools/geometry_generation/generate_seed_p_32loop_v01.py --project-root projects/5t_32ch_loop_dipole_rx. The case deliberately has no formal input JSON until a hash-bound valid Head5T body exists.
- Compatibility: Additive project-local candidate. Four global radial crossover layers are sufficient for static collision clearance but are not accepted for formal EM ranking; a new version with localized insulated overpasses is required. No solver, body, accepted case, or numerical threshold changed.
- Evidence: Static checks passed for 32 closed components, 4312 nodes/segments, 32 physical ports, 128 lumped locations, 83 adjacency pairs, 2.325-2.500 mm segment lengths and 1.179 mm minimum adjacent-conductor centerline distance. The initial 1.5 mm layer attempt failed at 0.299 mm and was not accepted.

### 2026-09-04 — Seed-P localized crossover v02 and Head5T fail-closed gate

- Summary: Replaced the v01 whole-loop radial layers with deterministic local insulated crossover bridges and a three-phase axial edge dither; added an explicit fail-closed native-geometry gate when no qualified Head5T asset exists.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/geometry_generation/generate_seed_p_32loop_v02_local_bridges.py; projects/5t_32ch_loop_dipole_rx/cases/5T_1H_Head5T_32Ch_LoopRx_A0_9x9x9x5_ICv11_v02/; projects/5t_32ch_loop_dipole_rx/docs/40_validation/SEED_P_32LOOP_LOCAL_BRIDGE_V02.md; projects/5t_32ch_loop_dipole_rx/status.json.
- Interfaces: python projects/5t_32ch_loop_dipole_rx/tools/geometry_generation/generate_seed_p_32loop_v02_local_bridges.py --project-root projects/5t_32ch_loop_dipole_rx emits v02 MSH/circuit/maps/collision evidence. It must not emit a formal input or run MATLAB until a body with explicit labels, 212.9 MHz properties, column idxS, anatomical ROIs and frozen helmet registration is available.
- Compatibility: Additive new geometry version; v01 remains preserved. Existing Hugo 3 T and sphere assets are explicitly disallowed as substitutes for formal Head5T. No Stage A/B/C authorization is implied.
- Evidence: v02 static checks passed with 32 closed loops, 10474 nodes/segments, 128 lumped locations, 166 local bridge records, 3 mm common base standoff, 18.5 mm maximum local radial position, 1.016 mm minimum adjacent-conductor distance and <=1.5 mm segment length. Native MARIE geometry remains blocked because the server has no qualified Head5T.

### 2026-09-08 — Fixed-32-channel graded Stage-B network gate

- Summary: Preserved the strict Grade-A formal-baseline gate and added a literature-supported Grade-B gate that permits only bounded, adjacency-listed exceptions for exploratory fixed-circuit Stage C; Grade B can never confer formal or research-validated baseline status.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/matlab/run_phase2_abc_case.m; projects/5t_32ch_loop_dipole_rx/docs/00_governance/STAGE_B_GRADED_NETWORK_GATE_POLICY_v01.md; marie-mri-coil-simulation skills/{SKILL.md,references/rx-array-validation.md,references/workspace-docs/MARIE_5T_32CH_STAGE_B分级网络门禁_v01.md}.
- Interfaces: Stage-B metrics now expose grade_a_pass, eligible_for_exploratory_stage_c, channels_better_than_minus15_db, coupling_exception_pair_count, coupling_exceptions_all_adjacent, and gate_policy; Stage C emits stage_c_class and research_validated=false.
- Compatibility: Strict legacy accepted results resume as Grade A. Historical rejected metrics remain immutable. Grade B is additive and requires at least 28/32 ports below -15 dB, all others below -12 dB, worst coupling below -10.5 dB, and at most four adjacency-listed exception pairs.
- Evidence: MATLAB checkcode passed; v16 retrospective audit found only 16/32 ports below -15 dB and 11 coupling exception pairs, including one non-adjacent pair, so it remains ineligible for both Stage-C classes.

### 2026-09-08 — Explicit temporary Stage-C override interface

- Summary: Added a fail-closed manual override path for diagnostic Stage C when both Grade A and Grade B fail; the original rejected evidence remains unchanged and the output can never become a validated baseline.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/matlab/run_phase2_abc_case.m; projects/5t_32ch_loop_dipole_rx/tools/automation/prepare_v05_v16_temporary_stage_c.py; projects/5t_32ch_loop_dipole_rx/docs/00_governance/STAGE_B_GRADED_NETWORK_GATE_POLICY_v01.md; marie-mri-coil-simulation skills/SKILL.md.
- Interfaces: MARIE_ALLOW_TEMPORARY_STAGE_C_OVERRIDE=1 is accepted only with stage_b_metrics.manual_temporary_override=true; Stage C emits stage_c_class=temporary_user_override, diagnostic_rejected_circuit=true, manual_temporary_override=true, and research_validated=false.
- Compatibility: Default Grade-A/Grade-B behavior remains fail-closed. The override requires exact user authorization and an isolated continuation RunTag; it does not mutate or promote the rejected source Stage B.
- Evidence: v05/v16 continuation 20260908T233500+0800_stage_c_temporary_override_v01 completed with network_consistency_rel=0, finite SNR, field_noise_s=280.630921, and a 7.383 GB final MAT.

### 2026-09-08 — Acquisition-specific and measured-SNR normalization contract

- Summary: Added a source-backed workflow for converting MARIE solution.snr_field.SNR into acquisition-specific predictions and for calibrating and validating against measured MRI SNR without per-ROI overfitting.
- Paths: marie-mri-coil-simulation skills/SKILL.md; references/snr-measurement-normalization.md; references/rx-array-validation.md; references/document-index.md; references/architecture-interfaces.md.
- Interfaces: Tasks involving absolute SNR, scanner comparison, bandwidth or sequence scaling, calibration, or SNR error maps must read references/snr-measurement-normalization.md and record the required provenance tuple.
- Compatibility: Documentation-only additive contract; no solver formula, source API, input, threshold, result MAT, or validated asset changed.
- Evidence: Live em_SNR.m and em_constants.m inspection confirmed res^3*omega*M0/sqrt(4*k_B*T0), the full Rx noise sum, T0=310 K, and the fixed equilibrium magnetization model; Markdown links and formulas are validated below.

### 2026-09-08 — WP6 fixed-32-channel Loop-to-dipole geometry exploration interface

- Summary: Added deterministic nested R2/R4/R6/R8 replacement generation, independent static auditing, and a MARIE-native geometry runner; geometry exploration may precede accepted A0 but cannot rank performance.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/geometry_generation/generate_32ch_loop_dipole_replacement_exploration_v01.py, projects/5t_32ch_loop_dipole_rx/tools/validation/validate_32ch_loop_dipole_replacement_v01.py, projects/5t_32ch_loop_dipole_rx/tools/matlab/run_wp6_replacement_geometry_case_v01.m, projects/5t_32ch_loop_dipole_rx/cases/5T_1H_Head5T_32Ch_LoopDipoleRx_R{2,4,6,8}_A0v05_C3v05_ICv11_v03/, projects/5t_32ch_loop_dipole_rx/docs/40_validation/WP6_32CH_LOOP_DIPOLE_REPLACEMENT_GEOMETRY_EXPLORATION_v01.md.
- Interfaces: python generate_32ch_loop_dipole_replacement_exploration_v03.py --project-root PATH [--k 2 4 6 8]; python validate_32ch_loop_dipole_replacement_v01.py CASE...; MATLAB run_wp6_replacement_geometry_case_v01(caseTag,expectedWie,expectedElements,expectedDipoles).
- Compatibility: Additive project-local interface. A0-v05 remains an engineering candidate, not an accepted baseline. Each changed geometry invalidates prior YPn and needs independent Stage A. No Stage A/B/C or performance ranking was authorized..
- Evidence: All four v03 candidates passed independent topology/port/mesh audits and native load_inputs + geo_assembly + four-view visualization under RunTag 20260908T_native_geometry_v04; physical ports=32; WIE supports=10530/10942/11549/11836..

### 2026-09-08 — Self-decoupled Loop candidate and multifrequency TMD evidence contract

- Summary: Defined local self-decoupled Loop use for dense Loop-Dipole receive arrays and required multifrequency transmission-zero evidence before full-array loss-aware TMD; retained overlap and preamplifier decoupling as complementary methods.
- Paths: projects/5t_32ch_loop_dipole_rx/docs/20_design/5T_32CH_LOOP_DIPOLE_SELF_DECOUPLING_AND_TMD_RESEARCH_v01.md, projects/5t_32ch_loop_dipole_rx/docs/30_simulation/CORE_MARIE_SIMULATION_IMPLEMENTATION_PLAN_v01.md, projects/5t_32ch_loop_dipole_rx/status.json, marie-mri-coil-simulation skills/SKILL.md.
- Interfaces: Planning contract: B0 mechanism sweep; B1 mode/arm resonance alignment; B2 matching; B3 neighbor-class minimax; B4 full-array finite-Q closure; FixedCircuit Stage C. No new callable runner is implemented yet..
- Compatibility: Documentation and validation-contract update only. Existing single-frequency TMD remains unchanged. No source, input, threshold, YPn, circuit JSON, or simulation result was modified..
- Evidence: Local Yan 2018 main/supplement/peer-review analysis; live loss-aware cost and runner inspection; primary UHF 32Rx evidence from Tavaf et al. 2021 and complementary SCC/sleeve array studies..

### 2026-09-08 — Head5T UISNR two-level calculation and operation contract

- Summary: Defined a reusable Head5T UISNR program with U1 surface-support-constrained optimal SNR and U2 converged dipole-shell UISNR approximation, plus compatibility, resource-probe, checkpoint, numerical-audit, and high-cost authorization gates.
- Paths: projects/5t_32ch_loop_dipole_rx/docs/30_simulation/HEAD5T_UISNR_CALCULATION_AND_OPERATION_PLAN_v01.md, projects/5t_32ch_loop_dipole_rx/docs/30_simulation/CORE_MARIE_SIMULATION_IMPLEMENTATION_PLAN_v01.md, projects/5t_32ch_loop_dipole_rx/status.json, marie-mri-coil-simulation skills/SKILL.md.
- Interfaces: Planned case-local U0-U5 BASIS workflow: static contract; native geometry; resource probe; surface-support convergence; dipole-shell convergence; frozen-basis finite-array comparison. No callable project runner has been implemented yet..
- Compatibility: Documentation and future evidence-layout contract only. Existing Sphere200 BASIS is explicitly incompatible. No source, body, support, BASIS, solver output, or threshold changed; no high-cost run was authorized..
- Evidence: Live BASIS_runner, IncidentField_Basis, geo_assembly, load_inputs defaults and UISNR implementation reviewed; project status confirms UISNR absent; existing Sphere200 basis is 5.9GB; approximately 178GB disk free at planning time..

### 2026-09-08 — Head5T UISNR U1 engineering-probe execution interface

- Summary: Implemented and launched the first case-local surface-supported UISNR engineering probe using the anonymous-material 2 mm Hugo surrogate and a closed coarse helmet support that encloses the body and all R2/R4/R6/R8 candidates.
- Paths: projects/5t_32ch_loop_dipole_rx/tools/geometry_generation/generate_head5t_uisnr_support_v01.py; projects/5t_32ch_loop_dipole_rx/tools/matlab/RUN_HEAD5T_UISNR_{GEOMETRY,BASIS}_ENGINEERING_v01.m; projects/5t_32ch_loop_dipole_rx/cases/5T_1H_HugoAnon5T2mm_PWC_HelmetSupport_UISNR_Engineering_v01/; projects/5t_32ch_loop_dipole_rx/runs/5T_1H_HugoAnon5T2mm_PWC_HelmetSupport_UISNR_Engineering_v01/.
- Interfaces: Run the Python generator from repository root; set `MARIE_RUN_DIR` to an existing case-local directory before invoking either MATLAB runner through `matlab -batch "run('...m')"`. The BASIS runner writes `status.json`, diary, failure evidence, an incident-basis metadata checkpoint, final metrics, and the case-local BASIS artifact.
- Compatibility: Additive project-local implementation; no MARIE source or accepted input was changed. The loader presently requires a pre-existing BasisFile, so a zero-byte placeholder is used only before completion. The plotting runner adds an empty `port` field to an M-only visualization copy because geo_shield and visualize_geometry disagree; numerical M remains unchanged.
- Evidence: Static containment passed for 629290 active body voxels and 127229 nodes from 12 R2/R4/R6/R8 candidate meshes. Native load_inputs + geo_assembly + visualize_geometry passed at 212.9 MHz with 432 triangles and 648 RWGs. The 2-worker BASIS run entered vie_assembly under RunTag 20260908T_uisnr_basis_engineering_v01; status remains engineering-surrogate and not research-validated until completion and convergence audits.

### 2026-09-09 — Mixed-channel loss-aware TMD refinement and R2 ICv12 circuit domain

- Summary: Replaced equal contiguous per-port variable blocks with detailed-mask-derived channel variable IDs for mixed Loop/Dipole arrays, and added a versioned R2 ICv12 circuit-only candidate with evidence-based expanded hard bounds.
- Paths: src/src_physics/src_electronics/co_simulation/co_sim_runners/{co_simulation_channel_variable_ids.m,runner_M_T_PD_loss_aware.m}; projects/5t_32ch_loop_dipole_rx/{tools/matlab/TEST_TMD_MIXED_CHANNEL_VARIABLE_IDS_v01.m,tools/automation/create_r2_icv12_parameter_domain.py,cases/5T_1H_Head5T_32Ch_LoopDipoleRx_R2_A0v05_C3v05_ICv12_v03,docs/40_validation/R2_ICV12_MIXED_CHANNEL_TMD_DOMAIN_v01.md}; marie-mri-coil-simulation skills/SKILL.md.
- Interfaces: co_simulation_channel_variable_ids maps detailed matching/fixed/tuning/mutual masks to per-channel unique optimizer IDs; MARIE_RX_TMD_BLOCK_COORDINATE and focused refinement now support unequal channel variable counts. Run create_r2_icv12_parameter_domain.py to reproduce the circuit-only ICv12 case..
- Compatibility: Default loss-aware TMD behavior is unchanged unless block-coordinate refinement is enabled. Equal-size arrays remain supported. ICv11 assets and results remain immutable; ICv12 changes only seed values and bounds, so hash-identical geometry permits reuse of the parent raw Stage-A YPn..
- Evidence: MATLAB TEST_TMD_MIXED_CHANNEL_VARIABLE_IDS_v01 PASS; checkcode clean for helper and runner; ICv12 static validation passed for 32 ports, 126 elements, all seeds within bounds, and identical parent/new MSH SHA-256 5bf94aabf5206085a2fc8780d35153c7331aea03e2b955c70aad57704196eef1..
# Project-scoped Stage-B gate override (2026-09-11)

The `5t_32ch_loop_dipole_rx` Phase-2 runner defines its current loss-aware Rx
TMD objective and acceptance gate together: every `SP_p < -12 dB` and every
off-diagonal `SP_s < -10 dB`.  It exports
`MARIE_RX_TMD_TARGET_RETURN_DB=-12` and
`MARIE_RX_TMD_TARGET_COUPLING_DB=-10`; `co_simulation.m` validates and consumes
these optional negative-dB overrides while retaining the generic MARIE defaults
of `-15/-12 dB` for other projects.  Historical RunTags retain their recorded
gate policy and must not be relabelled.

### 2026-09-14 — SSD/HDD tiered storage and capacity gate

- Summary: Defined SSD control-plane and HDD data-plane ownership, stable symlink paths, storage provenance, capacity reserves, migration verification, checkpoint and retention rules for MARIE projects and UISNR work.
- Paths: AGENTS.md, MARIE_Agent_Harness.md, marie-mri-coil-simulation skills/{SKILL.md,references/storage-layout.md,references/document-index.md,references/architecture-interfaces.md,references/workspace-docs/{AGENTS.md,MARIE_Agent_Harness.md},scripts/refresh_bundle_manifest.py}.
- Interfaces: Use /mnt/data/<user>/marie/projects/<ProjectID> for large data; record storage logical_path/realpath/filesystem/tier/size/hash/link_type; require writable mount and 2.5x output headroom before high-cost runs..
- Compatibility: Documentation-only additive contract. Existing paths and results are not moved. Future migration uses copy-checksum-symlink-regression and requires separate deletion approval..
- Evidence: server_guide.pdf pages 8-10 reviewed; live df/findmnt showed system SSD 275G free and /mnt/data 6.9T free but currently ro with no /mnt/data/<user>; workspace/snapshot SHA-256 pairs match; storage-layout is tracked by bundle-manifest; source and installed skill validation plus recursive hash equality passed after deployment.

### 2026-09-24 — Reusable UISNR contracts templates and regression suite

- Summary: Added pointwise ROI semantics, constrained-versus-ultimate result classes, stable Phi pseudoinverse policy, corrected physical ICP conjugation, streaming/non-overwrite guidance, convergence/Hodge diagnostics, generic MATLAB templates, and synthetic regression tests.
- Paths: docs/validation/MARIE_UISNR工程契约与回归测试_v01.md; marie-mri-coil-simulation skills/{SKILL.md,references/uisnr-*.md,references/workspace-docs/MARIE_UISNR工程契约与回归测试_v01.md,assets/matlab-scripts/uisnr,tests/uisnr,scripts/refresh_bundle_manifest.py}.
- Interfaces: MATLAB POST_UISNR_FINAL_MAP_TEMPLATE, EXTRACT_ICP_TARGET_TEMPLATE, RUN_UISNR_BASIS_STREAMING_TEMPLATE, VALIDATE_UISNR_CONTRACT_TEMPLATE, POST_UISNR_CONVERGENCE_TEMPLATE, COMPARE_ARRAY_TO_UISNR_TEMPLATE, PLOT_COMPLEX_CURRENT_DIAGNOSTICS_TEMPLATE; test entry RUN_ALL_UISNR_SKILL_TESTS(skillRoot)..
- Compatibility: Additive skill/workspace contract; no MARIE solver, project input, existing result, ROI, network threshold, or research status changed. Project-specific partitions and gates remain case-local..
- Evidence: MATLAB R2025b checkcode reported 0 issues; five synthetic tests passed for quadratic-form/basis invariance, streaming parity and overwrite refusal, ICP global-phase covariance, idxS ordering, and headless complex-current figures..
