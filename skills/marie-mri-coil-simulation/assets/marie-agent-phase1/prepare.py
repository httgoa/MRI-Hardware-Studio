#!/usr/bin/env python3
"""Prepare immutable MARIE execution evidence without launching MATLAB."""

from __future__ import annotations

import hashlib
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

CASE_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def fail(message: str, code: int = 2) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def inside(root: Path, relative: str, label: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        fail(f"{label} escapes workspace: {relative}")
    if not candidate.is_file():
        fail(f"{label} not found: {candidate}", 3)
    return candidate


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_dependency(root: Path, case_dir: Path, spec: dict[str, object]) -> dict[str, object]:
    label = str(spec.get("label", ""))
    stage = str(spec.get("stage", ""))
    pattern = str(spec.get("glob", ""))
    if not label or not CASE_RE.fullmatch(label) or not stage or not CASE_RE.fullmatch(stage):
        fail(f"Invalid dependency label/stage: {spec}", 4)
    if not pattern or Path(pattern).is_absolute() or ".." in Path(pattern).parts:
        fail(f"Invalid dependency glob: {pattern}", 4)
    candidates: list[tuple[str, Path, dict[str, object]]] = []
    for state_path in (case_dir / "executions").glob("*/execution.json"):
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if state.get("stage") != stage or state.get("state") != "succeeded":
            continue
        for artifact in state_path.parent.glob(pattern):
            if artifact.is_file():
                candidates.append((str(state.get("finished_at") or state.get("created_at") or ""), artifact, state))
    if not candidates:
        fail(f"Required dependency not found: label={label} stage={stage} glob={pattern}", 7)
    _, source, producer = max(candidates, key=lambda item: item[0])
    source = source.resolve()
    source.relative_to(root)
    return {
        "label": label, "stage": stage, "producer_run_id": producer.get("run_id"),
        "source": source.relative_to(root).as_posix(), "bytes": source.stat().st_size,
        "sha256": sha256(source),
    }


def git_output(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=False
    )
    return result.stdout.strip()


def main() -> int:
    if len(sys.argv) != 3:
        fail(f"Usage: {sys.argv[0]} <CaseTag> <stage>")
    case_tag, stage_name = sys.argv[1:]
    if not CASE_RE.fullmatch(case_tag) or not CASE_RE.fullmatch(stage_name):
        fail("CaseTag and stage must contain only ASCII letters, digits, dot, underscore, or hyphen")

    root = Path(__file__).resolve().parents[2]
    case_dir = root / "runs" / case_tag
    config_path = case_dir / "agent-case.json"
    if not config_path.is_file():
        fail(f"Case configuration not found: {config_path}", 3)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1 or config.get("case_tag") != case_tag:
        fail("agent-case.json schema_version/case_tag mismatch", 4)

    executions_dir = case_dir / "executions"
    executions_dir.mkdir(exist_ok=True)
    lock_path = executions_dir / ".case.lock"
    lock_handle = lock_path.open("a+")
    fcntl.flock(lock_handle, fcntl.LOCK_EX)
    for state_path in executions_dir.glob("*/execution.json"):
        try:
            existing = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            fail(f"Unreadable existing execution state: {state_path}", 4)
        if existing.get("state") in {"authorized", "launching", "running"}:
            fail(f"Case already has an active execution: {state_path.parent.name}", 5)

    stage = config.get("stages", {}).get(stage_name)
    if not isinstance(stage, dict):
        fail(f"Stage not configured: {stage_name}", 4)
    if not stage.get("enabled", False):
        fail(f"Stage is disabled: {stage_name}; reason: {stage.get('disabled_reason', 'not specified')}", 5)

    resources = config.get("resources", {})
    workers = resources.get("workers")
    if not isinstance(workers, int) or isinstance(workers, bool) or not 1 <= workers <= 64:
        fail("resources.workers must be an integer from 1 to 64", 4)
    gpu = resources.get("gpu", 0)
    if not isinstance(gpu, int) or isinstance(gpu, bool) or gpu not in {0, 1}:
        fail("resources.gpu must be 0 or 1", 4)
    dependencies = [
        resolve_dependency(root, case_dir, item) for item in stage.get("dependencies", [])
    ]

    runner = inside(root, stage["runner"], "runner")
    artifacts = config.get("artifacts", {})
    snapshot_sources: list[tuple[str, Path]] = [("runner", runner), ("agent_case", config_path)]
    for key in ("input_json", "geometry_file", "active_circuit_json"):
        value = artifacts.get(key, "")
        if value:
            snapshot_sources.append((key, inside(root, value, key)))

    timestamp = datetime.now().astimezone()
    run_base = f"{timestamp:%Y%m%d_%H%M%S}_{stage_name}"
    run_id = run_base
    suffix = 1
    while (executions_dir / run_id).exists():
        suffix += 1
        run_id = f"{run_base}_{suffix:02d}"

    execution_dir = executions_dir / run_id
    snapshots_dir = execution_dir / "snapshots"
    logs_dir = execution_dir / "logs"
    validation_dir = execution_dir / "validation"
    snapshots_dir.mkdir(parents=True)
    logs_dir.mkdir()
    validation_dir.mkdir()

    hashes: list[dict[str, object]] = []
    for label, source in snapshot_sources:
        target = snapshots_dir / f"{label}__{source.name}"
        shutil.copy2(source, target)
        hashes.append(
            {
                "label": label,
                "source": source.relative_to(root).as_posix(),
                "snapshot": target.relative_to(root).as_posix(),
                "bytes": source.stat().st_size,
                "sha256": sha256(source),
            }
        )

    (snapshots_dir / "hashes.sha256").write_text(
        "".join(f"{item['sha256']}  {item['snapshot']}\n" for item in hashes),
        encoding="utf-8",
    )

    matlab = config.get("matlab") or os.environ.get("MATLAB_BIN")
    if not matlab:
        fail("MATLAB executable is not configured; set config.matlab or MATLAB_BIN", 6)
    matlab_path = Path(matlab)
    if not matlab_path.is_file() or not os.access(matlab_path, os.X_OK):
        fail(f"MATLAB executable unavailable: {matlab}", 6)
    runner_rel = runner.relative_to(root).as_posix()
    frozen_runner = next(Path(item["snapshot"]) for item in hashes if item["label"] == "runner")
    pool_helper = root / "tools" / "marie-agent" / "matlab"
    batch_expression = (
        f"cd('{root.as_posix()}'); startup; "
        f"addpath('{pool_helper.as_posix()}'); marie_agent_configure_pool({workers}); "
        f"run('{frozen_runner.as_posix()}')"
    )
    command = [matlab, "-batch", batch_expression]
    command_preview = " ".join(json.dumps(part) for part in command)
    (execution_dir / "command.txt").write_text(command_preview + "\n", encoding="utf-8")

    cost = stage.get("cost", "unknown")
    writes_json = bool(stage.get("writes_active_json", False))
    approval_required = cost in {"high", "very-high"} or writes_json
    disk = shutil.disk_usage(root)
    execution = {
        "schema_version": 2,
        "case_tag": case_tag,
        "run_id": run_id,
        "stage": stage_name,
        "state": "prepared",
        "scientific_status_changed": False,
        "created_at": timestamp.isoformat(timespec="seconds"),
        "started_at": None,
        "finished_at": None,
        "exit_code": None,
        "runner": runner_rel,
        "frozen_runner": frozen_runner.as_posix(),
        "command": command,
        "log": f"runs/{case_tag}/executions/{run_id}/logs/{stage_name}.log",
        "cost": cost,
        "writes_active_json": writes_json,
        "approval_required": approval_required,
        "launch_available": True,
        "resources_requested": resources,
        "production_profile": config.get("production_profile", "legacy-geometry-only"),
        "dependencies": dependencies,
        "disk_free_bytes_at_prepare": disk.free,
        "git_branch": git_output(root, "branch", "--show-current"),
        "git_head": git_output(root, "rev-parse", "HEAD"),
        "git_porcelain_sha256": hashlib.sha256(
            git_output(root, "status", "--porcelain").encode("utf-8")
        ).hexdigest(),
        "snapshots": hashes,
        "warnings": [
            "Preparation does not authorize or launch MATLAB.",
            "Runtime which -all, process state, and resource availability must be rechecked before launch.",
        ],
    }
    gate_material = {
        "case_tag": case_tag,
        "run_id": run_id,
        "stage": stage_name,
        "command": command,
        "cost": cost,
        "writes_active_json": writes_json,
        "resources_requested": resources,
        "production_profile": config.get("production_profile", "legacy-geometry-only"),
        "dependencies": dependencies,
        "snapshots": [{"label": item["label"], "source": item["source"], "sha256": item["sha256"]} for item in hashes],
    }
    execution["gate_digest"] = hashlib.sha256(
        json.dumps(gate_material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    (execution_dir / "execution.json").write_text(
        json.dumps(execution, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    gate = f"""# Execution preparation gate

- CaseTag: `{case_tag}`
- RunID: `{run_id}`
- Stage: `{stage_name}`
- Cost: `{cost}`
- Writes active circuit JSON: `{str(writes_json).lower()}`
- Explicit approval required: `{str(approval_required).lower()}`
- Runner: `{runner_rel}`
- Requested workers: `{resources.get('workers', 'unspecified')}`
- Requested GPU: `{resources.get('gpu', 'unspecified')}`
- Production profile: `{execution['production_profile']}`
- Resolved dependencies: `{len(dependencies)}`
- Disk free at preparation: `{disk.free}` bytes
- Launch interface available: `true` (launch remains a separate explicit action)
- Gate digest: `{execution['gate_digest']}`

## Command preview

```text
{command_preview}
```

This file is not proof of runtime validation or user approval. Recheck processes, resources, paths, output overwrite risk, locks, and authorization before launch.
"""
    (execution_dir / "gate.md").write_text(gate, encoding="utf-8")
    print(execution_dir.relative_to(root).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
