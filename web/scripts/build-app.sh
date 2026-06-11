#!/usr/bin/env bash
# 앱 셸(Capacitor) 정적 export 빌드 — 웹 전용 라우트를 임시 제외하고 next build를 돌린다.
set -euo pipefail

WEB_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WEB_DIR"

# 웹 전용(앱 제외) 라우트·파일. export를 깨뜨리는 force-dynamic/동적 세그먼트 포함.
EXCLUDES=(
  "app/admin" "app/dev" "app/support" "app/supporters"
  "app/faq" "app/glossary"
  "app/spectate/picks" "app/spectate/themes"
  "app/spectate/[id]" "app/spectate/pro/[id]"
  "app/game/play/[id]" "app/game/review/[id]"
  "app/sitemap.ts" "app/robots.ts"
)

STASH="$WEB_DIR/.app-shell-excluded"
rm -rf "$STASH"

restore() {
  set +e
  cd "$WEB_DIR"
  for p in "${EXCLUDES[@]}"; do
    if [ -e "$STASH/$p" ]; then
      mkdir -p "$(dirname "$p")"
      rm -rf "$p"
      mv "$STASH/$p" "$p"
    fi
  done
  rm -rf "$STASH"
}
trap restore EXIT

for p in "${EXCLUDES[@]}"; do
  if [ -e "$p" ]; then
    mkdir -p "$STASH/$(dirname "$p")"
    mv "$p" "$STASH/$p"
  fi
done

BUILD_TARGET=app \
NEXT_PUBLIC_APP_SHELL=1 \
NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-https://inkbaduk.com}" \
NEXT_PUBLIC_WS_URL="${NEXT_PUBLIC_WS_URL:-wss://inkbaduk.com}" \
npx next build

echo "✔ app shell export → $WEB_DIR/out"
