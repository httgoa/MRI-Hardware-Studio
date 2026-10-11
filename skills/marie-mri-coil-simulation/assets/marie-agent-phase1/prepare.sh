#!/usr/bin/env bash

set -u
source "$(dirname "$0")/common.sh"

if test "$#" -ne 2; then
    printf 'Usage: %s <CaseTag> <stage>\n' "$0" >&2
    exit 2
fi
validate_case_tag "$1" || exit $?
exec python "$MARIE_AGENT_ROOT/tools/marie-agent/prepare.py" "$1" "$2"
