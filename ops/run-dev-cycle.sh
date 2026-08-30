#!/usr/bin/env bash
# launchd가 매일 04:30 호출 — 자율 버그 사이클 프롬프트로 헤드리스 Claude Code를 1회 실행.
set -euo pipefail
# launchd는 로그인 셸 PATH를 상속하지 않는다 — Homebrew 경로(gh·claude 등)를 명시적으로 앞에 붙인다.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT"

[ -f ops/ops.env ] && { set -a; . ops/ops.env; set +a; }

mkdir -p docs/ops/state/log
RUNLOG="docs/ops/state/log/dev-cycle-runs.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] dev-cycle 시작" >> "$RUNLOG"

# 세션 한도로 죽으면 리셋 시각 이후 1회 재시도한다 (ops/lib/session-retry.sh).
. ops/lib/session-retry.sh
run_claude_with_session_retry "$RUNLOG" \
  /opt/homebrew/bin/claude -p "$(cat docs/ops/dev-cycle-prompt.md)" \
  --dangerously-skip-permissions \
  --channels plugin:telegram@claude-plugins-official \
  || echo "[$(date '+%Y-%m-%d %H:%M:%S')] 비정상 종료" >> "$RUNLOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] dev-cycle 종료" >> "$RUNLOG"
