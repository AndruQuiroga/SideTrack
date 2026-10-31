#!/usr/bin/env bash
# Copies backups to a second host, retrying whatever is missing there.
JOB="sidetrack-backup-copy"
. "$(dirname "$(readlink -f "$0")")/backup-lib.sh"

: "${SIDETRACK_BACKUP_DIR:?set SIDETRACK_BACKUP_DIR}"
: "${SIDETRACK_BACKUP_MOUNT:?set SIDETRACK_BACKUP_MOUNT}"
: "${SIDETRACK_COPY_TARGET:?set SIDETRACK_COPY_TARGET}"
SIDETRACK_COPY_KEY="${SIDETRACK_COPY_KEY:-/etc/sidetrack/backup-copy-key}"

remote() {
  ssh -i "$SIDETRACK_COPY_KEY" -o BatchMode=yes -o ConnectTimeout=10 -o IdentitiesOnly=yes \
    "$SIDETRACK_COPY_TARGET" "$@"
}

require_backup_mount

STEP="listing the second host"
copied="$(remote list)"

copies=0
while read -r name; do
  [ -n "$name" ] || continue
  if grep -qxF "$name" <<<"$copied"; then
    continue
  fi
  STEP="verifying $name"
  (cd "$SIDETRACK_BACKUP_DIR" && sha256sum --check --status "$name.sha256")
  STEP="copying $name"
  sha256="$(cut -d' ' -f1 "$SIDETRACK_BACKUP_DIR/$name.sha256")"
  remote put "$name" "$sha256" <"$SIDETRACK_BACKUP_DIR/$name"
  copies=$((copies + 1))
done < <(scheduled_backups)
log "copied $copies backups"

STEP="applying retention on the second host"
kept="$(kept_backups)"
if [ -n "$kept" ]; then
  remote keep <<<"$kept"
fi

heartbeat "${SIDETRACK_COPY_HEARTBEAT_URL:-}"
