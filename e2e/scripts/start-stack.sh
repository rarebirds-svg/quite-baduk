#!/usr/bin/env bash
# e2e 테스트용 backend + web을 docker 없이 띄우는 스크립트. 로컬·CI 공용.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PID_DIR="$ROOT/e2e/.pids"
LOG_DIR="$ROOT/e2e/.logs"
mkdir -p "$PID_DIR" "$LOG_DIR"

API_PORT="${BADUK_API_PORT:-8000}"
WEB_PORT="${BADUK_WEB_PORT:-3000}"
WAIT_SECONDS="${BADUK_WAIT_SECONDS:-120}"

echo "[start-stack] booting backend on :$API_PORT, web on :$WEB_PORT"

# Backend — venv가 없으면 만든다. 이미 있으면 재사용.
(
  cd "$ROOT/backend"
  if [ ! -d .venv311 ]; then
    echo "[start-stack] creating backend .venv311"
    python3.11 -m venv .venv311
    source .venv311/bin/activate
    pip install -q -e ".[dev]"
  else
    source .venv311/bin/activate
  fi

  mkdir -p data
  export KATAGO_MOCK=true
  export DATABASE_URL="sqlite+aiosqlite:///./data/e2e-test.db"
  export JWT_SECRET="${JWT_SECRET:-e2e-test-secret-not-for-prod}"
  export CORS_ORIGINS="http://localhost:$WEB_PORT"
  # 9개 e2e 스펙이 동일 IP로 다수 세션을 생성하므로 rate limit 우회.
  export BADUK_E2E_RATE_LIMIT_DISABLED=true

  # 새 DB일 때 alembic 마이그레이션을 적용해 sessions 등 테이블을 만든다.
  alembic upgrade head

  exec uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT" --workers 1
) > "$LOG_DIR/backend.log" 2>&1 &
echo $! > "$PID_DIR/backend.pid"

# Web — node_modules가 없으면 ci 설치. dev 모드로 띄워 build 단계 생략.
(
  cd "$ROOT/web"
  if [ ! -d node_modules ]; then
    echo "[start-stack] installing web node_modules"
    npm ci --no-audit --no-fund > /dev/null
  fi
  export NEXT_PUBLIC_API_URL="http://localhost:$API_PORT"
  exec npx next dev -H 127.0.0.1 -p "$WEB_PORT"
) > "$LOG_DIR/web.log" 2>&1 &
echo $! > "$PID_DIR/web.pid"

# 헬스 대기.
deadline=$((SECONDS + WAIT_SECONDS))
until curl -fs "http://localhost:$API_PORT/api/health" >/dev/null 2>&1; do
  if (( SECONDS >= deadline )); then
    echo "[start-stack] backend not ready in ${WAIT_SECONDS}s — see $LOG_DIR/backend.log" >&2
    exit 1
  fi
  sleep 2
done
echo "[start-stack] backend ready"

until curl -fs "http://localhost:$WEB_PORT/" >/dev/null 2>&1; do
  if (( SECONDS >= deadline )); then
    echo "[start-stack] web not ready in ${WAIT_SECONDS}s — see $LOG_DIR/web.log" >&2
    exit 1
  fi
  sleep 2
done
echo "[start-stack] web ready"

echo "[start-stack] stack up. backend=$API_PORT web=$WEB_PORT"
