#!/usr/bin/env bash
# Weekly proof that the newest backup restores. Never connects to production.
JOB="sidetrack-restore-check"
. "$(dirname "$(readlink -f "$0")")/backup-lib.sh"

: "${SIDETRACK_BACKUP_DIR:?set SIDETRACK_BACKUP_DIR}"
: "${SIDETRACK_BACKUP_MOUNT:?set SIDETRACK_BACKUP_MOUNT}"
IMAGE="${SIDETRACK_RESTORE_IMAGE:-pgvector/pgvector:pg16}"

require_backup_mount

STEP="finding the newest backup"
newest="$(scheduled_backups | head -n 1)"
if [ -z "$newest" ]; then
  echo "$JOB: no scheduled backup to check" >&2
  exit 1
fi

STEP="verifying the checksum"
(cd "$SIDETRACK_BACKUP_DIR" && sha256sum --check --status "$newest.sha256")

STEP="starting the disposable database"
container="sidetrack-restore-check-$$"
cleanup() { docker rm -f -v "$container" >/dev/null 2>&1 || true; }
docker run -d --name "$container" --network none \
  -e POSTGRES_USER=sidetrack -e POSTGRES_DB=sidetrack \
  -e POSTGRES_HOST_AUTH_METHOD=trust "$IMAGE" >/dev/null

STEP="waiting for the disposable database"
ready=0
for _ in $(seq 1 60); do
  # Connects over TCP because the image's init server only listens on its socket.
  if docker exec "$container" pg_isready -q -h 127.0.0.1 -U sidetrack -d sidetrack; then
    ready=1
    break
  fi
  sleep 1
done
[ "$ready" -eq 1 ]

STEP="restoring"
docker exec -i "$container" pg_restore -U sidetrack -d sidetrack --exit-on-error \
  <"$SIDETRACK_BACKUP_DIR/$newest"

query() { docker exec "$container" psql -U sidetrack -d sidetrack -Atc "$1"; }

STEP="checking the schema head"
expected="$(cat "$SIDETRACK_BACKUP_DIR/$newest.head")"
if [ -z "$expected" ] || [ "$(query 'select version_num from alembic_version')" != "$expected" ]; then
  echo "$JOB: restored schema head does not match the backup's" >&2
  exit 1
fi

STEP="checking restored records"
for table in weeks users; do
  if [ "$(query "select count(*) from $table")" -eq 0 ]; then
    echo "$JOB: restored $table table is empty" >&2
    exit 1
  fi
done

log "restored $newest"
heartbeat "${SIDETRACK_RESTORE_HEARTBEAT_URL:-}"
