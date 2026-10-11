#!/usr/bin/env bash

set -u
source "$(dirname "$0")/common.sh"

if test "$#" -lt 1 || test "$#" -gt 2; then
    printf 'Usage: %s <CaseTag> [RunID]\n' "$0" >&2
    exit 2
fi
validate_case_tag "$1" || exit $?
case_dir="$(case_dir_for "$1")"
run_id="${2:-}"

if test -z "$run_id"; then
    run_id="$(find "$case_dir/executions" -mindepth 1 -maxdepth 1 -type d -printf '%T@\t%f\n' 2>/dev/null | sort -nr | cut -f2- | sed -n '1p')"
fi
test -n "$run_id" || { printf 'No executions for %s\n' "$1" >&2; exit 3; }
validate_case_tag "$run_id" || exit $?
execution_dir="$case_dir/executions/$run_id"
test -d "$execution_dir" || { printf 'RunID not found: %s\n' "$run_id" >&2; exit 4; }

sed -n '1,200p' "$execution_dir/execution.json"
log_file="$(find "$execution_dir/logs" -maxdepth 1 -type f -name '*.log' -printf '%T@\t%p\n' 2>/dev/null | sort -nr | cut -f2- | sed -n '1p')"
if test -n "$log_file"; then
    printf '\n== %s ==\n' "$log_file"
    tail -n 200 "$log_file"
else
    printf '\nNo runtime log: execution has not been launched.\n'
fi
