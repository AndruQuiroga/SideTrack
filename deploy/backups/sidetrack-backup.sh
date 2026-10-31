#!/usr/bin/env bash
# Daily database backup, run by sidetrack-backup.timer on the database node.
JOB="sidetrack-backup"
. "$(dirname "$(readlink -f "$0")")/backup-lib.sh"

: "${SIDETRACK_BACKUP_DIR:?set SIDETRACK_BACKUP_DIR}"
: "${SIDETRACK_BACKUP_MOUNT:?set SIDETRACK_BACKUP_MOUNT}"

require_backup_mount

STEP="finding the database container"
db="$(docker ps -q --filter 'name=^sidetrack_db\.')"
if [ -z "$db" ] || [ "$(wc -l <<<"$db")" -ne 1 ]; then
  echo "$JOB: expected one local sidetrack_db container" >&2
  exit 1
fi

name="sidetrack-daily-$(date -u +%Y%m%dT%H%M%SZ).dump"
target="$SIDETRACK_BACKUP_DIR/$name"
partial="$target.partial"
cleanup() { rm -f "$partial" "$target.sha256.partial" "$target.head.partial"; }

STEP="recording the schema head"
docker exec "$db" psql -U sidetrack -d sidetrack -Atc \
  'select version_num from alembic_version' >"$target.head.partial"

STEP="dumping the database"
docker exec "$db" pg_dump -U sidetrack -d sidetrack -Fc >"$partial"
if [ ! -s "$partial" ]; then
  echo "$JOB: the dump is empty" >&2
  exit 1
fi
sync "$partial"

STEP="recording the checksum"
(cd "$SIDETRACK_BACKUP_DIR" && sha256sum "$name.partial") |
  sed "s/\.partial\$//" >"$target.sha256.partial"

STEP="publishing the backup"
mv "$target.head.partial" "$target.head"
mv "$target.sha256.partial" "$target.sha256"
mv "$partial" "$target"
log "wrote $name"

STEP="applying retention"
kept="$(kept_backups)"
while read -r old; do
  [ -n "$old" ] || continue
  if ! grep -qxF "$old" <<<"$kept"; then
    rm -f "$SIDETRACK_BACKUP_DIR/$old" "$SIDETRACK_BACKUP_DIR/$old.sha256" \
      "$SIDETRACK_BACKUP_DIR/$old.head"
    log "removed $old"
  fi
done < <(scheduled_backups)

heartbeat "${SIDETRACK_BACKUP_HEARTBEAT_URL:-}"
