#!/usr/bin/env python3
"""Control-plane runner for D1 fractionated-dipole data-prep batches.

This mirrors ``run_d1_regular_batch.py`` while keeping the FD single-case
engine separate.  It plans, tracks, and resumes repeated FD cases; live CST work
still happens through code emitted for ``cst_run_python_tool``.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import traceback
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
REPO_ROOT = SKILL_ROOT.parents[2]
PROGRESS_PATH = REPO_ROOT / "results_data_prep" / "fd_batch_progress.json"

sys.path.insert(0, str(SCRIPT_DIR))
import data_prep_fd_dipole_complete_case as single  # noqa: E402
import run_d1_regular_batch as control  # noqa: E402


LIVE_STAGES = control.LIVE_STAGES
STAGES = control.STAGES
STATUSES = control.STATUSES


def _install_fd_context() -> None:
    control.single = single
    control.PROGRESS_PATH = PROGRESS_PATH
    control.select_rows = select_rows
    control.load_progress = load_progress
    control.emit_live_code = emit_live_code


def read_matrix() -> list[dict[str, str]]:
    with single.CASE_MATRIX.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def select_rows(
    cases: list[str] | None = None,
    roles: list[str] | None = None,
    include_fractionated: bool = True,
    max_cases: int | None = None,
) -> list[dict[str, str]]:
    del include_fractionated  # FD runner is family-specific by construction.
    wanted_cases = set(cases or [])
    wanted_roles = set(roles or [])
    rows: list[dict[str, str]] = []
    for row in read_matrix():
        if wanted_cases and row["case_matrix_id"] not in wanted_cases:
            continue
        if wanted_roles and row["role"] not in wanted_roles:
            continue
        if row["family"] != "fractionated_dipole":
            continue
        if row["source_seed"] != "template" or row["network_role"] != "direct_port":
            continue
        rows.append(row)
        if max_cases is not None and len(rows) >= max_cases:
            break
    return rows


def load_progress() -> dict[str, Any]:
    progress = control._read_json(
        PROGRESS_PATH,
        {
            "schema_version": "data_prep.d1_fd_batch.v1",
            "created_at": control._now(),
            "updated_at": None,
            "selection": {},
            "cases": {},
        },
    )
    progress.setdefault("schema_version", "data_prep.d1_fd_batch.v1")
    progress.setdefault("cases", {})
    return progress


def emit_live_code(case_matrix_id: str, live_stage: str) -> str:
    if live_stage not in LIVE_STAGES:
        raise ValueError(f"live stage must be one of {LIVE_STAGES}")
    script_dir = repr(str(SCRIPT_DIR))
    case_repr = repr(case_matrix_id)
    if live_stage == "build":
        call = "out = single.live_build_fd_case(de, project, model3d, case_matrix_id)"
        start_stage = "planned"
    elif live_stage == "start_solver":
        call = "out = single.live_start_solver(project, model3d)"
        start_stage = "project_built"
    elif live_stage == "poll_solver":
        call = "out = single.live_poll_solver(project, model3d)"
        start_stage = "solver_started"
    else:
        call = "out = single.live_export_fields_and_sar(de, project, model3d, case_matrix_id)"
        start_stage = "solver_done"
    return f"""# Paste into cst_run_python_tool. For build, start from an active blank MWS project.
import sys
import traceback
sys.path.insert(0, {script_dir})
import data_prep_fd_dipole_complete_case as single
import run_d1_fd_batch as batch

case_matrix_id = {case_repr}
batch.record_stage(case_matrix_id, "active", "{start_stage}", event="live_{live_stage}_start")
try:
    {call}
    state = batch.record_live_result(case_matrix_id, "{live_stage}", out)
    result = {{"live_result": out, "batch_state": state}}
except Exception as exc:
    detail = {{"error": f"{{type(exc).__name__}}: {{exc}}", "traceback": traceback.format_exc()}}
    state = batch.record_stage(case_matrix_id, "needs_codex", "{start_stage}", event="live_{live_stage}_exception", detail=detail)
    result = {{"error": detail, "batch_state": state}}
"""


def main() -> None:
    _install_fd_context()
    control.main()


_install_fd_context()

inspect_case = control.inspect_case
init_progress = control.init_progress
selected_status_rows = control.selected_status_rows
next_case = control.next_case
record_stage = control.record_stage
record_live_result = control.record_live_result
finalize_case = control.finalize_case
action_for_stage = control.action_for_stage


if __name__ == "__main__":
    main()
