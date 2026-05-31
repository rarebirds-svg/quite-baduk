#!/usr/bin/env bash
# api·web HTTP 헬스를 폴링하고 연속 실패가 임계 넘으면 자동 kickstart·incident·알림을 수행한다.
set -euo pipefail

# ROOT는 스크립트 위치 기준으로 도출 — worktree/메인 어디서 실행하든 자기 트리에 작용한다.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$ROOT/docs/ops/state"
INCIDENTS="$STATE_DIR/incidents.md"

# 설정 (테스트 시 env로 덮어쓰기 가능)
API_URL="${HEALTH_API_URL:-http://127.0.0.1:8000/api/health}"
WEB_URL="${HEALTH_WEB_URL:-http://127.0.0.1:3000/}"
FAIL_THRESHOLD="${HEALTH_FAIL_THRESHOLD:-2}"   # watchdog 1h 주기 → 2회면 ~2h 무응답
COOLDOWN_SECS="${HEALTH_COOLDOWN_SECS:-3600}"
DRY_RUN="${WATCHDOG_DRY_RUN:-0}"               # 1이면 kickstart·incident·notify 모두 생략

now=$(date +%s)

probe() {  # url → 0(2xx/3xx) | 1(실패)
  local url="$1" code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 "$url" 2>/dev/null || echo 000)
  [ "$code" -ge 200 ] && [ "$code" -lt 400 ]
}

check_one() {  # name url label
  local name="$1" url="$2" label="$3"
  local cfile="$STATE_DIR/.health-fail-$name"
  if probe "$url"; then
    rm -f "$cfile"
    echo "[$name] OK"
    return 0
  fi
  local fails
  fails=$(( $(cat "$cfile" 2>/dev/null || echo 0) + 1 ))
  echo "$fails" > "$cfile"
  echo "[$name] FAIL ($fails/$FAIL_THRESHOLD)"
  [ "$fails" -lt "$FAIL_THRESHOLD" ] && return 0

  # 쿨다운 — 무한 재시작 루프 방지
  local kfile="$STATE_DIR/.health-kick-$name"
  local lastk
  lastk=$(cat "$kfile" 2>/dev/null || echo 0)
  if [ $(( now - lastk )) -lt "$COOLDOWN_SECS" ]; then
    echo "[$name] 임계 초과나 쿨다운 중 — kickstart skip"
    return 0
  fi

  if [ "$DRY_RUN" = "1" ]; then
    echo "[dry-run] launchctl kickstart -k gui/$(id -u)/$label (incident·notify 생략)"
    rm -f "$cfile"
    return 0
  fi

  echo "[$name] 임계 초과 — 자동 kickstart 실행"
  if launchctl kickstart -k "gui/$(id -u)/$label"; then
    kick_note="watchdog가 자동 재시작 수행."
  else
    kick_note="자동 재시작 시도했으나 launchctl 비정상 종료 — 수동 확인 필요."
    echo "[$name] kickstart 실패 (launchctl rc 비정상)" >&2
  fi
  echo "$now" > "$kfile"   # 성공·실패 무관 cooldown 기록 — launchd 매시간 난타 방지
  rm -f "$cfile"
  {
    echo ""
    echo "### WD-$(date '+%Y%m%d-%H%M%S') — $name 헬스 ${fails}회 연속 실패 자동 kickstart"
    echo ""
    echo "- 감지: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "- 대상: $label / URL $url"
    echo "- $kick_note"
  } >> "$INCIDENTS"
  "$ROOT/ops/notify.sh" "[inkbaduk] $name ${fails}회 무응답 — 자동 kickstart 실행 ($label)" \
    || echo "[$name] notify 실패 (incident는 기록됨)" >&2
}

check_one "api" "$API_URL" "com.baduk.api" || true
check_one "web" "$WEB_URL" "com.baduk.web" || true
echo "health 검사 완료"
exit 0
