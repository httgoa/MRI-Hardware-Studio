#!/usr/bin/env python3
"""Control-plane runner for D1 regular-dipole data-prep batches.

This script intentionally does not replace the single-case engine.  It plans,
tracks, and resumes repeated cases, while live CST work still calls
``data_prep_dipole_complete_case.py`` through the CST MCP.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
REPO_ROOT = SKILL_ROOT.parents[2]
PROGRESS_PATH = REPO_ROOT / "results_data_prep" / "batch_progress.json"

sys.path.insert(0, str(SCRIPT_DIR))
import data_prep_dipole_complete_case as single  # noqa: E402


STAGES = [
    "planned",
    "project_built",
    "solver_started",
    "solver_done",
    "fields_exported",
    "record_written",
    "validated",
]
STATUSES = ["pending", "active", "partial", "validated", "failed", "needs_codex", "skipped"]
LIVE_STAGES = ["build", "start_solver", "poll_solver", "export"]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    last_exc = None
    for _attempt in range(10):
        try:
            tmp.replace(path)
            return
        except PermissionError as exc:
            last_exc = exc
            time.sleep(0.2)
    raise last_exc


def _rel(path: str | Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT))
    except Exception:
        return str(path)


def _stage_index(stage: str | None) -> int:
    try:
        return STAGES.index(stage or "planned")
    except ValueError:
        return 0


def _case_state_path(case_matrix_id: str) -> Path:
    return single.case_paths(case_matrix_id)["log_dir"] / "batch_state.json"


def read_matrix() -> list[dict[str, str]]:
    with single.CASE_MATRIX.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def select_rows(
    cases: list[str] | None = None,
    roles: list[str] | None = None,
    include_fractionated: bool = False,
    max_cases: int | None = None,
) -> list[dict[str, str]]:
    wanted_cases = set(cases or [])
    wanted_roles = set(roles or [])
    rows: list[dict[str, str]] = []
    for row in read_matrix():
        if wanted_cases and row["case_matrix_id"] not in wanted_cases:
            continue
        if wanted_roles and row["role"] not in wanted_roles:
            continue
        if not include_fractionated and row["family"] != "regular_dipole":
            continue
        if row["source_seed"] != "template" or row["network_role"] != "direct_port":
            continue
        rows.append(row)
        if max_cases is not None and len(rows) >= max_cases:
            break
    return rows


def _record_path_for(row: dict[str, str]) -> Path:
    rid = single.record_id_for(row)
    return REPO_ROOT / "results_data_prep" / "records" / f"{rid}.json"


def _path_from_record(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def inspect_case(row: dict[str, str]) -> dict[str, Any]:
    case_id = row["case_matrix_id"]
    rid = single.record_id_for(row)
    paths = single.case_paths(case_id)
    case_dir = paths["case_dir"]
    record_path = _record_path_for(row)
    local_record = paths["output_dir"] / "record.json"
    record = None
    record_source = None
    for candidate in (record_path, local_record):
        if candidate.exists():
            try:
                record = json.loads(candidate.read_text(encoding="utf-8"))
                record_source = candidate
                break
            except Exception:
                record = None

    sar_h5 = case_dir / "sar10g_native_norescale_2mm.h5"
    if record:
        sar_h5 = _path_from_record(record.get("field_artifacts", {}).get("sar10g_h5")) or sar_h5

    artifacts = {
        "project": paths["project_path"].exists(),
        "hfield_h5": (case_dir / "hfield_1mm.h5").exists(),
        "loss_h5": (case_dir / "loss_2mm.h5").exists(),
        "loss_txt": (case_dir / "loss_2mm.txt").exists(),
        "surface_current": (case_dir / "surfcurrent_conductor_clean.txt").exists()
        or (case_dir / "surfcurrent_raw.h5").exists(),
        "sar10g_h5": bool(sar_h5 and sar_h5.exists() and sar_h5.stat().st_size > 0),
        "fom": (case_dir / "fom.json").exists(),
        "electrical_summary": (paths["log_dir"] / "electrical_summary.json").exists(),
        "record": bool(record),
    }

    qa_status = None
    sar_status = None
    schema_pass = None
    if record:
        qa_status = record.get("qa", {}).get("qa_status")
        sar_status = record.get("sar_signature", {}).get("sar_status")
        schema_pass = record.get("qa", {}).get("schema_pass")

    validated = (
        qa_status == "validated"
        and sar_status == "validated_native_h5"
        and artifacts["sar10g_h5"]
        and schema_pass is True
    )
    if validated:
        derived_stage = "validated"
        derived_status = "validated"
    elif record:
        derived_stage = "record_written"
        derived_status = "partial" if qa_status != "validated" else "needs_codex"
    elif artifacts["sar10g_h5"] or artifacts["hfield_h5"] or artifacts["loss_h5"] or artifacts["loss_txt"]:
        derived_stage = "fields_exported"
        derived_status = "partial"
    elif artifacts["project"]:
        derived_stage = "project_built"
        derived_status = "active"
    else:
        derived_stage = "planned"
        derived_status = "pending"

    return {
        "case_matrix_id": case_id,
        "record_id": rid,
        "role": row["role"],
        "family": row["family"],
        "L_line_mm": row["L_line_mm"],
        "strip_width_mm": row["strip_width_mm"],
        "coil_to_phantom_mm": row["coil_to_phantom_mm"],
        "record_path": _rel(record_source) if record_source else None,
        "project_path": _rel(paths["project_path"]),
        "case_dir": _rel(case_dir),
        "artifacts": artifacts,
        "qa_status": qa_status,
        "sar_status": sar_status,
        "schema_pass": schema_pass,
        "derived_stage": derived_stage,
        "derived_status": derived_status,
    }


def load_progress() -> dict[str, Any]:
    progress = _read_json(
        PROGRESS_PATH,
        {
            "schema_version": "data_prep.d1_regular_batch.v1",
            "created_at": _now(),
            "updated_at": None,
            "selection": {},
            "cases": {},
        },
    )
    progress.setdefault("cases", {})
    return progress


def _base_case_state(row: dict[str, str]) -> dict[str, Any]:
    inspected = inspect_case(row)
    status = inspected["derived_status"]
    stage = inspected["derived_stage"]
    return {
        "case_matrix_id": row["case_matrix_id"],
        "record_id": inspected["record_id"],
        "role": row["role"],
        "status": status,
        "stage": stage,
        "action": action_for_stage(stage, status),
        "updated_at": _now(),
        "last_error": None,
        "attempts": {},
        "history": [],
        "paths": {
            "project_path": inspected["project_path"],
            "case_dir": inspected["case_dir"],
            "record_path": inspected["record_path"],
        },
        "artifacts": inspected["artifacts"],
        "qa_status": inspected["qa_status"],
        "sar_status": inspected["sar_status"],
    }


def upsert_cases(
    progress: dict[str, Any],
    rows: list[dict[str, str]],
    *,
    preserve_blocked: bool = True,
) -> dict[str, Any]:
    for row in rows:
        cid = row["case_matrix_id"]
        old = progress["cases"].get(cid, {})
        new = _base_case_state(row)
        if old:
            new["history"] = old.get("history", [])
            new["attempts"] = old.get("attempts", {})
            new["last_error"] = old.get("last_error")
            old_status = old.get("status")
            if preserve_blocked and old_status in {"failed", "needs_codex"} and new["status"] != "validated":
                new["status"] = old_status
                new["stage"] = old.get("stage", new["stage"])
            elif _stage_index(old.get("stage")) > _stage_index(new["stage"]) and new["status"] != "validated":
                new["stage"] = old.get("stage")
                new["status"] = old.get("status", new["status"])
        new["action"] = action_for_stage(new["stage"], new["status"])
        progress["cases"][cid] = new
        _write_json(_case_state_path(cid), new)
    progress["updated_at"] = _now()
    return progress


def init_progress(args: argparse.Namespace) -> dict[str, Any]:
    rows = select_rows(
        args.cases,
        args.roles,
        include_fractionated=args.include_fractionated,
        max_cases=args.max_cases,
    )
    progress = load_progress()
    progress["selection"] = {
        "cases": args.cases or [],
        "roles": args.roles or [],
        "include_fractionated": args.include_fractionated,
        "include_validated": args.include_validated,
    }
    upsert_cases(progress, rows)
    _write_json(PROGRESS_PATH, progress)
    return progress


def action_for_stage(stage: str, status: str | None = None) -> str | None:
    if status in {"failed", "needs_codex", "skipped", "validated"}:
        return None
    return {
        "planned": "build",
        "project_built": "start_solver",
        "solver_started": "poll_solver",
        "solver_done": "export",
        "fields_exported": "finalize",
        "record_written": "finalize",
    }.get(stage)


def selected_status_rows(args: argparse.Namespace) -> list[dict[str, Any]]:
    rows = select_rows(
        args.cases,
        args.roles,
        include_fractionated=args.include_fractionated,
        max_cases=args.max_cases,
    )
    progress = load_progress()
    upsert_cases(progress, rows)
    _write_json(PROGRESS_PATH, progress)
    return [progress["cases"][row["case_matrix_id"]] for row in rows]


def next_case(args: argparse.Namespace) -> dict[str, Any] | None:
    rows = selected_status_rows(args)
    candidates = []
    for row in rows:
        if row["status"] == "validated" and not args.include_validated:
            continue
        if row["status"] in {"failed", "needs_codex"} and not args.include_blocked:
            continue
        if row["status"] == "skipped":
            continue
        action = action_for_stage(row["stage"], row["status"])
        if not action:
            continue
        priority = 0 if row["status"] == "active" else 1
        candidates.append((priority, row))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]["case_matrix_id"]))
    case = candidates[0][1]
    return {
        "case_matrix_id": case["case_matrix_id"],
        "record_id": case["record_id"],
        "role": case["role"],
        "status": case["status"],
        "stage": case["stage"],
        "next_action": action_for_stage(case["stage"], case["status"]),
        "project_path": case["paths"]["project_path"],
        "case_dir": case["paths"]["case_dir"],
    }


def record_stage(
    case_matrix_id: str,
    status: str,
    stage: str,
    *,
    event: str | None = None,
    detail: Any = None,
) -> dict[str, Any]:
    row = single.read_case_row(case_matrix_id)
    progress = load_progress()
    upsert_cases(progress, [row], preserve_blocked=False)
    state = progress["cases"][case_matrix_id]
    state["status"] = status
    state["stage"] = stage
    state["action"] = action_for_stage(stage, status)
    state["updated_at"] = _now()
    if status in {"failed", "needs_codex"}:
        state["last_error"] = detail
    if event:
        state.setdefault("history", []).append(
            {"at": _now(), "event": event, "status": status, "stage": stage, "detail": detail}
        )
    progress["cases"][case_matrix_id] = state
    progress["updated_at"] = _now()
    _write_json(PROGRESS_PATH, progress)
    _write_json(_case_state_path(case_matrix_id), state)
    return state


def _live_result_ok(stage: str, output: dict[str, Any]) -> tuple[bool, str, str]:
    if stage == "build":
        return bool(output.get("ok")), "project_built", "active"
    if stage == "start_solver":
        return bool(output.get("started")), "solver_started", "active"
    if stage == "poll_solver":
        if output.get("is_running"):
            return True, "solver_started", "active"
        info_text = json.dumps(output.get("solver_info"), default=str).lower()
        failed = any(token in info_text for token in ["error", "failed", "aborted"])
        return (not failed), ("solver_started" if failed else "solver_done"), ("needs_codex" if failed else "active")
    if stage == "export":
        exports = output.get("exports", {})
        h_ok = bool(exports.get("hfield_h5", {}).get("ok"))
        loss_ok = bool(exports.get("loss_h5", {}).get("ok"))
        sar = exports.get("sar10g_h5", {})
        sar_ok = bool(sar.get("ok") or sar.get("case_copy_bytes", 0))
        return h_ok and loss_ok and sar_ok, "fields_exported", "active"
    return False, "planned", "needs_codex"


def record_live_result(case_matrix_id: str, live_stage: str, output: dict[str, Any]) -> dict[str, Any]:
    ok, next_stage, status = _live_result_ok(live_stage, output)
    if not ok:
        status = "needs_codex"
    paths = single.ensure_dirs(case_matrix_id)
    stamp = _now().replace(":", "").replace("+", "Z")
    out_path = paths["log_dir"] / f"batch_{live_stage}_{stamp}.json"
    _write_json(out_path, output)
    detail = {"live_stage": live_stage, "ok": ok, "result_path": _rel(out_path)}
    if not ok:
        detail["output_excerpt"] = str(output)[:1000]
    return record_stage(
        case_matrix_id,
        status,
        next_stage,
        event=f"live_{live_stage}_complete",
        detail=detail,
    )


def finalize_case(case_matrix_id: str) -> dict[str, Any]:
    paths = single.ensure_dirs(case_matrix_id)
    try:
        result = single.write_record(
            case_matrix_id,
            electrical_summary_path=paths["log_dir"] / "electrical_summary.json",
        )
        record = result["record"]
        validated = record.get("qa", {}).get("qa_status") == "validated"
        sar_validated = record.get("sar_signature", {}).get("sar_status") == "validated_native_h5"
        stage = "validated" if validated and sar_validated else "record_written"
        status = "validated" if stage == "validated" else "partial"
        record_stage(case_matrix_id, status, stage, event="offline_finalize_complete", detail=_rel(result["local_record"]))
        return result
    except Exception as exc:  # noqa: BLE001
        detail = {"error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()}
        record_stage(case_matrix_id, "needs_codex", "fields_exported", event="offline_finalize_failed", detail=detail)
        raise


def emit_live_code(case_matrix_id: str, live_stage: str) -> str:
    if live_stage not in LIVE_STAGES:
        raise ValueError(f"live stage must be one of {LIVE_STAGES}")
    script_dir = repr(str(SCRIPT_DIR))
    case_repr = repr(case_matrix_id)
    if live_stage == "build":
        call = "out = single.live_build_case(de, project, model3d, case_matrix_id)"
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
import data_prep_dipole_complete_case as single
import run_d1_regular_batch as batch

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


def _print_table(rows: list[dict[str, Any]]) -> None:
    headers = ["case", "role", "status", "stage", "action", "record_id", "sar"]
    table = []
    for row in rows:
        table.append(
            [
                row["case_matrix_id"],
                row["role"],
                row["status"],
                row["stage"],
                row.get("action") or "",
                row["record_id"],
                row.get("sar_status") or "",
            ]
        )
    widths = [len(h) for h in headers]
    for line in table:
        for i, value in enumerate(line):
            widths[i] = max(widths[i], len(str(value)))
    print("  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)))
    print("  ".join("-" * widths[i] for i in range(len(headers))))
    for line in table:
        print("  ".join(str(value).ljust(widths[i]) for i, value in enumerate(line)))


def main() -> None:
    ap = argparse.ArgumentParser(description="Plan and resume D1 regular-dipole data-prep batches.")
    ap.add_argument("--cases", nargs="+", default=None, help="Case ids such as RD_A01 RD_S00.")
    ap.add_argument("--roles", nargs="+", default=None, help="Role filter, usually anchor or space_fill.")
    ap.add_argument("--include-fractionated", action="store_true", help="Include non-regular rows; off by default.")
    ap.add_argument("--include-validated", action="store_true", help="Do not hide validated cases from --next.")
    ap.add_argument("--include-blocked", action="store_true", help="Allow --next to return failed/needs_codex rows.")
    ap.add_argument("--max-cases", type=int, default=None, help="Limit selected rows after filters.")
    ap.add_argument("--json", action="store_true", help="Print machine-readable JSON for plan/status/next.")

    commands = ap.add_mutually_exclusive_group()
    commands.add_argument("--plan", action="store_true", help="Show selected cases without writing progress.")
    commands.add_argument("--init", action="store_true", help="Create/update batch_progress.json.")
    commands.add_argument("--status", action="store_true", help="Show progress and derived artifact status.")
    commands.add_argument("--next", action="store_true", help="Print the next resumable case/action.")
    commands.add_argument("--emit-live-code", choices=LIVE_STAGES, help="Emit cst_run_python_tool Python for one live stage.")
    commands.add_argument("--finalize", action="store_true", help="Run offline record writing for --case.")
    commands.add_argument("--mark-stage", action="store_true", help="Manually set --case/--stage/--mark-status.")
    commands.add_argument("--mark-failed", action="store_true", help="Mark --case as needs_codex with --message.")

    ap.add_argument("--case", default=None, help="Single case id for emit/finalize/mark commands.")
    ap.add_argument("--stage", choices=STAGES, default=None, help="Stage for --mark-stage.")
    ap.add_argument("--mark-status", choices=STATUSES, default=None, help="Status for --mark-stage.")
    ap.add_argument("--message", default=None, help="Human note for manual marks.")
    args = ap.parse_args()

    if args.plan:
        rows = [
            _base_case_state(row)
            for row in select_rows(
                args.cases,
                args.roles,
                include_fractionated=args.include_fractionated,
                max_cases=args.max_cases,
            )
        ]
        if args.json:
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        else:
            _print_table(rows)
        return

    if args.init:
        progress = init_progress(args)
        selected = [
            progress["cases"][row["case_matrix_id"]]
            for row in select_rows(
                args.cases,
                args.roles,
                include_fractionated=args.include_fractionated,
                max_cases=args.max_cases,
            )
        ]
        if args.json:
            print(json.dumps({"progress_path": str(PROGRESS_PATH), "cases": selected}, indent=2, ensure_ascii=False))
        else:
            print(f"wrote {PROGRESS_PATH}")
            _print_table(selected)
        return

    if args.status:
        rows = selected_status_rows(args)
        if args.json:
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        else:
            _print_table(rows)
        return

    if args.next:
        item = next_case(args)
        if args.json:
            print(json.dumps(item, indent=2, ensure_ascii=False))
        else:
            print("No resumable case." if item is None else json.dumps(item, indent=2, ensure_ascii=False))
        return

    if args.emit_live_code:
        if not args.case:
            ap.error("--emit-live-code requires --case")
        print(emit_live_code(args.case, args.emit_live_code))
        return

    if args.finalize:
        if not args.case:
            ap.error("--finalize requires --case")
        print(json.dumps(finalize_case(args.case), indent=2, ensure_ascii=False, default=str))
        return

    if args.mark_stage:
        if not args.case or not args.stage or not args.mark_status:
            ap.error("--mark-stage requires --case, --stage, and --mark-status")
        print(json.dumps(record_stage(args.case, args.mark_status, args.stage, event="manual_mark", detail=args.message), indent=2, ensure_ascii=False))
        return

    if args.mark_failed:
        if not args.case:
            ap.error("--mark-failed requires --case")
        print(json.dumps(record_stage(args.case, "needs_codex", args.stage or "planned", event="manual_failed", detail=args.message), indent=2, ensure_ascii=False))
        return

    ap.print_help()


if __name__ == "__main__":
    main()
