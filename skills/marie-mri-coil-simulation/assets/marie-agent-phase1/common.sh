#!/usr/bin/env bash

set -u

MARIE_AGENT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

validate_case_tag() {
    case "$1" in
        ''|*[!A-Za-z0-9._-]*)
            printf 'Invalid CaseTag: %s\n' "$1" >&2
            return 2
            ;;
    esac
}

case_dir_for() {
    printf '%s/runs/%s\n' "$MARIE_AGENT_ROOT" "$1"
}
