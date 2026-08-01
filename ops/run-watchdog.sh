#!/usr/bin/env bash
# launchd가 1시간마다 호출 — staleness + health 검사를 한 번씩 실행한다.
set -euo pipefail
# launchd는 로그인 셸 PATH를 상속하지 않는다 — Homebrew 경로(gh·claude 등)를 명시적으로 앞에 붙인다.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT"
[ -f ops/ops.env ] && { set -a; . ops/ops.env; set +a; }
ops/check-staleness.sh || echo "check-staleness 비정상 종료" >&2
ops/check-health.sh    || echo "check-health 비정상 종료" >&2
