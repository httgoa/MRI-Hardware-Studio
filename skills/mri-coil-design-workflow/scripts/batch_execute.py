"""L1 deterministic batch executor for the artifact-first pipeline.

This module runs INSIDE the CST MCP python process (via `cst_run_python_tool`,
where `de`, `project`, `model3d` are in scope). It replays a list of
pre-generated `.bas` history blocks in ONE call, inside CST quiet mode, and
captures per-block success/failure — WITHOUT any LLM in the loop. The agent
sends this once and receives one structured table back.

Two execution modes share the SAME pre-generated `.bas` set:

  * batch_quiet   (production): all blocks inside `de.quiet_mode_enabled()`,
                  no popups, fewest COM round-trips, fastest.
  * demo_stepwise (recording):  quiet mode OFF, front-end visible; caller drives
                  ResetViewToStructure + milestone pauses between blocks. Use
                  `run_blocks(..., quiet=False)` and iterate one block per call
                  from the agent side so the viewport repaints.

Return contract (assign to `result` in cst_run_python_tool):
  {
    "ok": bool,                      # all attempted blocks succeeded
    "executed": [ {title, status, error} ... ],
    "failed_index": int | None,      # index into `blocks` that failed (stop point)
    "completed_titles": [str ...],   # blocks already in history (checkpoint)
  }

On failure the batch stops at the offending block (checkpoint). Re-run with the
remaining blocks after L2/L3 repairs that one `.bas`.
"""
from __future__ import annotations

import os
from typing import Callable, List, Optional, Sequence, Tuple


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def run_blocks(
    project,
    de,
    blocks: Sequence[Tuple[str, str]],
    quiet: bool = True,
    start_index: int = 0,
    stop_on_error: bool = True,
    on_block: Optional[Callable[[int, str], None]] = None,
) -> dict:
    """Replay (title, bas_path) blocks via project.modeler.add_to_history.

    Args:
      project: active CST project (has .modeler, .save).
      de:      DesignEnvironment (provides quiet_mode_enabled()).
      blocks:  ordered [(title, bas_path), ...].
      quiet:   True → wrap the whole batch in de.quiet_mode_enabled()
               (batch_quiet). False → visible (demo_stepwise).
      start_index: resume from this block index (checkpoint continue).
      stop_on_error: stop at the first failing block (default).
      on_block: optional callback(index, title) after each successful block —
                used by demo_stepwise to fit-view / pause between blocks.
    """
    executed: List[dict] = []
    completed: List[str] = []
    failed_index: Optional[int] = None

    def _do_one(idx: int, title: str, path: str) -> bool:
        if not os.path.isfile(path):
            executed.append({"title": title, "status": "error",
                             "error": f"bas file not found: {path}"})
            return False
        try:
            project.modeler.add_to_history(title, _read(path))
            executed.append({"title": title, "status": "ok", "error": None})
            completed.append(title)
            if on_block is not None:
                on_block(idx, title)
            return True
        except Exception as exc:  # noqa: BLE001 — capture exact CST error text
            executed.append({"title": title, "status": "error", "error": repr(exc)})
            return False

    work = list(enumerate(blocks))[start_index:]

    def _loop() -> None:
        nonlocal failed_index
        for idx, (title, path) in work:
            ok = _do_one(idx, title, path)
            if not ok:
                failed_index = idx
                if stop_on_error:
                    return

    if quiet:
        # quiet_mode_enabled suppresses GUI dialogs (Abort/Retry/Ignore etc.)
        with de.quiet_mode_enabled():
            _loop()
    else:
        _loop()

    try:
        project.save()
    except Exception:  # noqa: BLE001 — save failure shouldn't mask block results
        pass

    return {
        "ok": failed_index is None,
        "executed": executed,
        "failed_index": failed_index,
        "completed_titles": completed,
    }


# --- Convenience for the agent when sending via cst_run_python_tool -----------
# The agent typically does:
#   exec(open(<this file>).read())
#   result = run_blocks(project, de, BLOCKS, quiet=True)
# where BLOCKS = [("define parameters", r"...\parameters.bas"), ...]
