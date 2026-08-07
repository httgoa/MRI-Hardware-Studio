# D1 Regular Dipole Batch Runner

This helper adds an automation layer around the already validated single-case
flow in `scripts/data_prep_dipole_complete_case.py`.

It does not change the single-case engine.  It only plans case order, records
checkpoints, skips validated outputs, emits CST MCP snippets, and runs the
offline final record write.

## Files

- Script: `scripts/run_d1_regular_batch.py`
- Shared progress: `results_data_prep/batch_progress.json`
- Per-case checkpoint: `results_data_prep/<case_matrix_id>/log/batch_state.json`
- Single-case engine: `scripts/data_prep_dipole_complete_case.py`

## Basic Use

Plan anchor rows:

```powershell
python .agents/skills/mri-coil-design-workflow/scripts/run_d1_regular_batch.py --plan --roles anchor
```

Plan a small smoke batch:

```powershell
python .agents/skills/mri-coil-design-workflow/scripts/run_d1_regular_batch.py --plan --roles space_fill --max-cases 3
```

Initialize or refresh progress:

```powershell
python .agents/skills/mri-coil-design-workflow/scripts/run_d1_regular_batch.py --init --roles anchor space_fill
```

Find the next action:

```powershell
python .agents/skills/mri-coil-design-workflow/scripts/run_d1_regular_batch.py --next --roles anchor space_fill
```

Show status:

```powershell
python .agents/skills/mri-coil-design-workflow/scripts/run_d1_regular_batch.py --status --roles anchor space_fill
```

## Live CST Pattern

The runner cannot call CST MCP tools by itself.  Codex still performs live CST
calls, but the runner keeps Codex out of routine decision-making.

For each case:

1. Use `--next` to get the next action.
2. For `build`, create a new blank MWS project through CST MCP first.
3. Emit the live code for that stage:

```powershell
python .agents/skills/mri-coil-design-workflow/scripts/run_d1_regular_batch.py --emit-live-code build --case RD_A01
```

4. Paste the emitted Python into `cst_run_python_tool`.
5. Repeat `--next`.

Live stages are:

- `build`: calls `live_build_case(de, project, model3d, case_id)`.
- `start_solver`: calls `live_start_solver(project, model3d)`.
- `poll_solver`: calls `live_poll_solver(project, model3d)`.
- `export`: calls `live_export_fields_and_sar(de, project, model3d, case_id)`.

After `fields_exported`, run offline finalize:

```powershell
python .agents/skills/mri-coil-design-workflow/scripts/run_d1_regular_batch.py --finalize --case RD_A01
```

`--finalize` calls the existing single-case `write_record(...)`, updates the
global record and manifest, and marks the case `validated` only if SAR HDF5 and
record QA pass.

## Error Handling

If a live stage fails, the emitted code records the case as `needs_codex` and
writes the stage result to:

```text
results_data_prep/<case_matrix_id>/log/batch_<stage>_<timestamp>.json
```

Codex should then inspect that one failed stage, repair the underlying issue,
and continue from the recorded stage.  Other cases do not need to be rolled
back.

Manual mark examples:

```powershell
python .agents/skills/mri-coil-design-workflow/scripts/run_d1_regular_batch.py --mark-failed --case RD_A01 --message "SAR HDF5 all zero"
python .agents/skills/mri-coil-design-workflow/scripts/run_d1_regular_batch.py --mark-stage --case RD_A01 --stage solver_done --mark-status active
```

## Intended Division Of Labor

- Script handles: queue, naming, skip/resume, artifact checks, progress files,
  final record write.
- Codex handles: CST MCP invocation, interpreting failures, patching the
  single-case engine only when a real reusable bug is found.
- User handles: deciding which family/role batch to run next.

For anchor and space-fill regular dipoles, the expected process is parameter
repetition over the same D1 complete-case chain.

## Fractionated Dipole Pilot

FD rows are no longer routed through this regular batch runner.  The first FD
pilot uses the sibling single-case engine:

```powershell
python .agents/skills/mri-coil-design-workflow/scripts/data_prep_fd_dipole_complete_case.py --case FD_A01 --paths
python .agents/skills/mri-coil-design-workflow/scripts/data_prep_fd_dipole_complete_case.py --case FD_A01 --emit-manifest
python .agents/skills/mri-coil-design-workflow/scripts/data_prep_fd_dipole_complete_case.py --case FD_A01 --emit-live-code build
python .agents/skills/mri-coil-design-workflow/scripts/data_prep_fd_dipole_complete_case.py --case FD_A01 --emit-live-code start_solver
python .agents/skills/mri-coil-design-workflow/scripts/data_prep_fd_dipole_complete_case.py --case FD_A01 --emit-live-code poll_solver
python .agents/skills/mri-coil-design-workflow/scripts/data_prep_fd_dipole_complete_case.py --case FD_A01 --emit-live-code export
python .agents/skills/mri-coil-design-workflow/scripts/data_prep_fd_dipole_complete_case.py --case FD_A01 --write-record --electrical-summary results_data_prep/FD_A01/log/electrical_summary.json
```

Only after one FD pilot is complete or has a diagnosed reusable failure should a
proper FD batch runner be added.
