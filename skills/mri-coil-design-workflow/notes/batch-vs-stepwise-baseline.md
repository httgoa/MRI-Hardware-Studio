# Baseline: batch_quiet Batch Modeling vs. Step-by-Step Driving (dipole) 

> Validates the payoff of `driving/batch-execution.md`'s `batch_quiet` mode on a live CST instance (2024, pid recorded in that session).
> Test project: `projects/dipole_batch_test/dipole.cst` (newly created from an empty project, did not touch the user's `dipole_scratch_M0`).
> Date: 2026-07-20. Builder: `scripts/build_dipole.py`.

## Test method
New empty mws → save → **one** `cst_run_python_tool` call: `exec(build_dipole.py)` + `run_dipole_build(de, model3d, project)`.

## Result (batch_quiet)

| Metric | batch_quiet (this run) | Old step-by-step path (reference) |
|---|---|---|
| Modeling MCP round-trips | **1** call to `cst_run_python_tool` | 9 calls to `cst_add_to_history_tool` (+ agent reasoning each time) |
| Modeling wall-clock | **2.79 s** (all 9 blocks + save + self-check) | Step-by-step, including per-block agent reasoning, typically minutes |
| Popups/hangs | **0** (wrapped in `de.quiet_mode_enabled()`) | Any step-by-step step could pop Abort/Retry/Ignore or hit stale COM |
| Geometry self-check | `n_shapes=5`, `shape_check="ok"` | None (required manually inspecting the tree) |
| Solids built | `Dipole1 / FR4_board / polycarbonate_board / foam / plantom` (exactly 5, names match) | Same |

## End-to-end regression (confirms the batch-built model solves and is usable downstream)
- Async solve: `start_solver` → poll, **~30s to complete** (the guard checks `is_solver_running` first).
- Post-solve volume field: `2D/3D Results\H-Field\h-field (f=0.21) [1]` **exists** → ports/monitors/solver blocks are all correct, and produce the `[1]` H-field needed downstream for circuit AC/B1+.
- Circuit tuning → AC combine → B1+ is an **unmodified** existing code path (`recipes/build/dipole-from-scratch.md` stages 2/3), already validated on a structurally identical model, so it was not re-run in this session (to avoid disturbing the user's already-open M0 project + save a long solve).

## Conclusion
- `batch_quiet` achieves the planning goal: compressing 9 rounds of "think → call MCP → read result" into 1 batch execution; quiet mode suppresses popups; modeling completes in 2.79s. The three old problems (getting stuck in thought loops/slower than a human/hangs) are all bypassed during the modeling stage.
- The shape-count self-check (`build_dipole.py._get_number_of_shapes`, via `_execute_vba_code` + `Open For Output` temp-file read-back, without polluting history) works correctly, returning 5=expected.
- **`batch_quiet` is established as the default for the `dipole-from-scratch` modeling stage.** Demo/recording scenarios use `demo_stepwise` (visible block-by-block, `recipes/build/demo-recording-mode.md`).

## Reuse for new topologies
When a new topology has no dedicated builder: assemble an ordered `blocks` list from `building-blocks/vba-knowledge/` → `run_batch(de, model3d, project, blocks, expected_shapes=N)` (same quiet-loop + self-check). See `driving/batch-execution.md`.
