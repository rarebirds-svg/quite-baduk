#!/usr/bin/env bash
# 잡이 자기 실행 결과 1건을 state/jobs/<job>.json에 덮어쓴다 — 다이제스트가 읽는 기계용 입력.
set -euo pipefail

JOB="${1:-}"
STATUS="${2:-}"
SUMMARY="${3:-}"

if [ -z "$JOB" ] || [ -z "$STATUS" ] || [ -z "$SUMMARY" ]; then
  echo "usage: report-job-status.sh <job> <ok|warn|fail> <summary>" >&2
  exit 2
fi
case "$STATUS" in
  ok|warn|fail) ;;
  *) echo "report-job-status: status는 ok|warn|fail만 허용 — '$STATUS'" >&2; exit 2 ;;
esac

ROOT="${ROOT:-/Users/daegong/projects/baduk}"
DIR="$ROOT/docs/ops/state/jobs"
mkdir -p "$DIR"

JOB="$JOB" STATUS="$STATUS" SUMMARY="$SUMMARY" OUT="$DIR/$JOB.json" python3 -c "
import json, os
from datetime import datetime, timedelta, timezone
with open(os.environ['OUT'], 'w', encoding='utf-8') as f:
    json.dump({
        'job': os.environ['JOB'],
        'status': os.environ['STATUS'],
        'summary': os.environ['SUMMARY'],
        'at': datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds'),
    }, f, ensure_ascii=False)
    f.write('\n')
"
