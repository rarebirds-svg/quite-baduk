#!/usr/bin/env bash
# launchd가 매주 일요일 03:00 호출 — prod venv에서 CWI 자동 수집 스크립트를 실행.
set -euo pipefail
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT/backend"

# prod backend의 .env 환경(DB_PATH 등)을 사용한다.
[ -f "$HOME/.baduk.env" ] && { set -a; . "$HOME/.baduk.env"; set +a; }

mkdir -p "$ROOT/docs/ops/state/log"
RUNLOG="$ROOT/docs/ops/state/log/content-ingest-runs.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] content-ingest 시작" >> "$RUNLOG"

source .venv311/bin/activate
python -m scripts.ingest_cwi_weekly >> "$RUNLOG" 2>&1 \
  || echo "[$(date '+%Y-%m-%d %H:%M:%S')] 비정상 종료" >> "$RUNLOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] content-ingest 종료" >> "$RUNLOG"
