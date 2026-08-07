"""Compact CST-live wrapper for one FD D1 batch case.

Run inside ``cst_run_python_tool`` with live ``de/project/model3d`` objects.
"""

from __future__ import annotations

import json
import time
import traceback

import data_prep_fd_dipole_complete_case as single
import run_d1_fd_batch as batch


REQUIRED_RESULT_NODES = [
    r"2D/3D Results\H-Field\h-field (f=0.21) [1]",
    r"2D/3D Results\E-Field\e-field (f=0.21) [1]",
    r"2D/3D Results\Power Loss Dens.\loss (f=0.21) [1]",
    r"2D/3D Results\Surface Current\surface current (f=0.21) [1]",
]


def run_case(de, project, model3d, case_matrix_id: str, poll_seconds: int = 45) -> dict:
    result = {"case_matrix_id": case_matrix_id, "wrapper_version": "stage-aware-v2"}
    try:
        batch.record_stage(
            case_matrix_id,
            "active",
            "planned",
            event="compact_wrapper_start",
            detail={"wrapper_fix": "stage-aware return checks; poll uses is_running"},
        )

        out = single.live_build_fd_case(de, project, model3d, case_matrix_id)
        batch.record_live_result(case_matrix_id, "build", out)
        if out.get("ok") is not True:
            raise RuntimeError("build failed: " + str(out.get("failed") or out))

        out = single.live_start_solver(project, model3d)
        batch.record_live_result(case_matrix_id, "start_solver", out)
        if out.get("started") is not True:
            raise RuntimeError("start_solver failed: " + str(out))

        polls = 0
        while True:
            out = single.live_poll_solver(project, model3d)
            batch.record_live_result(case_matrix_id, "poll_solver", out)
            polls += 1
            running = bool(out.get("is_running"))
            info = json.dumps(out.get("solver_info"), default=str).lower()
            if (not running) and any(token in info for token in ["failed", "aborted"]):
                raise RuntimeError("solver failed/aborted: " + info[:1000])
            if not running:
                break
            time.sleep(poll_seconds)
        result["poll_count"] = polls
        batch.record_stage(case_matrix_id, "active", "solver_done", event="compact_wrapper_solver_done")

        for _attempt in range(10):
            oks = []
            for node in REQUIRED_RESULT_NODES:
                try:
                    oks.append(bool(model3d.SelectTreeItem(node)))
                except Exception:
                    oks.append(False)
            if all(oks):
                break
            try:
                project.save()
            except Exception:
                pass
            time.sleep(15)
        else:
            raise RuntimeError("post-solve result nodes not selectable before export")

        out = single.live_export_fields_and_sar(de, project, model3d, case_matrix_id)
        batch.record_live_result(case_matrix_id, "export", out)
        exports = out.get("exports", {})
        export_ok = all(
            bool(exports.get(key, {}).get("ok"))
            for key in ["hfield_h5", "efield_h5", "loss_h5", "surface_current_h5"]
        ) and bool(exports.get("sar10g_h5", {}).get("ok") or exports.get("sar10g_h5", {}).get("case_copy_bytes", 0))
        if not export_ok:
            raise RuntimeError("export incomplete: " + json.dumps(exports, default=str)[:2000])

        final = batch.finalize_case(case_matrix_id)
        record = final.get("record", {})
        state = batch.load_progress()["cases"][case_matrix_id]
        result.update(
            {
                "status": state.get("status"),
                "stage": state.get("stage"),
                "record": final.get("local_record"),
                "qa_status": record.get("qa", {}).get("qa_status"),
                "sar_status": record.get("sar_signature", {}).get("sar_status"),
            }
        )
    except Exception as exc:
        detail = {"error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()}
        result["batch_state"] = batch.record_stage(
            case_matrix_id,
            "needs_codex",
            "active_or_solver",
            event="compact_wrapper_exception",
            detail=detail,
        )
        result["error"] = detail
    return result
