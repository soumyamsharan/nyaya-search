#!/bin/sh
# Start Postgres (localhost only, inside the container), then the API in the foreground.
set -eu
pg_ctl --pgdata="$PGDATA" --log=/tmp/postgres.log --wait start
exec api
