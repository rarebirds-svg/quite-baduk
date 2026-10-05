#!/usr/bin/env bash
# 세션 한도("hit your session limit")로 죽은 헤드리스 Claude 실행을 리셋 시각 이후 1회 재시도하는 공용 헬퍼 (run-*.sh가 source).

. "$(dirname "${BASH_SOURCE[0]}")/notify-once.sh"

# 한도 메시지의 "resets 4am" / "resets 9:30am" 류 문구로 대기 초를 계산한다.
# $1=Claude 출력을 담은 파일, $2=현재 epoch(테스트 주입용, 기본 now).
# 파싱 실패 시 3600, 상한 21600(6h — 다음 스케줄 슬롯 침범 방지), 리셋 시각에 300s 마진.
session_limit_reset_wait() {
  local file="$1" now="${2:-$(date +%s)}"
  local fallback=3600 cap=21600 margin=300
  local token h m ampm day target wait
  token=$(grep -oE "resets [0-9]{1,2}(:[0-9]{2})?[ap]m" "$file" | head -1 | sed 's/^resets //')
  if [ -z "$token" ]; then echo "$fallback"; return 0; fi
  h=$(echo "$token" | sed -E 's/^([0-9]{1,2}).*/\1/')
  m=$(echo "$token" | grep -oE ':[0-9]{2}' | tr -d ':' || true)
  ampm=$(echo "$token" | grep -oE '[ap]m$')
  h=$((10#$h)); m=$((10#${m:-0}))
  [ "$ampm" = "pm" ] && [ "$h" -ne 12 ] && h=$((h + 12))
  [ "$ampm" = "am" ] && [ "$h" -eq 12 ] && h=0
  day=$(date -j -r "$now" +%Y-%m-%d)
  target=$(date -j -f "%Y-%m-%d %H:%M:%S" "$day $(printf '%02d:%02d' "$h" "$m"):00" +%s 2>/dev/null) \
    || { echo "$fallback"; return 0; }
  [ "$target" -le "$now" ] && target=$((target + 86400))
  wait=$((target - now + margin))
  [ "$wait" -gt "$cap" ] && wait=$cap
  echo "$wait"
}

# Claude를 실행하고, 세션 한도로 실패하면 리셋 시각까지 기다렸다가 1회 재시도한다.
# $1=런로그 경로, $2...=실행할 명령 전체. 성공 시 0, 최종 실패 시 마지막 exit code.
run_claude_with_session_retry() {
  local runlog="$1"; shift
  local tmp rc attempt wait marker_dir job marker auth_rc
  local marker_dir_default="$HOME/.ops-report/markers"
  for attempt in 1 2; do
    tmp=$(mktemp)
    rc=0
    "$@" > "$tmp" 2>&1 || rc=$?
    cat "$tmp" >> "$runlog"
    if [ "$rc" -eq 0 ]; then rm -f "$tmp"; return 0; fi
    # 인증 만료는 사람이 /login 해야 풀리므로 재시도하지 않고 마커로 보류만 남긴다(세션 한도 분기보다 먼저).
    # 문구만으로는 오탐한다 — incidents.md에 인용된 이 문구를 오케스트레이터가 출력하다 죽는 경우가 있다.
    # 실제 자격증명을 교차 확인해 rc=1(만료)일 때만 보류로 넘어간다.
    if grep -qE "OAuth session expired|Failed to authenticate" "$tmp"; then
      auth_rc=0
      bash "$(dirname "${BASH_SOURCE[0]}")/../check-claude-auth.sh" >/dev/null 2>&1 || auth_rc=$?
      if [ "$auth_rc" -eq 1 ]; then
        rm -f "$tmp"
        marker_dir="${MARKER_DIR:-$marker_dir_default}"
        job=$(basename "$runlog"); job="${job%-runs.log}"
        marker="$marker_dir/auth-pending-$job"
        mkdir -p "$marker_dir"
        [ -f "$marker" ] || date +%s > "$marker"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 인증 만료 감지 — 보류 (재로그인 후 watchdog가 1회 재트리거)" >> "$runlog"
        notify_once claude-auth "⛔ Claude 인증 만료 — 헤드리스 잡 보류 중. 터미널에서 claude → /login 후 다음 watchdog(1h)이 자동 재트리거." || true
        return "$rc"
      fi
    fi
    if [ "$attempt" -eq 1 ] && grep -q "hit your session limit" "$tmp"; then
      wait=$(session_limit_reset_wait "$tmp")
      rm -f "$tmp"
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] 세션 한도 감지 — ${wait}s 대기 후 1회 재시도" >> "$runlog"
      sleep "$wait"
      continue
    fi
    rm -f "$tmp"
    return "$rc"
  done
  return "$rc"
}
