#!/usr/bin/env bash
# watchdog가 1시간마다 호출 — Claude 인증 상태를 확인해 만료·임박을 하루 1회 알리고, 회복되면 보류된 잡을 1회 재트리거한다.
set -euo pipefail

# ROOT는 주입 우선. 기본값은 스크립트 위치 기준 리포 루트다.
DEFAULT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="${ROOT:-$DEFAULT_ROOT}"
cd "$ROOT"   # notify-once.sh의 NOTIFY 기본값이 상대경로다

. ops/lib/notify-once.sh

MARKER_DIR="${MARKER_DIR:-$HOME/.ops-report/markers}"
LOG_DIR="$ROOT/docs/ops/state/log"
INCIDENTS="$ROOT/docs/ops/state/incidents.md"
NOW="${NOW:-$(date +%s)}"
GUARD_SECS=86400   # 24h 안에 두 번째 재트리거는 하지 않는다

# 잡 → launchd 라벨. 이름이 그대로 라벨이 아닌 예외만 따로 적는다.
label_for() {
  case "$1" in
    orchestrator) echo "com.inkbaduk.ops-orchestrator" ;;
    dev-cycle|content-draft|analytics-weekly|news-hook) echo "com.inkbaduk.$1" ;;
    *) return 1 ;;
  esac
}

append_incident() {  # append_incident <잡> <제목 뒷부분> <상세 한 줄>. check-staleness.sh의 WD 블록과 같은 형식
  local job="$1" title="$2" detail="$3"
  local id
  id="WD-$(date '+%Y%m%d')-$(date '+%H%M%S')"
  {
    echo ""
    echo "### $id — $job $title"
    echo ""
    echo "- 감지: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "- $detail"
  } >> "$INCIDENTS"
}

auth_rc=0
auth_out=$(bash ops/check-claude-auth.sh) || auth_rc=$?
echo "$auth_out"

if [ "$auth_rc" -eq 1 ]; then
  # 만료. session-retry.sh와 같은 키라 하루 1회로 합쳐진다. 재트리거는 하지 않는다.
  notify_once claude-auth "⛔ Claude 인증 만료 — 헤드리스 잡 보류 중. 터미널에서 claude → /login 후 다음 watchdog(1h)이 자동 재트리거." \
    || echo "check-auth-recovery: 만료 알림 발송 실패" >&2
  exit 0
fi

if [ "$auth_rc" -ne 0 ]; then
  # warn. 만료 임박(D-3)만 알리고, 확인 불가는 stdout에만 남긴다 — 키체인 접근 실패로 매일 울리지 않게.
  case "$auth_out" in
    *"확인 불가"*) : ;;
    *) notify_once claude-auth-warn "⚠️ ${auth_out#warn: }" || echo "check-auth-recovery: 임박 알림 발송 실패" >&2 ;;
  esac
  exit 0
fi

# 인증 ok — 보류된 잡을 재트리거한다.
# macOS 기본 bash 3.2는 set -u에서 빈 배열 전개가 unbound라 글롭을 직접 돌고 미매치를 건너뛴다.
for marker in "$MARKER_DIR"/auth-pending-*; do
  [ -e "$marker" ] || continue
  job=$(basename "$marker"); job="${job#auth-pending-}"
  label=$(label_for "$job") || {
    echo "check-auth-recovery: 알 수 없는 보류 잡 '$job' — 마커 삭제" >&2
    rm -f "$marker"
    continue
  }

  guard="$MARKER_DIR/auth-retriggered-$job"
  if [ -f "$guard" ]; then
    last=$(cat "$guard" 2>/dev/null || echo 0)
    case "$last" in ''|*[!0-9]*) last=0 ;; esac
    if [ $(( NOW - last )) -lt "$GUARD_SECS" ]; then
      rm -f "$marker"
      append_incident "$job" "인증 회복 후 재트리거 실패(🟡 격상)" "24h 내 2회째 인증 실패 — 사람 확인 필요."
      echo "재트리거 보류: $job (24h 내 2회째 — incident 기록)"
      continue
    fi
  fi

  # -k는 붙이지 않는다. 재로그인 후 정규 슬롯이 이미 정상 실행 중이면 -k가 그 실행을 죽인다.
  # -k 없는 kickstart는 실행 중이면 no-op, 아니면 시작이라 이 용도에 정확히 맞는다.
  kick_rc=0
  "${LAUNCHCTL:-launchctl}" kickstart "gui/$(id -u)/$label" || kick_rc=$?

  # 마커 전이는 성공·실패 무관하게 한다 — 매시 재트리거를 반복하는 루프를 막는다.
  rm -f "$marker"
  echo "$NOW" > "$guard"
  mkdir -p "$LOG_DIR"
  if [ "$kick_rc" -ne 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 인증 회복 — 재트리거 실패(launchctl rc=$kick_rc)" >> "$LOG_DIR/$job-runs.log"
    append_incident "$job" "재트리거 실패(launchctl rc=$kick_rc)" "launchctl kickstart 실패 ($label) — 사람 확인 필요."
    echo "재트리거 실패: $job ($label)"
    continue
  fi
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 인증 회복 — watchdog 재트리거" >> "$LOG_DIR/$job-runs.log"
  echo "재트리거: $job ($label)"
done

exit 0
