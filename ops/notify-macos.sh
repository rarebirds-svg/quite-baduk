#!/usr/bin/env bash
# macOS 로컬 알림(osascript)을 띄운다. Telegram 실패 시 last-resort 채널.
set -euo pipefail

MSG="${1:-}"
if [ -z "$MSG" ]; then
  echo "usage: notify-macos.sh <message>" >&2
  exit 2
fi

# osascript 인자 escape — 작은따옴표/큰따옴표 모두 안전하게.
escaped=$(printf '%s' "$MSG" | sed 's/"/\\"/g')
osascript -e "display notification \"$escaped\" with title \"inkbaduk watchdog\""
