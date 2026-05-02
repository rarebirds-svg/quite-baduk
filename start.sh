#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# 1. Docker daemon check
if ! docker info >/dev/null 2>&1; then
  echo "Docker Desktop이 실행 중이 아닙니다. Docker Desktop을 먼저 실행해 주세요." >&2
  exit 1
fi

# 2. .env bootstrap
if [ ! -f .env ]; then
  cp .env.example .env
  echo ".env 파일이 없어서 .env.example로부터 생성했습니다."
fi

# 3. Compose up
echo "Docker 스택을 빌드하고 띄웁니다..."
docker compose up --build -d

# 4. Health wait (max 60s)
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
  echo "스택이 60초 안에 준비되지 않았습니다. 'docker compose logs'로 확인하세요." >&2
  exit 1
fi

echo "준비 완료. 브라우저를 엽니다: http://localhost:3000"

# 5. Browser open (macOS)
open http://localhost:3000 || true

# 6. Tail logs (Ctrl+C exits the tail, containers keep running; use ./stop.sh to stop)
echo "로그를 따라갑니다. Ctrl+C로 빠져나와도 컨테이너는 계속 실행됩니다. 종료는 ./stop.sh"
exec docker compose logs -f
