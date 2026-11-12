#!/usr/bin/env bash
# Restore drill: restore a backup into a scratch database and check it matches the live one.
#   scripts/restore-drill.sh [compose-file] [dump-file-inside-/backups]
# Defaults: compose.prod.yml and the newest backups/backup-*.dump. Works locally with docker-compose.yml too.
source "$(dirname "$0")/lib.sh"
need docker
compose=${1:-compose.prod.yml}
dump=${2:-$(basename "$(ls -1t backups/backup-*.dump | head -1)")}
live=${POSTGRES_DB:-nyaya}
scratch="restore_drill_$(date -u +%s)"
query="SELECT (SELECT count(*) FROM judgments WHERE status='ok') || '/' || (SELECT count(*) FROM paragraphs) || '/' ||
       (SELECT count(*) FROM citations) || '/' ||
       (SELECT string_agg(id::text, ',' ORDER BY score DESC) FROM (SELECT p.id, paradedb.score(p.id) AS score
          FROM paragraphs p WHERE p.text ||| 'demand notice cheque dishonour' ORDER BY score DESC LIMIT 5) t)"

log "restoring /backups/$dump into $scratch"
db_exec "$compose" createdb -U nyaya "$scratch"
trap 'db_exec "$compose" dropdb -U nyaya --if-exists "$scratch"' EXIT
db_exec "$compose" pg_restore -U nyaya -d "$scratch" --no-owner "/backups/$dump"

expected=$(db_exec "$compose" psql -U nyaya -d "$live" -Atc "$query")
actual=$(db_exec "$compose" psql -U nyaya -d "$scratch" -Atc "$query")
log "live:     $expected"
log "restored: $actual"
[[ "$expected" == "$actual" ]] || die "restore drill FAILED: restored data differs"
log "restore drill PASSED (counts and a sample keyword search match)"
