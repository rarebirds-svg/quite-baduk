#!/usr/bin/env bash
# launchd가 매일 12시·18시 호출 — 오케스트레이터 프롬프트로 헤드리스 Claude Code를 1회 실행.
set -euo pipefail
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT"

[ -f ops/ops.env ] && { set -a; . ops/ops.env; set +a; }

mkdir -p docs/ops/state/log
RUNLOG="docs/ops/state/log/orchestrator-runs.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] orchestrator 시작" >> "$RUNLOG"

# 헤드리스 실행. 무인 스케줄이라 권한 프롬프트가 불가능 — 가드레일은
# autonomy-policy.md(🟡 액션은 Telegram 승인)이지 OS 권한창이 아니다.
/opt/homebrew/bin/claude -p "$(cat docs/ops/orchestrator-prompt.md)" \
  --dangerously-skip-permissions \
  >> "$RUNLOG" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] 비정상 종료" >> "$RUNLOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] orchestrator 종료" >> "$RUNLOG"
