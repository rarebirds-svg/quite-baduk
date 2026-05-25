#!/usr/bin/env bash
# launchd가 1시간마다 호출 — check-staleness.sh를 한 번 실행한다.
set -euo pipefail
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT"
[ -f ops/ops.env ] && { set -a; . ops/ops.env; set +a; }
exec ops/check-staleness.sh
