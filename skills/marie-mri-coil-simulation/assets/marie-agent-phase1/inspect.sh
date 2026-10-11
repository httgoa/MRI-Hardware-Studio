#!/usr/bin/env bash

set -u
source "$(dirname "$0")/common.sh"

requested_case="${1:-}"
if test -n "$requested_case"; then
    validate_case_tag "$requested_case" || exit $?
    exec bash "$MARIE_AGENT_ROOT/tools/session_bootstrap.sh" "$requested_case"
fi
exec bash "$MARIE_AGENT_ROOT/tools/session_bootstrap.sh"
