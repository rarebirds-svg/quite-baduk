#!/usr/bin/env bash
# 세션 한도("hit your session limit")로 죽은 헤드리스 Claude 실행을 리셋 시각 이후 1회 재시도하는 공용 헬퍼 (run-*.sh가 source).

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
  local tmp rc attempt wait
  for attempt in 1 2; do
    tmp=$(mktemp)
    rc=0
    "$@" > "$tmp" 2>&1 || rc=$?
    cat "$tmp" >> "$runlog"
    if [ "$rc" -eq 0 ]; then rm -f "$tmp"; return 0; fi
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
