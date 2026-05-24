#!/usr/bin/env bash
# start-stack.sh가 띄운 backend·web을 PID 파일 기준으로 종료한다.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PID_DIR="$ROOT/e2e/.pids"

for name in backend web; do
  pidfile="$PID_DIR/$name.pid"
  if [ -f "$pidfile" ]; then
    pid="$(cat "$pidfile")"
    if kill -0 "$pid" 2>/dev/null; then
      # 자식 프로세스(uvicorn worker, next dev child)까지 함께 종료.
      pkill -P "$pid" 2>/dev/null || true
      kill "$pid" 2>/dev/null || true
      sleep 1
      kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
      echo "[stop-stack] $name stopped (pid $pid)"
    fi
    rm -f "$pidfile"
  fi
done
