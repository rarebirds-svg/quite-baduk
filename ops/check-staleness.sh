#!/usr/bin/env bash
# launchd 잡들의 마지막 성공 실행 timestamp가 임계 초과로 stale인지 검사하고 incident·알림을 발생시킨다.
set -euo pipefail

ROOT="${ROOT:-/Users/daegong/projects/baduk}"   # 테스트가 픽스처 디렉터리로 덮어쓴다
LOG_DIR="$ROOT/docs/ops/state/log"
INCIDENTS="$ROOT/docs/ops/state/incidents.md"
COOLDOWN_DIR="$ROOT/docs/ops/state"
COOLDOWN_SECS=3600   # 같은 잡 1시간 1회 알림
MARKER_DIR="${MARKER_DIR:-$HOME/.ops-report/markers}"   # 테스트가 픽스처로 덮어쓴다

# 잡 정의: "표시명|로그파일|임계(초)|성공 종료 마커"
JOBS=(
  "orchestrator|orchestrator-runs.log|64800|orchestrator 종료"      # 18h (plist는 12:00·18:00 두 슬롯, 야간 갭 18h 허용)
  "dev-cycle|dev-cycle-runs.log|108000|dev-cycle 종료"              # 30h
  "content-draft|content-draft-runs.log|432000|content-draft 종료"  # 5d (plist 주 2회 토·수 02:00, 최장 4d 갭 + 1d 마진)
  "content-ingest|content-ingest-runs.log|777600|content-ingest 종료" # 9d (plist 주 1회 일 03:00, 7d 주기 + 2d 마진)
  "analytics-weekly|analytics-weekly-runs.log|691200|analytics-weekly 종료"  # 8d
  "backup|backup.out.log|108000|backup 완료"                        # 30h
)

now=$(date +%s)
incidents_added=0

extract_last_ts() {
  # 마지막 "성공" 종료 마커의 timestamp를 epoch 초로 변환. 없으면 빈 문자열.
  #
  # 래퍼(run-*.sh)는 실패해도 "[ts] 비정상 종료" 뒤에 "[ts] <잡> 종료"를 무조건 남긴다.
  # 따라서 마지막 timestamp만 보면 인증 실패로 즉시 죽은 잡도 "방금 실행됨"으로 보이고,
  # 크래시 루프는 매 사이클 timestamp를 갱신해 영구히 은폐된다 (이슈 #70).
  # 직전에 "비정상 종료"가 찍힌 종료 마커는 성공으로 세지 않는다.
  local file="$1" success_marker="$2"
  [ -f "$file" ] || return 0
  local ts_str
  ts_str=$(awk -v ok="$success_marker" '
    /^\[[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]\]/ {
      ts = substr($0, 2, 19)
      rest = substr($0, 22)
      if (index(rest, "비정상 종료")) { failed = 1; next }
      if (index(rest, "시작"))        { failed = 0; next }
      if (index(rest, ok)) { if (!failed) last = ts; failed = 0 }
    }
    END { print last }
  ' "$file")
  [ -z "$ts_str" ] && return 0
  date -j -f "%Y-%m-%d %H:%M:%S" "$ts_str" +%s 2>/dev/null || true
}

check_cooldown() {
  local job="$1"
  local file="$COOLDOWN_DIR/.watchdog-cooldown-$job"
  [ -f "$file" ] || return 1   # cooldown 없음 → 알림 가능
  local last
  last=$(cat "$file" 2>/dev/null || echo 0)
  local diff=$(( now - last ))
  [ "$diff" -lt "$COOLDOWN_SECS" ]   # true면 아직 cooldown 중
}

write_cooldown() {
  local job="$1"
  echo "$now" > "$COOLDOWN_DIR/.watchdog-cooldown-$job"
}

append_incident() {
  local job="$1"
  local age_h="$2"
  local last_str="$3"
  local today
  today=$(date '+%Y%m%d')
  local id
  id="WD-$today-$(date +%H%M%S)"
  {
    echo ""
    echo "### $id — $job stale ${age_h}h"
    echo ""
    echo "- 감지: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "- 마지막 성공 실행: ${last_str:-N/A}"
    echo "- 임계 초과 — watchdog가 자동 감지."
  } >> "$INCIDENTS"
}

for entry in "${JOBS[@]}"; do
  IFS='|' read -r job logname threshold success_marker <<<"$entry"
  logfile="$LOG_DIR/$logname"
  last_ts=$(extract_last_ts "$logfile" "$success_marker")
  if [ -z "$last_ts" ]; then
    last_str="(성공 실행 기록 없음)"
    age=$threshold   # 성공 기록이 하나도 없으면 무조건 stale
  else
    last_str=$(date -r "$last_ts" '+%Y-%m-%d %H:%M:%S')
    age=$(( now - last_ts ))
  fi

  if [ "$age" -ge "$threshold" ]; then
    if check_cooldown "$job"; then
      echo "[$job] stale but in cooldown — skip notify" >&2
      continue
    fi
    age_h=$(( age / 3600 ))
    append_incident "$job" "$age_h" "$last_str"
    msg="[inkbaduk] $job 잡 ${age_h}h 정지 — 마지막 성공 실행 ${last_str:-N/A}"
    "$ROOT/ops/notify.sh" "$msg" || echo "[$job] notify 채널 전부 실패 (incident는 기록됨)" >&2
    write_cooldown "$job"
    incidents_added=$(( incidents_added + 1 ))
  fi
done

# 정기 다이제스트 미발송 검사 — 마커 부재가 "발송 실패 또는 미실행" 신호다.
# 슬롯 정시(09:00·21:00) +30분이 지났는데 마커가 없으면 경보한다.
today=$(date '+%Y-%m-%d')
cur_min=$(( 10#$(date '+%H') * 60 + 10#$(date '+%M') ))
for slot_def in "am|540" "pm|1260"; do   # 09:00=540분, 21:00=1260분
  IFS='|' read -r slot slot_min <<<"$slot_def"
  [ "$cur_min" -lt $(( slot_min + 30 )) ] && continue
  for project in inkbaduk popory; do
    marker="$MARKER_DIR/$project-$slot-$today"
    [ -f "$marker" ] && continue
    key="digest-$project-$slot"
    if check_cooldown "$key"; then
      echo "[$key] 미발송이지만 cooldown — skip notify" >&2
      continue
    fi
    msg="[inkbaduk] $project $slot 다이제스트 미발송 — $today 정시 +30분 경과, 마커 없음"
    "$ROOT/ops/notify.sh" "$msg" || echo "[$key] notify 채널 전부 실패" >&2
    write_cooldown "$key"
    incidents_added=$(( incidents_added + 1 ))
  done
done

echo "watchdog 검사 완료 — 신규 incident $incidents_added 건"
exit 0
