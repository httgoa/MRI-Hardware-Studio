#!/usr/bin/env python3
"""Regenerate MARIE skill bundle hashes after an approved source update."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date
from pathlib import Path


def describe(path: Path, root: Path, kind: str) -> dict[str, object]:
    return {
        "kind": kind,
        "name": path.name,
        "bundle_path": path.relative_to(root).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skill-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument(
        "--source-workspace",
        default=os.environ.get("MARIE_ROOT", "/path/to/marie-tools"),
    )
    args = parser.parse_args()

    root = args.skill_root.resolve()
    documents = sorted((root / "references" / "workspace-docs").glob("*.md"))
    matlab_scripts = sorted((root / "assets" / "matlab-scripts").rglob("*.m"))
    test_files = (
        sorted(path for path in (root / "tests").rglob("*") if path.is_file())
        if (root / "tests").is_dir()
        else []
    )
    agent_tools = sorted(
        path
        for path in (root / "assets" / "marie-agent-phase1").rglob("*")
        if path.is_file()
    )
    support_paths = [
        root / "SKILL.md",
        root / "agents" / "openai.yaml",
        root / "references" / "architecture-interfaces.md",
        root / "references" / "document-index.md",
        root / "references" / "rx-array-validation.md",
        root / "references" / "snr-measurement-normalization.md",
        root / "references" / "storage-layout.md",
        root / "references" / "upstream-and-license.md",
        root / "references" / "uisnr-workflow-and-contracts.md",
        root / "references" / "uisnr-icp-complex-conventions.md",
        root / "references" / "uisnr-convergence-validation.md",
        *sorted((root / "scripts").glob("*")),
    ]
    support_paths = [
        path
        for path in support_paths
        if path.is_file() and path.name != "refresh_bundle_manifest.py"
    ]

    manifest = {
        "schema_version": 2,
        "snapshot_date": date.today().isoformat(),
        "source_workspace": args.source_workspace,
        "documents": [describe(path, root, "document") for path in documents],
        "matlab_scripts": [
            describe(path, root, "matlab-script") for path in matlab_scripts
        ],
        "agent_tools": [
            describe(path, root, "agent-tool") for path in agent_tools
        ],
        "tests": [describe(path, root, "test") for path in test_files],
        "support_files": [
            describe(path, root, "skill-support") for path in support_paths
        ],
        "self_hash_exclusion": "references/bundle-manifest.json and scripts/refresh_bundle_manifest.py are excluded to avoid self-referential hashes.",
    }
    target = root / "references" / "bundle-manifest.json"
    target.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
