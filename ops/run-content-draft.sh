#!/usr/bin/env bash
# launchd가 매주 토요일 02:00 호출 — 콘텐츠 초안 헤드리스 Claude를 1회 실행.
set -euo pipefail
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT"

[ -f ops/ops.env ] && { set -a; . ops/ops.env; set +a; }

mkdir -p docs/ops/state/log
RUNLOG="docs/ops/state/log/content-draft-runs.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] content-draft 시작" >> "$RUNLOG"

/opt/homebrew/bin/claude -p "$(cat docs/ops/content-draft-prompt.md)" \
  --dangerously-skip-permissions \
  --channels plugin:telegram@claude-plugins-official \
  >> "$RUNLOG" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] 비정상 종료" >> "$RUNLOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] content-draft 종료" >> "$RUNLOG"
