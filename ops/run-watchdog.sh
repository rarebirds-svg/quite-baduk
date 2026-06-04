#!/usr/bin/env bash
# launchd가 1시간마다 호출 — staleness + health 검사를 한 번씩 실행한다.
set -euo pipefail
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT"
[ -f ops/ops.env ] && { set -a; . ops/ops.env; set +a; }
ops/check-staleness.sh || echo "check-staleness 비정상 종료" >&2
ops/check-health.sh    || echo "check-health 비정상 종료" >&2
