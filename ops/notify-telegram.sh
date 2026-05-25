#!/usr/bin/env bash
# Telegram Bot API로 메시지를 보낸다. 토큰/채팅ID 없거나 non-2xx면 비0 종료(상위 fallback 트리거).
set -euo pipefail

MSG="${1:-}"
if [ -z "$MSG" ]; then
  echo "usage: notify-telegram.sh <message>" >&2
  exit 2
fi

ROOT="/Users/daegong/projects/baduk"
[ -f "$ROOT/ops/ops.env" ] && { set -a; . "$ROOT/ops/ops.env"; set +a; }
# Telegram bot token의 진실 공급원은 ~/.claude/channels/telegram/.env (plugin 관리).
[ -f "$HOME/.claude/channels/telegram/.env" ] && { set -a; . "$HOME/.claude/channels/telegram/.env"; set +a; }

: "${TELEGRAM_BOT_TOKEN:=}"
: "${TELEGRAM_CHAT_ID:=}"

if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
  echo "notify-telegram: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing" >&2
  exit 1
fi

http_code=$(curl -s -o /tmp/notify-telegram.out -w "%{http_code}" \
  --max-time 10 \
  -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_CHAT_ID}" \
  --data-urlencode "text=${MSG}")

if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
  exit 0
fi
echo "notify-telegram: HTTP $http_code" >&2
cat /tmp/notify-telegram.out >&2 2>/dev/null || true
exit 1
