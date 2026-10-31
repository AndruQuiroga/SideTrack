#!/usr/bin/env bash
# Shared by the Sidetrack backup jobs. See deploy/README.md.
set -euo pipefail
umask 077

SIDETRACK_BACKUP_ENV="${SIDETRACK_BACKUP_ENV:-/etc/sidetrack/backup.env}"
if [ -r "$SIDETRACK_BACKUP_ENV" ]; then
  # shellcheck disable=SC1090
  . "$SIDETRACK_BACKUP_ENV"
fi

BACKUP_PATTERN='^sidetrack-daily-[0-9]{8}T[0-9]{6}Z\.dump$'
STEP="startup"

log() { echo "$JOB: $*"; }

cleanup() { :; }

finish() {
  local status=$?
  cleanup || true
  if [ "$status" -ne 0 ]; then
    echo "$JOB: failed during $STEP" >&2
  fi
  exit "$status"
}
trap finish EXIT

require_backup_mount() {
  STEP="checking the backup mount"
  local mount
  mount="$(findmnt -n -o TARGET -T "$SIDETRACK_BACKUP_DIR")"
  if [ "$mount" != "$SIDETRACK_BACKUP_MOUNT" ]; then
    echo "$JOB: backup directory is on $mount, expected $SIDETRACK_BACKUP_MOUNT" >&2
    return 1
  fi
}

# Newest first. Prints nothing when the directory holds no scheduled backups.
scheduled_backups() {
  { ls -1 "$SIDETRACK_BACKUP_DIR" 2>/dev/null || true; } | { grep -E "$BACKUP_PATTERN" || true; } |
    sort -r
}

# The newest backup of each of the last 7 days, 4 ISO weeks and 6 months.
kept_backups() {
  declare -A days=() weeks=() months=()
  local name day week month keep
  while read -r name; do
    [ -n "$name" ] || continue
    day="${name:16:8}"
    week="$(date -u -d "$day" +%G%V)"
    month="${day:0:6}"
    keep=0
    if [ -z "${days[$day]:-}" ] && [ "${#days[@]}" -lt 7 ]; then
      days[$day]=1
      keep=1
    fi
    if [ -z "${weeks[$week]:-}" ] && [ "${#weeks[@]}" -lt 4 ]; then
      weeks[$week]=1
      keep=1
    fi
    if [ -z "${months[$month]:-}" ] && [ "${#months[@]}" -lt 6 ]; then
      months[$month]=1
      keep=1
    fi
    if [ "$keep" -eq 1 ]; then
      echo "$name"
    fi
  done < <(scheduled_backups)
}

# Sent only after a job succeeds; a missing heartbeat is what raises the alert.
heartbeat() {
  local url="${1:-}"
  if [ -z "$url" ]; then
    log "no heartbeat configured"
  elif ! curl -fsS -m 10 -o /dev/null "$url" >/dev/null 2>&1; then
    log "heartbeat was not delivered"
  fi
}
