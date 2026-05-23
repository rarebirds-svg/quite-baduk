#!/usr/bin/env bash
# launchd가 매주 일요일 09:00 호출 — 주간 분석 리포트 헤드리스 Claude를 1회 실행.
set -euo pipefail
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT"

[ -f ops/ops.env ] && { set -a; . ops/ops.env; set +a; }

mkdir -p docs/ops/state/log docs/ops/state/reports
RUNLOG="docs/ops/state/log/analytics-weekly-runs.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] analytics-weekly 시작" >> "$RUNLOG"

/opt/homebrew/bin/claude -p "$(cat docs/ops/analytics-prompt.md)" \
  --dangerously-skip-permissions \
  --channels plugin:telegram@claude-plugins-official \
  >> "$RUNLOG" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] 비정상 종료" >> "$RUNLOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] analytics-weekly 종료" >> "$RUNLOG"
