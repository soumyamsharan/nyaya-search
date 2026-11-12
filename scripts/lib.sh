#!/usr/bin/env bash
# Shared helpers for the deploy scripts. Source it; do not run it.
set -euo pipefail

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }
need() { for c in "$@"; do command -v "$c" >/dev/null || die "missing command: $c"; done; }
stamp() { date -u +%Y%m%dT%H%M%SZ; }

# Run psql/pg_dump/pg_restore inside a compose project's db container.
#   db_exec <compose-file> <command...>
db_exec() {
  local file=$1; shift
  docker compose -f "$file" exec -T db "$@"
}
