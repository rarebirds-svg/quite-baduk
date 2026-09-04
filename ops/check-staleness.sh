#!/usr/bin/env bash
# launchd 잡들의 마지막 성공 실행 timestamp가 임계 초과로 stale인지 검사하고 incident·알림을 발생시킨다.
set -euo pipefail

if [ -z "${ROOT:-}" ]; then
  echo "check-staleness.sh: ROOT를 명시적으로 지정해야 한다 — 예) ROOT=/path/to/repo $0" >&2
  exit 1
fi
. "$(dirname "$0")/lib/notify-once.sh"

LOG_DIR="$ROOT/docs/ops/state/log"
INCIDENTS="$ROOT/docs/ops/state/incidents.md"
COOLDOWN_DIR="$ROOT/docs/ops/state"
COOLDOWN_SECS=3600   # 같은 잡 1시간 1회 알림
# 다이제스트 미발송은 잡 stale과 달리 즉시 고쳐지지 않는다. watchdog 주기(1h)와 쿨다운이 같으면
# 매 실행마다 쿨다운이 갓 만료돼 억제가 사실상 무효가 되므로 주기보다 길게 둔다.
DIGEST_COOLDOWN_SECS=21600   # 6h
# 인증 만료는 사람이 /login 하기 전까지 풀리지 않는다. 잡별 쿨다운(1h)으로 두면 묶음 경보가
# 매 watchdog 실행마다 다시 쌓이므로 다이제스트와 같은 6h를 쓴다.
AUTH_COOLDOWN_SECS=21600     # 6h
MARKER_DIR="${MARKER_DIR:-$HOME/.ops-report/markers}"   # 테스트가 픽스처로 덮어쓴다
# notify_once의 NOTIFY 기본값은 상대경로다 — 이 스크립트는 cd하지 않으므로 절대경로로 고정한다.
NOTIFY="${NOTIFY:-$ROOT/ops/notify.sh}"
# check-auth-recovery가 방금 재트리거한 잡은 아직 성공 로그를 남기지 못한다. 이 창 안에서는
# stale 경보를 건너뛴다 — 곧바로 경보하면 오케스트레이터가 다시 kickstart 해 실행 중인 잡을 죽인다.
RETRIGGER_GRACE_SECS=7200

# 잡 정의: "표시명|로그파일|임계(초)|성공 종료 마커"
JOBS=(
  "orchestrator|orchestrator-runs.log|64800|orchestrator 종료"      # 18h (plist는 09:00·21:00 두 슬롯, 최장 갭 12h + 6h 마진)
  "dev-cycle|dev-cycle-runs.log|108000|dev-cycle 종료"              # 30h
  "content-draft|content-draft-runs.log|432000|content-draft 종료"  # 5d (plist 주 2회 토·수 02:00, 최장 4d 갭 + 1d 마진)
  "content-ingest|content-ingest-runs.log|777600|content-ingest 종료" # 9d (plist 주 1회 일 03:00, 7d 주기 + 2d 마진)
  "analytics-weekly|analytics-weekly-runs.log|691200|analytics-weekly 종료"  # 8d
  "news-hook|news-hook-runs.log|691200|news-hook 종료"  # 8d (plist 주 1회 일 05:00, 7d 주기 + 1d 마진)
  "backup|backup.out.log|108000|backup 완료"                        # 30h
)

now=$(date +%s)
incidents_added=0

# Claude 인증이 만료되면 Claude 의존 잡이 한꺼번에 stale이 된다. 원인이 하나이므로 잡별로
# 경보하지 않고 아래에서 1건으로 묶는다. 종료코드만 쓴다 — 0 ok / 1 만료 / 2 확인 불가·임박.
# CLAUDE_CREDENTIALS_CMD·NOW는 환경으로 그대로 전달된다 (이 스크립트는 소문자 now를 쓴다).
auth_rc=0
bash "$(dirname "$0")/check-claude-auth.sh" >/dev/null 2>&1 || auth_rc=$?
AUTH_EXPIRED=0
if [ "$auth_rc" -eq 1 ]; then
  AUTH_EXPIRED=1
fi
auth_stale_jobs=""

