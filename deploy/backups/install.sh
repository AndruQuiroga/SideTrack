#!/usr/bin/env bash
# Run with sudo from a copy of deploy/backups.
#   sudo ./install.sh sender                     on the database node
#   sudo ./install.sh receiver DIR 'PUBLIC_KEY'  on the second host
set -euo pipefail
umask 022

SOURCE="$(dirname "$(readlink -f "$0")")"
LIB=/usr/local/lib/sidetrack-backup

install_scripts() {
  install -d -m 0755 "$LIB"
  install -m 0755 "$SOURCE"/*.sh "$LIB"/
}

install_sender() {
  install_scripts
  install -d -m 0700 /etc/sidetrack
  if [ ! -e /etc/sidetrack/backup.env ]; then
    install -m 0600 "$SOURCE/backup.env.example" /etc/sidetrack/backup.env
  fi
  if [ ! -e /etc/sidetrack/backup-copy-key ]; then
    ssh-keygen -q -t ed25519 -N '' -C sidetrack-backup-copy -f /etc/sidetrack/backup-copy-key
  fi
  install -m 0644 "$SOURCE"/*.service "$SOURCE"/*.timer /etc/systemd/system/
  systemctl daemon-reload
  echo "Fill in /etc/sidetrack/backup.env, then enable the timers:"
  echo "  systemctl enable --now sidetrack-backup.timer sidetrack-backup-copy.timer" \
    "sidetrack-restore-check.timer"
  echo "Copy key: $(cat /etc/sidetrack/backup-copy-key.pub)"
}

install_receiver() {
  local dir="$1" key="$2" home=/var/lib/sidetrack-backup
  install_scripts
  id -u sidetrack-backup >/dev/null 2>&1 ||
    useradd --system --home-dir "$home" --create-home --shell /bin/bash sidetrack-backup
  install -d -m 0700 -o sidetrack-backup -g sidetrack-backup "$dir" "$home/.ssh"
  local command="SIDETRACK_RECEIVE_DIR=$dir $LIB/sidetrack-backup-receive.sh"
  echo "command=\"$command\",restrict $key" >"$home/.ssh/authorized_keys"
  chown sidetrack-backup:sidetrack-backup "$home/.ssh/authorized_keys"
  chmod 0600 "$home/.ssh/authorized_keys"
}

case "${1:-}" in
  sender) install_sender ;;
  receiver) install_receiver "${2:?receive directory}" "${3:?public key}" ;;
  *)
    echo "usage: install.sh sender | receiver DIR 'PUBLIC_KEY'" >&2
    exit 2
    ;;
esac
