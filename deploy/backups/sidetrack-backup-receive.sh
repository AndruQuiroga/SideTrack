#!/usr/bin/env bash
# Forced SSH command on the second host: the copy key can run only list, put and keep.
set -euo pipefail
umask 077

: "${SIDETRACK_RECEIVE_DIR:?set SIDETRACK_RECEIVE_DIR}"
PATTERN='^sidetrack-daily-[0-9]{8}T[0-9]{6}Z\.dump$'

read -r -a request <<<"${SSH_ORIGINAL_COMMAND:-}"
command="${request[0]:-}"

valid_name() { [[ "$1" =~ $PATTERN ]]; }

case "$command" in
  list)
    { ls -1 "$SIDETRACK_RECEIVE_DIR" || true; } | { grep -E "$PATTERN" || true; }
    ;;
  put)
    name="${request[1]:-}"
    sha256="${request[2]:-}"
    valid_name "$name" && [[ "$sha256" =~ ^[0-9a-f]{64}$ ]] || {
      echo "invalid put request" >&2
      exit 2
    }
    partial="$SIDETRACK_RECEIVE_DIR/$name.partial"
    trap 'rm -f "$partial"' EXIT
    cat >"$partial"
    if [ "$(sha256sum "$partial" | cut -d' ' -f1)" != "$sha256" ]; then
      echo "checksum mismatch for $name" >&2
      exit 1
    fi
    sync "$partial"
    echo "$sha256  $name" >"$SIDETRACK_RECEIVE_DIR/$name.sha256"
    mv "$partial" "$SIDETRACK_RECEIVE_DIR/$name"
    ;;
  keep)
    kept="$(cat)"
    if [ -z "$kept" ]; then
      echo "refusing to remove every backup" >&2
      exit 2
    fi
    while read -r name; do
      if [ -n "$name" ] && ! grep -qxF "$name" <<<"$kept"; then
        rm -f "$SIDETRACK_RECEIVE_DIR/$name" "$SIDETRACK_RECEIVE_DIR/$name.sha256"
      fi
    done < <({ ls -1 "$SIDETRACK_RECEIVE_DIR" || true; } | { grep -E "$PATTERN" || true; })
    ;;
  *)
    echo "unsupported command" >&2
    exit 2
    ;;
esac