# Claude를 쓰는 잡만 인증 만료 묶음 대상이다. backup·content-ingest는 Claude를 호출하지 않으므로
# (run-content-ingest.sh는 session-retry를 source하지 않는다) 기존 개별 경보 경로를 그대로 탄다.
is_claude_job() {
  case "$1" in
    orchestrator|dev-cycle|content-draft|analytics-weekly|news-hook) return 0 ;;
    *) return 1 ;;
  esac
}

# auth-retriggered-<job> 마커는 check-auth-recovery가 남긴다. 잡 표시명과 마커의 잡 이름은
# 같은 값이라 별도 매핑이 필요 없다 (마커는 <job>-runs.log 이름에서 유래).
recently_retriggered() {  # recently_retriggered <잡> <마지막 성공 epoch(빈값 가능)>
  local job="$1" last="$2"
  local file="$MARKER_DIR/auth-retriggered-$job"
  [ -f "$file" ] || return 1
  local ts
  ts=$(cat "$file" 2>/dev/null || echo 0)
  case "$ts" in ''|*[!0-9]*) return 1 ;; esac
  [ -n "$last" ] && [ "$ts" -le "$last" ] && return 1
  [ $(( now - ts )) -lt "$RETRIGGER_GRACE_SECS" ]
}

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
  local secs="${2:-$COOLDOWN_SECS}"
  local file="$COOLDOWN_DIR/.watchdog-cooldown-$job"
  [ -f "$file" ] || return 1   # cooldown 없음 → 알림 가능
  local last
  last=$(cat "$file" 2>/dev/null || echo 0)
  local diff=$(( now - last ))
  [ "$diff" -lt "$secs" ]   # true면 아직 cooldown 중
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
    if recently_retriggered "$job" "$last_ts"; then
      echo "[$job] stale이지만 재트리거 대기 중 — skip" >&2
      continue
    fi
    if [ "$AUTH_EXPIRED" -eq 1 ] && is_claude_job "$job"; then
      # 잡별 쿨다운 마커는 건드리지 않는다 — 인증 회복 후 개별 경보가 정상 동작해야 한다.
      auth_stale_jobs="$auth_stale_jobs $job"
      continue
    fi
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

# 인증 만료로 보류된 stale 잡들을 1건으로 묶어 기록한다.
if [ -n "$auth_stale_jobs" ]; then
  if check_cooldown "claude-auth" "$AUTH_COOLDOWN_SECS"; then
    echo "[claude-auth] 인증 만료 stale이지만 cooldown — skip notify" >&2
  else
    # 이름을 정렬해 JOBS 배열 순서가 바뀌어도 incident 제목이 흔들리지 않게 한다.
    auth_stale_list=$(printf '%s\n' $auth_stale_jobs | sort | paste -sd, - | sed 's/,/, /g')
    {
      echo ""
      echo "### WD-$(date '+%Y%m%d')-$(date +%H%M%S) — Claude 인증 만료 (stale: $auth_stale_list)"
      echo ""
      echo "- 인증 만료로 Claude 잡 전부 정지 — claude /login 필요. 개별 stale 경보는 이 건으로 묶음."
    } >> "$INCIDENTS"
    # session-retry·check-auth-recovery와 같은 키를 써 인증 만료 알림을 하루 1회로 합친다.
    msg="[inkbaduk] Claude 인증 만료 — 잡 정지: $auth_stale_list. claude /login 필요"
    notify_once claude-auth "$msg" || echo "[claude-auth] notify 채널 전부 실패 (incident는 기록됨)" >&2
    write_cooldown "claude-auth"
    incidents_added=$(( incidents_added + 1 ))
  fi
fi

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
    if check_cooldown "$key" "$DIGEST_COOLDOWN_SECS"; then
      echo "[$key] 미발송이지만 cooldown — skip notify" >&2
      continue
    fi
    msg="[$project] $slot 다이제스트 미발송 — $today 정시 +30분 경과, 마커 없음"
    "$ROOT/ops/notify.sh" "$msg" || echo "[$key] notify 채널 전부 실패" >&2
    write_cooldown "$key"
    incidents_added=$(( incidents_added + 1 ))
  done
done

echo "watchdog 검사 완료 — 신규 incident $incidents_added 건"
exit 0
