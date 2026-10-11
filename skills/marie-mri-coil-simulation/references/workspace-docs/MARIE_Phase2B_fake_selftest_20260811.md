# MARIE Phase 2B fake-runner self-test

Date: 2026-08-11

## Scope

This test used a temporary directory and a SHA-256 allowlisted fake executable stored below `_agent_tests/bin`. It did not invoke MATLAB, read a command from `agent-case.json`, change scientific `status.json`, or enable production submission.

## Implemented primitives

- atomic JSON replacement with file and directory fsync;
- append-only `events.jsonl` entries with monotonic revision;
- validated state transitions;
- lifecycle case flock;
- canonical active-JSON path flock, including symlink alias collision;
- exclusive before-write backup in the temporary fixture;
- separate process and wrapper exit-code files;
- detached tmux execution in a temporary fixture.

## Executed tests

The first run failed because the temporary active-JSON lock parent did not exist. The missing directory creation was corrected and the complete suite was rerun.

Final passing cases: exit 0, exit 42, SIGTERM, forbidden system executable, same-case lock conflict, canonical JSON alias lock conflict, detached tmux completion, event revision ordering, approval single-use consumption, `startup_unknown`, and orphan recovery.

Final production boundary checks:

- `launch.sh ... --check`: RC 0;
- `launch.sh ...` without `--check`: RC 11;
- no MATLAB/TMD/MRGF executable process observed;
- no new persistent tmux session created; the pre-existing `marie-codex` session remained.

## Not yet complete

Production worker integration, launch timeout observation, crash reconciliation under forced power loss, and a real geometry-only tmux run remain disabled and unverified.
