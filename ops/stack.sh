#!/usr/bin/env bash
# prod(launchd) 상태 조회와 staging 네이티브 스택 기동·중지를 담당하는 운영 래퍼.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

WORKTREE="$ROOT/.worktrees/staging"
RUN_DIR="$ROOT/.run"
ENVFILE="$ROOT/ops/staging.env"

usage() { echo "사용법: ops/stack.sh {up|down|ps} staging | ops/stack.sh {ps|restart} prod" >&2; exit 1; }

ACTION="${1:-}"; TARGET="${2:-}"
{ [ -z "$ACTION" ] || [ -z "$TARGET" ]; } && usage

# shellcheck disable=SC1090
[ -f "$ENVFILE" ] && { set -a; . "$ENVFILE"; set +a; }

staging_up() {
  [ -d "$WORKTREE" ] || { echo "staging worktree 없음. 계획 Task 3을 먼저 수행하세요." >&2; exit 1; }
  mkdir -p "$RUN_DIR" "$WORKTREE/backend/data"

  ( cd "$WORKTREE/backend"
    # shellcheck disable=SC1091
    source .venv311/bin/activate
    export DB_PATH KATAGO_MOCK JWT_SECRET CORS_ORIGINS
    alembic upgrade head >> "$RUN_DIR/staging-backend.log" 2>&1
    exec nohup uvicorn app.main:app --host 127.0.0.1 --port "$STAGING_BACKEND_PORT" \
      >> "$RUN_DIR/staging-backend.log" 2>&1
  ) & echo $! > "$RUN_DIR/staging-backend.pid"

  ( cd "$WORKTREE/web"
    export NEXT_PUBLIC_API_URL="http://localhost:$STAGING_BACKEND_PORT"
    exec nohup npm run dev -- -p "$STAGING_WEB_PORT" \
      >> "$RUN_DIR/staging-web.log" 2>&1
  ) & echo $! > "$RUN_DIR/staging-web.pid"

  echo "staging 기동 요청: backend :$STAGING_BACKEND_PORT, web :$STAGING_WEB_PORT"
  echo "준비까지 30~60초. 확인: ops/stack.sh ps staging"
}

staging_down() {
  for svc in backend web; do
    pf="$RUN_DIR/staging-$svc.pid"
    if [ -f "$pf" ] && kill -0 "$(cat "$pf")" 2>/dev/null; then
      kill "$(cat "$pf")" 2>/dev/null && echo "staging-$svc 중지"
    fi
    rm -f "$pf"
  done
  # next dev 는 자식 프로세스를 띄우므로 포트 기준으로도 정리한다.
  for port in "$STAGING_BACKEND_PORT" "$STAGING_WEB_PORT"; do
    pids="$(lsof -ti ":$port" 2>/dev/null || true)"
    [ -n "$pids" ] && kill $pids 2>/dev/null || true
  done
}

staging_ps() {
  for svc in backend web; do
    pf="$RUN_DIR/staging-$svc.pid"
    if [ -f "$pf" ] && kill -0 "$(cat "$pf")" 2>/dev/null; then
      echo "staging-$svc: 가동 (pid $(cat "$pf"))"
    else
      echo "staging-$svc: 중단됨"
    fi
  done
  curl -fs --max-time 10 "http://localhost:$STAGING_BACKEND_PORT/api/health" \
    && echo " <- staging backend health" || echo "staging backend health: 응답 없음"
}

prod_ps() {
  launchctl list | grep -E 'com\.baduk\.(api|web)' || echo "launchd: com.baduk.* 미등록"
  curl -fs --max-time 10 "http://localhost:8000/api/health" \
    && echo " <- prod backend health" || echo "prod backend health: 응답 없음"
  curl -fs --max-time 10 "http://localhost:3000" >/dev/null \
    && echo "prod web :3000 OK" || echo "prod web :3000 응답 없음"
}

prod_restart() {
  local uid; uid="$(id -u)"
  for svc in com.baduk.api com.baduk.web; do
    launchctl kickstart -k "gui/$uid/$svc"
    echo "$svc 재시작 요청"
  done
  echo "기동 대기 20초..."
  sleep 20
  prod_ps
}

case "$ACTION/$TARGET" in
  up/staging)   staging_up ;;
  down/staging) staging_down ;;
  ps/staging)   staging_ps ;;
  ps/prod)      prod_ps ;;
  restart/prod) prod_restart ;;
  *)            usage ;;
esac
