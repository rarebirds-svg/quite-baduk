#!/usr/bin/env bash
# 네이티브 개발 스택 부트스트랩 (Docker 미사용).
# 백엔드(uvicorn)와 프론트엔드(next dev)를 백그라운드로 실행하고,
# 헬스체크 후 브라우저를 열고 로그를 tail 합니다.
# Ctrl+C로 tail에서 빠져나와도 두 프로세스는 계속 실행됩니다. 종료는 ./stop.sh
set -euo pipefail
cd "$(dirname "$0")"

ROOT="$(pwd)"
RUN_DIR="${ROOT}/.run"
mkdir -p "${RUN_DIR}"

BACKEND_PID_FILE="${RUN_DIR}/backend.pid"
WEB_PID_FILE="${RUN_DIR}/web.pid"
BACKEND_LOG="${RUN_DIR}/backend.log"
WEB_LOG="${RUN_DIR}/web.log"

# ─── 1. 이미 실행 중인 프로세스 체크 ─────────────────────────
is_alive() {
  local pid_file="$1"
  [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

if is_alive "$BACKEND_PID_FILE" || is_alive "$WEB_PID_FILE"; then
  echo "이미 실행 중인 프로세스가 있습니다. 먼저 ./stop.sh로 종료해 주세요." >&2
  exit 1
fi

if lsof -ti :8000 >/dev/null 2>&1; then
  echo "포트 8000이 이미 사용 중입니다. 점유 프로세스를 종료한 뒤 다시 시도하세요." >&2
  exit 1
fi
if lsof -ti :3000 >/dev/null 2>&1; then
  echo "포트 3000이 이미 사용 중입니다. 점유 프로세스를 종료한 뒤 다시 시도하세요." >&2
  exit 1
fi

# ─── 2. backend/.env 부트스트랩 ──────────────────────────────
if [ ! -f "${ROOT}/backend/.env" ]; then
  if [ -f "${ROOT}/backend/.env.example" ]; then
    cp "${ROOT}/backend/.env.example" "${ROOT}/backend/.env"
    echo "backend/.env 가 없어서 backend/.env.example로부터 생성했습니다."
  else
    echo "backend/.env.example 가 없습니다. backend 환경 설정을 확인해 주세요." >&2
    exit 1
  fi
fi

# ─── 3. 의존성 사전 점검 ──────────────────────────────────────
if [ ! -x "${ROOT}/backend/.venv311/bin/uvicorn" ]; then
  echo "backend/.venv311 에 uvicorn이 설치되어 있지 않습니다." >&2
  echo "  cd backend && python3.11 -m venv .venv311 && source .venv311/bin/activate && pip install -e '.[dev]'" >&2
  exit 1
fi
if [ ! -d "${ROOT}/web/node_modules" ]; then
  echo "web/node_modules 가 없습니다. 'cd web && npm install' 후 다시 시도하세요." >&2
  exit 1
fi

# ─── 4. 백엔드 기동 (uvicorn --reload) ────────────────────────
echo "백엔드(uvicorn)를 기동합니다..."
(
  cd "${ROOT}/backend"
  # shellcheck disable=SC1091
  source .venv311/bin/activate
  exec nohup .venv311/bin/uvicorn app.main:app \
    --host 127.0.0.1 --port 8000 --reload \
    >>"${BACKEND_LOG}" 2>&1
) &
echo $! > "${BACKEND_PID_FILE}"

# ─── 5. 프론트엔드 기동 (next dev) ────────────────────────────
echo "프론트엔드(next dev)를 기동합니다..."
(
  cd "${ROOT}/web"
  exec nohup npm run dev >>"${WEB_LOG}" 2>&1
) &
echo $! > "${WEB_PID_FILE}"

# ─── 6. 헬스 체크 (최대 60초) ────────────────────────────────
echo -n "스택 준비를 기다리는 중"
ready=0
for _ in $(seq 1 60); do
  if curl -fs http://localhost:8000/api/health >/dev/null 2>&1 \
     && curl -fs http://localhost:3000 >/dev/null 2>&1; then
    ready=1
    break
  fi
  echo -n "."
  sleep 1
done
echo

if [ "$ready" -ne 1 ]; then
  echo "스택이 60초 안에 준비되지 않았습니다. 로그를 확인하세요:" >&2
  echo "  tail -f ${BACKEND_LOG} ${WEB_LOG}" >&2
  exit 1
fi

echo "준비 완료. 브라우저를 엽니다: http://localhost:3000"
open http://localhost:3000 2>/dev/null || true

echo "로그를 따라갑니다. Ctrl+C로 빠져나와도 백엔드/프론트는 계속 실행됩니다. 종료는 ./stop.sh"
exec tail -n 0 -F "${BACKEND_LOG}" "${WEB_LOG}"
