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
  for job in orchestrator dev-cycle content-draft content-ingest analytics-weekly news-hook; do
    {
      echo "[$recent] $job 시작"
      echo "[$recent] $job 종료"
    } > "$logdir/$job-runs.log"
  done
  {
    echo "[$recent] backup 시작"
    echo "[$recent] backup 완료"
  } > "$logdir/backup.out.log"
  # 다이제스트 마커도 픽스처 안에 둔다 — 실제 ~/.ops-report/markers를 읽으면
  # 이 테스트가 벽시계 시각과 운영 마커 상태에 의존하게 된다.
  mkdir -p "$root/markers"
  # 인증 상태도 픽스처로 고정한다 — 실제 키체인을 읽으면 재로그인 시점에 따라 결과가 흔들린다.
  printf '{"claudeAiOauth":{"refreshTokenExpiresAt":%s}}\n' "$(( (now + 2592000) * 1000 ))" > "$root/creds.json"
  # 묶음 알림은 notify_once를 거친다 — NOTIFY를 픽스처로 갈아끼워 호출 횟수를 센다.
  cat > "$root/fake-notify" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$(dirname "$0")/notify-calls"
EOF
  chmod +x "$root/fake-notify"
  echo "$root"
}

# 픽스처 ROOT로 대상 스크립트를 1회 실행한다. 인증 자격증명도 픽스처 파일에서 읽힌다.
run_target() {
  local root="$1"
  ROOT="$root" MARKER_DIR="$root/markers" NOTIFY="$root/fake-notify" \
    CLAUDE_CREDENTIALS_CMD="cat '$root/creds.json'" \
    bash "$TARGET" >/dev/null 2>&1
}

# 이 케이스에서 incident가 난 잡 이름들을 개행 구분으로 출력한다.
detected_jobs() {
  local root="$1"
  run_target "$root"
  local incidents="$root/docs/ops/state/incidents.md"
  [ -f "$incidents" ] || return 0
  grep -oE '^### WD-[0-9]+-[0-9]+ — [a-z-]+ stale' "$incidents" | awk '{print $4}'
}

# count_matches <ERE> <파일> → 매칭 줄 수. 파일이 없으면 0.
count_matches() {
  [ -f "$2" ] || { echo 0; return 0; }
  local n
  n=$(grep -cE "$1" "$2" 2>/dev/null) || n=0
  echo "$n"
}

count_lines() {  # 파일이 없으면 0
  [ -f "$1" ] || { echo 0; return 0; }
  wc -l < "$1" | tr -d ' '
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

check_eq() {  # check_eq <설명> <기대값> <실제값>
  local desc="$1" expect="$2" got="$3"
  if [ "$got" = "$expect" ]; then
    echo "  ok — $desc"
    pass=$(( pass + 1 ))
  else
    echo "  FAIL — $desc (기대 $expect, 실제 $got)"
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

AUTH_BUNDLE_RE='^### WD-[0-9]+-[0-9]+ — Claude 인증 만료 \(stale: dev-cycle, orchestrator\)$'

echo "6) 인증 만료 — Claude 잡 stale은 1건으로 묶고 backup은 별도"
root=$(make_fixture)
printf '{"claudeAiOauth":{"refreshTokenExpiresAt":%s}}\n' "$(( (now - 3600) * 1000 ))" > "$root/creds.json"
for job in dev-cycle orchestrator; do
  {
    echo "[$(ts_ago 604800)] $job 시작"
    echo "[$(ts_ago 604740)] $job 종료"
  } > "$root/docs/ops/state/log/$job-runs.log"
done
{
  echo "[$(ts_ago 604800)] backup 시작"
  echo "[$(ts_ago 604740)] backup 완료"
} > "$root/docs/ops/state/log/backup.out.log"
# content-ingest는 Claude를 쓰지 않는다 (run-content-ingest.sh는 session-retry를 source하지 않음).
{
  echo "[$(ts_ago 1209600)] content-ingest 시작"
  echo "[$(ts_ago 1209540)] content-ingest 종료"
} > "$root/docs/ops/state/log/content-ingest-runs.log"
incidents="$root/docs/ops/state/incidents.md"
out=$(detected_jobs "$root")
check "dev-cycle 개별 stale 블록은 남기지 않는다" no dev-cycle "$out"
check "orchestrator 개별 stale 블록은 남기지 않는다" no orchestrator "$out"
check "backup은 Claude와 무관하므로 기존 경로대로 기록된다" yes backup "$out"
check "content-ingest도 Claude와 무관하므로 개별 블록으로 남는다" yes content-ingest "$out"
check_eq "묶음 incident 1건" 1 "$(count_matches "$AUTH_BUNDLE_RE" "$incidents")"
check_eq "묶음 알림 1회" 1 "$(count_lines "$root/notify-calls")"

echo "7) 인증 만료 상태로 즉시 재실행"
run_target "$root"
check_eq "쿨다운으로 묶음 incident가 늘지 않는다" 1 "$(count_matches "$AUTH_BUNDLE_RE" "$incidents")"
check_eq "묶음 알림도 누적되지 않는다" 1 "$(count_lines "$root/notify-calls")"
rm -rf "$root"

echo "8) 재트리거 직후 stale — 개별 경보를 건너뛴다"
# check-auth-recovery가 방금 kickstart한 잡은 아직 성공 로그를 남기지 못한다.
# 여기서 경보하면 오케스트레이터가 화이트리스트로 다시 kickstart -k 해 실행 중인 잡을 죽인다.
root=$(make_fixture)
{
  echo "[$(ts_ago 604800)] dev-cycle 시작"
  echo "[$(ts_ago 604740)] dev-cycle 종료"
} > "$root/docs/ops/state/log/dev-cycle-runs.log"
echo "$(( now - 600 ))" > "$root/markers/auth-retriggered-dev-cycle"
out=$(detected_jobs "$root")
check "10분 전 재트리거면 stale 경보를 보류한다" no dev-cycle "$out"
rm -rf "$root"

echo "9) 재트리거 후 2h 초과 — 기존대로 경보"
root=$(make_fixture)
{
  echo "[$(ts_ago 604800)] dev-cycle 시작"
  echo "[$(ts_ago 604740)] dev-cycle 종료"
} > "$root/docs/ops/state/log/dev-cycle-runs.log"
echo "$(( now - 10800 ))" > "$root/markers/auth-retriggered-dev-cycle"
out=$(detected_jobs "$root")
check "3h 전 재트리거는 더 이상 보류 사유가 아니다" yes dev-cycle "$out"
rm -rf "$root"

echo ""
echo "통과 $pass / 실패 $fail"
[ "$fail" -eq 0 ]
