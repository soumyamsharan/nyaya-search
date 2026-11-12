#!/usr/bin/env bash
# Nightly backup on the server: dump the live database, upload to OCI Object Storage, keep the newest N.
# Cron (as the deploy user):  15 2 * * * cd ~/nyaya && scripts/backup.sh >> backups/backup.log 2>&1
# Needs the OCI CLI configured for this user (oci setup config) and BACKUP_BUCKET in .env.
source "$(dirname "$0")/lib.sh"
need docker oci
set -a; source .env; set +a
bucket=${BACKUP_BUCKET:?set BACKUP_BUCKET in .env}
keep=${BACKUP_KEEP:-7}
db=${POSTGRES_DB:-nyaya}
file="backup-$(stamp).dump"

log "dumping $db"
db_exec compose.prod.yml pg_dump -U nyaya -d "$db" -Fc -f "/backups/$file"
log "uploading $file to bucket $bucket"
oci os object put --bucket-name "$bucket" --file "backups/$file" --name "$file" --no-overwrite >/dev/null

log "pruning: keep newest $keep in the bucket and locally"
oci os object list --bucket-name "$bucket" --prefix backup- --all --query 'data[].name' --raw-output \
  | tr -d '[]", ' | grep . | sort -r | tail -n +"$((keep + 1))" \
  | while read -r old; do oci os object delete --bucket-name "$bucket" --object-name "$old" --force; done
ls -1t backups/backup-*.dump | tail -n +"$((keep + 1))" | xargs -r rm -f
log "backup complete"
