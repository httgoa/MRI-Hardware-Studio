#!/usr/bin/env bash
set -u
source "$(dirname "$0")/common.sh"
exec python "$(dirname "$0")/approve.py" "$@"
