#!/usr/bin/env bash

# Portable read-only entry into an active MARIE workspace.
set -u

workspace="${1:-${MARIE_WORKSPACE:-$(pwd)}}"
requested_case="${2:-}"
bootstrap="$workspace/tools/session_bootstrap.sh"

if ! test -d "$workspace"; then
    printf 'MARIE workspace not found: %s\n' "$workspace" >&2
    exit 2
fi

if ! test -f "$bootstrap"; then
    printf 'Initialization interface not found: %s\n' "$bootstrap" >&2
    printf 'Read AGENTS.md, MARIE_Agent_Harness.md, Git state, runs, resources, and processes manually.\n' >&2
    exit 3
fi

if test -n "$requested_case"; then
    exec bash "$bootstrap" "$requested_case"
fi
exec bash "$bootstrap"
