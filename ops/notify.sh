#!/usr/bin/env bash
# 알림 채널 다중화 진입점 — Telegram → macOS notification 순으로 시도, 첫 성공에서 멈춤.
set -euo pipefail

MSG="${1:-}"
if [ -z "$MSG" ]; then
  echo "usage: notify.sh <message>" >&2
  exit 2
fi

ROOT="/Users/daegong/projects/baduk"

if "$ROOT/ops/notify-telegram.sh" "$MSG" 2>/dev/null; then
  exit 0
fi

if "$ROOT/ops/notify-macos.sh" "$MSG" 2>/dev/null; then
  exit 0
fi

echo "notify: all channels failed for: $MSG" >&2
exit 1
