#!/usr/bin/env bash
# check-staleness.sh의 stale 판정을 임시 ROOT의 픽스처 로그로 검증한다.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET="$REPO/ops/check-staleness.sh"

pass=0
fail=0

now=$(date +%s)
ts_ago() {  # ts_ago <초 전> → "YYYY-MM-DD HH:MM:SS"
  date -r $(( now - $1 )) '+%Y-%m-%d %H:%M:%S'
}

# 모든 잡을 "방금 성공"으로 채운 픽스처 ROOT를 만든다. 개별 케이스는 한 잡만 덮어쓴다.
make_fixture() {
  local root
  root=$(mktemp -d -t staleness-fixture)
  mkdir -p "$root/docs/ops/state/log"
  local logdir="$root/docs/ops/state/log"
  local recent
  recent=$(ts_ago 600)
  for job in orchestrator dev-cycle content-draft content-ingest analytics-weekly; do
    {
      echo "[$recent] $job 시작"
      echo "[$recent] $job 종료"
    } > "$logdir/$job-runs.log"
  done
  {
    echo "[$recent] backup 시작"
    echo "[$recent] backup 완료"
  } > "$logdir/backup.out.log"
  echo "$root"
}

# 이 케이스에서 incident가 난 잡 이름들을 개행 구분으로 출력한다.
detected_jobs() {
  local root="$1"
  ROOT="$root" bash "$TARGET" >/dev/null 2>&1
  local incidents="$root/docs/ops/state/incidents.md"
  [ -f "$incidents" ] || return 0
  grep -oE '^### WD-[0-9]+-[0-9]+ — [a-z-]+ stale' "$incidents" | awk '{print $4}'
}

check() {  # check <설명> <기대: yes|no> <잡이름> <감지결과>
  local desc="$1" expect="$2" job="$3" detected="$4"
  local got="no"
  echo "$detected" | grep -qx "$job" && got="yes"
  if [ "$got" = "$expect" ]; then
    echo "  ok — $desc"
    pass=$(( pass + 1 ))
  else
    echo "  FAIL — $desc (기대 stale=$expect, 실제 stale=$got)"
    fail=$(( fail + 1 ))
  fi
}

echo "1) 인증 실패로 즉시 종료한 잡 (마지막 성공은 임계 초과)"
# 회귀 대상. 실패 종료도 "[ts] dev-cycle 종료"를 남기므로 마지막 timestamp만 보면 방금 실행된 것처럼 보인다.
root=$(make_fixture)
{
  echo "[$(ts_ago 172800)] dev-cycle 시작"
  echo "[$(ts_ago 172800)] dev-cycle 종료"
  echo "[$(ts_ago 3600)] dev-cycle 시작"
  echo "Failed to authenticate: OAuth session expired and could not be refreshed"
  echo "[$(ts_ago 3540)] 비정상 종료"
  echo "[$(ts_ago 3540)] dev-cycle 종료"
} > "$root/docs/ops/state/log/dev-cycle-runs.log"
out=$(detected_jobs "$root")
check "실패 종료는 신선도를 갱신하지 않는다" yes dev-cycle "$out"
rm -rf "$root"

echo "2) 정상 성공 종료"
root=$(make_fixture)
out=$(detected_jobs "$root")
check "방금 성공한 잡은 stale이 아니다" no dev-cycle "$out"
check "backup 완료 마커도 성공으로 인정된다" no backup "$out"
rm -rf "$root"

echo "3) 실패 후 재실행이 성공한 경우"
root=$(make_fixture)
{
  echo "[$(ts_ago 172800)] dev-cycle 시작"
  echo "[$(ts_ago 172740)] 비정상 종료"
  echo "[$(ts_ago 172740)] dev-cycle 종료"
  echo "[$(ts_ago 600)] dev-cycle 시작"
  echo "[$(ts_ago 540)] dev-cycle 종료"
} > "$root/docs/ops/state/log/dev-cycle-runs.log"
out=$(detected_jobs "$root")
check "직전 실패는 이후 성공을 가리지 않는다" no dev-cycle "$out"
rm -rf "$root"

echo "4) 빈 로그"
root=$(make_fixture)
: > "$root/docs/ops/state/log/orchestrator-runs.log"
out=$(detected_jobs "$root")
check "로그가 비어 있으면 stale" yes orchestrator "$out"
rm -rf "$root"

echo "5) 잡 본문에 '비정상 종료' 문자열이 등장하는 경우"
# 사이클 요약문이 이 단어를 인용할 수 있다. timestamp 접두어가 없으면 마커가 아니다.
root=$(make_fixture)
{
  echo "[$(ts_ago 600)] orchestrator 시작"
  echo "check-staleness 비정상 종료 사례를 이슈 #70으로 등록했다."
  echo "[$(ts_ago 540)] orchestrator 종료"
} > "$root/docs/ops/state/log/orchestrator-runs.log"
out=$(detected_jobs "$root")
check "본문 인용은 실패로 오판하지 않는다" no orchestrator "$out"
rm -rf "$root"

echo ""
echo "통과 $pass / 실패 $fail"
[ "$fail" -eq 0 ]
