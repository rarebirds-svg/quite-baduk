#!/usr/bin/env bash
# launchd 잡들의 마지막 실행 timestamp가 임계 초과로 stale인지 검사하고 incident·알림을 발생시킨다.
set -euo pipefail

ROOT="/Users/daegong/projects/baduk"
LOG_DIR="$ROOT/docs/ops/state/log"
INCIDENTS="$ROOT/docs/ops/state/incidents.md"
COOLDOWN_DIR="$ROOT/docs/ops/state"
COOLDOWN_SECS=3600   # 같은 잡 1시간 1회 알림

# 잡 정의: "표시명|로그파일|임계(초)"
JOBS=(
  "orchestrator|orchestrator-runs.log|64800"      # 18h (plist는 12:00·18:00 두 슬롯, 야간 갭 18h 허용)
  "dev-cycle|dev-cycle-runs.log|108000"           # 30h
  "content-draft|content-draft-runs.log|108000"   # 30h
  "content-ingest|content-ingest-runs.log|108000" # 30h
  "analytics-weekly|analytics-weekly-runs.log|691200"  # 8d
  "backup|backup.out.log|108000"                  # 30h
)

now=$(date +%s)
incidents_added=0

extract_last_ts() {
  # 마지막 "[YYYY-MM-DD HH:MM:SS]" 패턴 찾아 epoch 초로 변환. 없으면 빈 문자열.
  local file="$1"
  [ -f "$file" ] || return 0
  local ts_str
  ts_str=$(grep -oE '^\[[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\]' "$file" | tail -1 | tr -d '[]')
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
    echo "- 마지막 실행: ${last_str:-N/A}"
    echo "- 임계 초과 — watchdog가 자동 감지."
  } >> "$INCIDENTS"
}

for entry in "${JOBS[@]}"; do
  IFS='|' read -r job logname threshold <<<"$entry"
  logfile="$LOG_DIR/$logname"
  last_ts=$(extract_last_ts "$logfile")
  if [ -z "$last_ts" ]; then
    last_str="(로그 비어있음)"
    age=$threshold   # 비어있으면 무조건 stale
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
    msg="[inkbaduk] $job 잡 ${age_h}h 정지 — 마지막 실행 ${last_str:-N/A}"
    "$ROOT/ops/notify.sh" "$msg" || echo "[$job] notify 채널 전부 실패 (incident는 기록됨)" >&2
    write_cooldown "$job"
    incidents_added=$(( incidents_added + 1 ))
  fi
done

echo "watchdog 검사 완료 — 신규 incident $incidents_added 건"
exit 0
