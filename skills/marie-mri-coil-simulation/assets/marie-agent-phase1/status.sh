#!/usr/bin/env bash

set -u
source "$(dirname "$0")/common.sh"

if test "$#" -ne 1; then
    printf 'Usage: %s <CaseTag>\n' "$0" >&2
    exit 2
fi
validate_case_tag "$1" || exit $?
case_dir="$(case_dir_for "$1")"
test -d "$case_dir" || { printf 'Case not found: %s\n' "$case_dir" >&2; exit 3; }

if test -f "$case_dir/status.json"; then
    printf '== Scientific status ==\n'
    sed -n '1,160p' "$case_dir/status.json"
fi

printf '\n== Executions ==\n'
if ! test -d "$case_dir/executions"; then
    printf 'none\n'
    exit 0
fi
find "$case_dir/executions" -mindepth 2 -maxdepth 2 -name execution.json \
    -printf '%T@\t%p\n' | sort -nr | cut -f2- | while IFS= read -r item; do
        python - "$item" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text(encoding="utf-8"))
print(f"{d['run_id']}\t{d['stage']}\t{d['state']}\t{d['created_at']}\t{p.parent}")
PY
    done
