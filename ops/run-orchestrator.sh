#!/usr/bin/env bash
# launchd가 매일 09시·21시 호출 — 오케스트레이터 프롬프트로 헤드리스 Claude Code를 1회 실행.
set -euo pipefail
# launchd는 로그인 셸 PATH를 상속하지 않는다 — Homebrew 경로(gh·claude 등)를 명시적으로 앞에 붙인다.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT"

[ -f ops/ops.env ] && { set -a; . ops/ops.env; set +a; }

mkdir -p docs/ops/state/log
RUNLOG="docs/ops/state/log/orchestrator-runs.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] orchestrator 시작" >> "$RUNLOG"

# 헤드리스 실행(공용 러너, 타임아웃 가드 포함). 무인 스케줄이라 권한 프롬프트가
# 불가능 — 가드레일은 autonomy-policy.md(🟡 액션은 Telegram 승인)이지 OS 권한창이
# 아니다. Telegram 플러그인 도구가 없으면 오케스트레이터가 curl Bot API로 폴백한다.
ops/claude-headless.sh docs/ops/orchestrator-prompt.md \
  >> "$RUNLOG" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] 비정상 종료" >> "$RUNLOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] orchestrator 종료" >> "$RUNLOG"
