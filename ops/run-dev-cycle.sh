#!/usr/bin/env bash
# launchd가 매일 02:00 호출 — 자율 버그 사이클 프롬프트로 헤드리스 Claude Code를 1회 실행.
set -euo pipefail
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT"

[ -f ops/ops.env ] && { set -a; . ops/ops.env; set +a; }

mkdir -p docs/ops/state/log
RUNLOG="docs/ops/state/log/dev-cycle-runs.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] dev-cycle 시작" >> "$RUNLOG"

/opt/homebrew/bin/claude -p "$(cat docs/ops/dev-cycle-prompt.md)" \
  --dangerously-skip-permissions \
  --channels plugin:telegram@claude-plugins-official \
  >> "$RUNLOG" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] 비정상 종료" >> "$RUNLOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] dev-cycle 종료" >> "$RUNLOG"
