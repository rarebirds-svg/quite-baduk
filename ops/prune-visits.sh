#!/usr/bin/env bash
# launchd가 매일 호출 — 180일 초과 visit_hits 방문 로그를 정리한다.
set -euo pipefail
# launchd는 로그인 셸 PATH를 상속하지 않는다 — Homebrew 경로를 명시적으로 앞에 붙인다.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT/backend"
[ -f "$HOME/.baduk.env" ] && { set -a; . "$HOME/.baduk.env"; set +a; }

RUNLOG="$ROOT/docs/ops/state/log/prune-visits-runs.log"
mkdir -p "$(dirname "$RUNLOG")"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] prune-visits 시작" >> "$RUNLOG"
.venv311/bin/python -m scripts.prune_visits >> "$RUNLOG" 2>&1 \
  || echo "[$(date '+%Y-%m-%d %H:%M:%S')] 비정상 종료" >> "$RUNLOG"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] prune-visits 종료" >> "$RUNLOG"
