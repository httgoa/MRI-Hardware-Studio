#!/usr/bin/env python3
"""Low-noise live wrapper for regular-dipole batch cases.

This module is meant to be imported from ``cst_run_python_tool``. It keeps the
control-plane state in ``run_d1_regular_batch.py`` while reducing CST MCP
round-trips after the first case has proven the pipeline.
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path
from typing import Any

import data_prep_dipole_complete_case as single
import run_d1_regular_batch as batch


def _new_mws_project(de, manager=None):
    project = de.new_mws()
    if manager is not None:
        try:
            manager.project = project
        except Exception:
            pass
    return project, project.model3d


def close_active_project(project, *, manager=None, save: bool = True, sleep_s: float = 2.0) -> dict[str, Any]:
    """Close the completed case project without closing the CST Design Environment."""
    filename = None
    try:
        filename = getattr(project, "filename", None)
    except Exception:
        filename = None
    if save:
        project.save()
    project.close()
    if manager is not None:
        try:
            manager.project = None
        except Exception:
            pass
    if sleep_s > 0:
        time.sleep(sleep_s)
    return {"closed": True, "project_path": str(filename) if filename else None, "saved": save}


def _record_exception(case_id: str, stage: str, live_stage: str, exc: BaseException) -> dict[str, Any]:
    detail = {"error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()}
    return batch.record_stage(
        case_id,
        "needs_codex",
        stage,
        event=f"live_{live_stage}_exception",
        detail=detail,
    )


def run_one_case_live(
    de,
    case_id: str,
    *,
    manager=None,
    poll_interval_s: float = 30.0,
    poll_timeout_s: float = 1800.0,
) -> dict[str, Any]:
    """Run build -> async solve/poll -> export for one selected case.

    The caller should run ``run_d1_regular_batch.py --finalize --case <case>``
    after this returns with ``stage == "fields_exported"``.
    """
    events: list[dict[str, Any]] = []

    try:
        project, model3d = _new_mws_project(de, manager=manager)
        batch.record_stage(case_id, "active", "planned", event="live_build_start")
        out = single.live_build_case(de, project, model3d, case_id)
        state = batch.record_live_result(case_id, "build", out)
        events.append({"stage": "build", "state": state, "out": out})
        if state["status"] in {"needs_codex", "failed"}:
            return {"ok": False, "case_matrix_id": case_id, "events": events, "state": state}
    except Exception as exc:  # noqa: BLE001
        state = _record_exception(case_id, "planned", "build", exc)
        return {"ok": False, "case_matrix_id": case_id, "events": events, "state": state}

    try:
        batch.record_stage(case_id, "active", "project_built", event="live_start_solver_start")
        out = single.live_start_solver(project, model3d)
        state = batch.record_live_result(case_id, "start_solver", out)
        events.append({"stage": "start_solver", "state": state, "out": out})
        if state["status"] in {"needs_codex", "failed"}:
            return {"ok": False, "case_matrix_id": case_id, "events": events, "state": state}
    except Exception as exc:  # noqa: BLE001
        state = _record_exception(case_id, "project_built", "start_solver", exc)
        return {"ok": False, "case_matrix_id": case_id, "events": events, "state": state}

    deadline = time.time() + poll_timeout_s
    while True:
        try:
            batch.record_stage(case_id, "active", "solver_started", event="live_poll_solver_start")
            out = single.live_poll_solver(project, model3d)
            state = batch.record_live_result(case_id, "poll_solver", out)
            events.append({"stage": "poll_solver", "state": state, "out": out})
            if state["status"] in {"needs_codex", "failed"}:
                return {"ok": False, "case_matrix_id": case_id, "events": events, "state": state}
            if state["stage"] == "solver_done":
                break
            if time.time() >= deadline:
                detail = {"error": f"solver poll timeout after {poll_timeout_s:g}s"}
                state = batch.record_stage(
                    case_id,
                    "needs_codex",
                    "solver_started",
                    event="live_poll_solver_timeout",
                    detail=detail,
                )
                return {"ok": False, "case_matrix_id": case_id, "events": events, "state": state}
            time.sleep(poll_interval_s)
        except Exception as exc:  # noqa: BLE001
            state = _record_exception(case_id, "solver_started", "poll_solver", exc)
            return {"ok": False, "case_matrix_id": case_id, "events": events, "state": state}

    try:
        batch.record_stage(case_id, "active", "solver_done", event="live_export_start")
        out = single.live_export_fields_and_sar(de, project, model3d, case_id)
        state = batch.record_live_result(case_id, "export", out)
        events.append({"stage": "export", "state": state, "out": out})
        return {
            "ok": state["status"] not in {"needs_codex", "failed"},
            "case_matrix_id": case_id,
            "events": events,
            "state": state,
            "finalize_command": f"python {Path(batch.__file__).as_posix()} --finalize --case {case_id}",
        }
    except Exception as exc:  # noqa: BLE001
        state = _record_exception(case_id, "solver_done", "export", exc)
        return {"ok": False, "case_matrix_id": case_id, "events": events, "state": state}
