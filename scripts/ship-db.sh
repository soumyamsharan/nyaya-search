#!/usr/bin/env bash
# Ship the locally ingested database to the server without touching live data:
# dump locally -> copy -> restore into a NEW database -> point the API at it -> keep the old one for rollback.
#   scripts/ship-db.sh ubuntu@<server-ip> [remote-dir]
source "$(dirname "$0")/lib.sh"
need docker scp ssh

target=${1:?usage: ship-db.sh user@host [remote-dir]}
remote_dir=${2:-nyaya}
local_compose="$(dirname "$0")/../docker-compose.yml"
name="nyaya_$(date -u +%Y%m%d%H%M)"
dump="/tmp/${name}.dump"

log "dumping local database"
db_exec "$local_compose" pg_dump -U nyaya -d nyaya -Fc >"$dump"
log "dump size: $(du -h "$dump" | cut -f1)"

log "copying to $target:$remote_dir/backups/"
scp "$dump" "$target:$remote_dir/backups/${name}.dump"

log "restoring into new database $name and switching the API to it"
ssh "$target" bash -s -- "$remote_dir" "$name" <<'REMOTE'
set -euo pipefail
cd "$1"; name=$2
dc() { docker compose -f compose.prod.yml "$@"; }
dc exec -T db createdb -U nyaya "$name"
dc exec -T db pg_restore -U nyaya -d "$name" --no-owner "/backups/${name}.dump"
previous=$(grep -E '^POSTGRES_DB=' .env | cut -d= -f2 || true)
if grep -qE '^POSTGRES_DB=' .env; then sed -i "s/^POSTGRES_DB=.*/POSTGRES_DB=${name}/" .env; else echo "POSTGRES_DB=${name}" >>.env; fi
dc up -d api
echo "API now uses ${name}; previous database ${previous:-nyaya} kept for rollback."
REMOTE
rm -f "$dump"
log "done. Roll back by setting POSTGRES_DB back in the server's .env and running: docker compose -f compose.prod.yml up -d api"
