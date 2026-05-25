#!/usr/bin/env bash
# repo의 ops/launchd/*.plist를 ~/Library/LaunchAgents/에 동기화하고 launchd에 재등록한다.
set -euo pipefail

ROOT="/Users/daegong/projects/baduk"
SRC_DIR="$ROOT/ops/launchd"
DST_DIR="$HOME/Library/LaunchAgents"
LOG="$ROOT/docs/ops/state/log/launchd-sync.log"
CHECK_ONLY=0

if [[ "${1:-}" == "--check" ]]; then
  CHECK_ONLY=1
fi

mkdir -p "$DST_DIR" "$(dirname "$LOG")"

drift=0
for src in "$SRC_DIR"/com.inkbaduk.*.plist; do
  [ -f "$src" ] || continue
  name=$(basename "$src")
  dst="$DST_DIR/$name"
  label="${name%.plist}"

  if [ ! -f "$dst" ]; then
    echo "MISSING $name (not in $DST_DIR)"
    drift=1
    if [ "$CHECK_ONLY" -eq 0 ]; then
      cp "$src" "$dst"
      if ! launchctl bootstrap "gui/$(id -u)" "$dst"; then
        echo "ERROR: launchctl bootstrap failed for $name" >&2
        exit 1
      fi
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] installed $name" >> "$LOG"
    fi
    continue
  fi

  src_hash=$(shasum -a 256 "$src" | awk '{print $1}')
  dst_hash=$(shasum -a 256 "$dst" | awk '{print $1}')
  if [ "$src_hash" != "$dst_hash" ]; then
    echo "DRIFT $name (repo != installed)"
    drift=1
    if [ "$CHECK_ONLY" -eq 0 ]; then
      launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
      cp "$src" "$dst"
      if ! launchctl bootstrap "gui/$(id -u)" "$dst"; then
        echo "ERROR: launchctl bootstrap failed for $name" >&2
        exit 1
      fi
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] resynced $name" >> "$LOG"
    fi
  fi
done

if [ "$CHECK_ONLY" -eq 1 ] && [ "$drift" -ne 0 ]; then
  exit 1
fi
exit 0
