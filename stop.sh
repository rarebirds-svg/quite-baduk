#!/usr/bin/env bash
# 네이티브 스택 종료. start.sh가 .run/{backend,web}.pid에 기록한 PID를
# 자식 프로세스(uvicorn → reloader, npm → next-server)까지 함께 종료합니다.
set -euo pipefail
cd "$(dirname "$0")"

RUN_DIR="$(pwd)/.run"
BACKEND_PID_FILE="${RUN_DIR}/backend.pid"
WEB_PID_FILE="${RUN_DIR}/web.pid"

stop_tree() {
  local label="$1"
  local pid_file="$2"

  if [ ! -f "${pid_file}" ]; then
    echo "${label}: PID 파일이 없습니다 (이미 종료됨)."
    return 0
  fi

  local pid
  pid=$(cat "${pid_file}")

  if ! kill -0 "${pid}" 2>/dev/null; then
    echo "${label}: PID ${pid} 프로세스가 없습니다 (이미 종료됨)."
    rm -f "${pid_file}"
    return 0
  fi

  echo "${label}: PID ${pid} 트리에 SIGTERM 송신..."
  # 자식 먼저, 부모 나중에. SIGTERM 후 10초 대기, 그래도 살아있으면 SIGKILL.
  # (uvicorn --reload reloader / next dev 는 SIGTERM 처리가 다소 느림)
  pkill -TERM -P "${pid}" 2>/dev/null || true
  kill -TERM "${pid}" 2>/dev/null || true

  for _ in $(seq 1 10); do
    if ! kill -0 "${pid}" 2>/dev/null; then
      break
    fi
    sleep 1
  done

  if kill -0 "${pid}" 2>/dev/null; then
    echo "${label}: 10초 내 종료되지 않아 SIGKILL."
    pkill -KILL -P "${pid}" 2>/dev/null || true
    kill -KILL "${pid}" 2>/dev/null || true
  fi

  rm -f "${pid_file}"
  echo "${label}: 종료 완료."
}

stop_tree "backend" "${BACKEND_PID_FILE}"
stop_tree "web" "${WEB_PID_FILE}"

# 혹시 모를 잔여 프로세스(포트 점유) 정리.
for port in 8000 3000; do
  pids=$(lsof -ti :${port} 2>/dev/null || true)
  if [ -n "${pids}" ]; then
    echo "포트 ${port} 잔여 프로세스 정리: ${pids}"
    # shellcheck disable=SC2086
    kill -TERM ${pids} 2>/dev/null || true
  fi
done

echo "모든 네이티브 스택을 종료했습니다."
