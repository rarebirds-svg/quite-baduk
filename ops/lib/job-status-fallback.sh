#!/usr/bin/env bash
# 래퍼 단계 실패로 잡이 상태를 못 남겼을 때 job json에 fail을 대신 기록하는 공용 헬퍼 (run-*.sh가 source).

# 비정상 종료한 잡이 이번 실행 중(start_epoch 이후) json을 갱신하지 않았으면 fail을 대신 남긴다.
# $1=잡 이름, $2=실행 시작 epoch. 기록 실패는 무시하고 항상 0 — set -e 래퍼의 종료 마커를 막지 않는다.
report_fail_if_unreported() {
  local job="$1" start="$2"
  local root="${ROOT:-/Users/daegong/projects/baduk}"
  local json="$root/docs/ops/state/jobs/$job.json"
  if [ -f "$json" ] && [ "$(stat -f %m "$json")" -ge "$start" ]; then
    return 0
  fi
  ROOT="$root" bash "$(dirname "${BASH_SOURCE[0]}")/../report-job-status.sh" "$job" fail \
    "래퍼 비정상 종료 — 실행 중 상태 보고 없음 ($job-runs.log 참조)" >/dev/null 2>&1 || true
  return 0
}
