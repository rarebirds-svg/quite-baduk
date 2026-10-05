#!/usr/bin/env bash
# session-retry.sh의 리셋 시각 파싱·대기 계산과 재시도 동작을 픽스처로 검증한다.
set -euo pipefail
cd "$(dirname "$0")/../.."
. ops/lib/session-retry.sh

pass=0; fail=0
check() { # $1=설명 $2=기대값 $3=실제값
  if [ "$2" = "$3" ]; then echo "  ok — $1"; pass=$((pass+1))
  else echo "  FAIL — $1 (기대 $2, 실제 $3)"; fail=$((fail+1)); fi
}

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# 알림·마커 픽스처는 파일 상단에서 한 번만 잡는다 — 아래 모든 케이스가 이 경로를 공유한다.
cat > "$tmp/fake-notify" <<'EOF'
#!/usr/bin/env bash
echo "$1" >> "$NOTIFY_LOG"
EOF
chmod +x "$tmp/fake-notify"
export NOTIFY_LOG="$tmp/notify-calls"; : > "$NOTIFY_LOG"
MARKER_DIR="$tmp/markers"
NOTIFY="$tmp/fake-notify"

# 인증 교차 확인용 자격증명 픽스처. 자식 bash(check-claude-auth.sh)로 전달돼야 하므로 export한다.
real_now=$(date +%s)
printf '{"claudeAiOauth":{"refreshTokenExpiresAt":%s}}\n' "$(( (real_now - 3600) * 1000 ))" > "$tmp/cred-expired.json"
printf '{"claudeAiOauth":{"refreshTokenExpiresAt":%s}}\n' "$(( (real_now + 2592000) * 1000 ))" > "$tmp/cred-ok.json"

# now 픽스처: 2026-08-30 09:03:42 KST → epoch
NOW=$(date -j -f "%Y-%m-%d %H:%M:%S" "2026-08-30 09:03:42" +%s)

echo "1) 실측 메시지 — resets 9:30am, 현재 09:03:42"
echo "You've hit your session limit · resets 9:30am (Asia/Seoul)" > "$tmp/a"
# 09:30:00 - 09:03:42 = 1578s + 300 마진 = 1878
check "27분 뒤 리셋 + 5분 마진" 1878 "$(session_limit_reset_wait "$tmp/a" "$NOW")"

echo "2) 실측 메시지 — resets 4am (분 없음), 현재 02:00:00"
NOW2=$(date -j -f "%Y-%m-%d %H:%M:%S" "2026-08-17 02:00:00" +%s)
echo "You've hit your session limit · resets 4am (Asia/Seoul)" > "$tmp/b"
check "2시간 + 5분 마진" 7500 "$(session_limit_reset_wait "$tmp/b" "$NOW2")"

echo "3) 리셋 시각이 이미 지남 → 익일로 넘기되 상한 6h 적용"
echo "resets 8am (Asia/Seoul)" > "$tmp/c"
NOW3=$(date -j -f "%Y-%m-%d %H:%M:%S" "2026-08-30 09:00:00" +%s)
check "상한 21600s" 21600 "$(session_limit_reset_wait "$tmp/c" "$NOW3")"

echo "4) 12시간 경계 — resets 12pm, 현재 11:00"
echo "resets 12pm (Asia/Seoul)" > "$tmp/d"
NOW4=$(date -j -f "%Y-%m-%d %H:%M:%S" "2026-08-30 11:00:00" +%s)
check "정오 = 1h + 마진" 3900 "$(session_limit_reset_wait "$tmp/d" "$NOW4")"

echo "5) 파싱 불가 문구 → 폴백 3600"
echo "some unrelated error output" > "$tmp/e"
check "폴백" 3600 "$(session_limit_reset_wait "$tmp/e" "$NOW")"

echo "6) 재시도 동작 — 1회차 세션한도 실패 후 2회차 성공"
runlog="$tmp/runlog"; : > "$runlog"
state="$tmp/state"; : > "$state"
fake_claude() {
  if [ ! -s "$state" ]; then
    echo tried > "$state"
    echo "You've hit your session limit · resets 9:30am (Asia/Seoul)"
    return 1
  fi
  echo "정상 출력"
  return 0
}
# 테스트에서는 실제 sleep을 건너뛴다
sleep() { :; }
run_claude_with_session_retry "$runlog" fake_claude
check "최종 exit 0" 0 "$?"
check "재시도 로그 기록" 1 "$(grep -c '세션 한도 감지' "$runlog")"
check "2회차 출력 도달" 1 "$(grep -c '정상 출력' "$runlog")"
unset -f sleep

echo "7) 세션한도 아닌 실패 → 재시도 없이 즉시 실패"
runlog2="$tmp/runlog2"; : > "$runlog2"
fake_fail() { echo "other fatal error"; return 3; }
rc=0; run_claude_with_session_retry "$runlog2" fake_fail || rc=$?
check "exit code 전파" 3 "$rc"
check "재시도 안 함" 0 "$(grep -c '세션 한도 감지' "$runlog2")"

# --- 인증 만료 보류 분기 ---
auth_fail() { echo "Failed to authenticate: OAuth session expired and could not be refreshed"; return 1; }
export CLAUDE_CREDENTIALS_CMD="cat $tmp/cred-expired.json"

echo "8) OAuth 만료 감지 → 보류 마커·런로그·알림 1회"
runlog3="$tmp/dev-cycle-runs.log"; : > "$runlog3"
rc=0; run_claude_with_session_retry "$runlog3" auth_fail || rc=$?
marker="$tmp/markers/auth-pending-dev-cycle"
check "exit code 전파" 1 "$rc"
check "보류 마커 생성" 1 "$([ -f "$marker" ] && echo 1 || echo 0)"
check "마커 내용이 epoch" 1 "$(grep -cE '^[0-9]+$' "$marker")"
check "런로그 보류 한 줄" 1 "$(grep -c '인증 만료 감지' "$runlog3")"
check "알림 1회" 1 "$(wc -l < "$NOTIFY_LOG" | tr -d ' ')"
check "세션 한도 재시도 경로 미진입" 0 "$(grep -c '세션 한도 감지' "$runlog3")"

echo "9) 같은 환경에서 재실행 → 알림 누적 없음·마커 불변"
marker_before=$(cat "$marker")
rc=0; run_claude_with_session_retry "$runlog3" auth_fail || rc=$?
check "여전히 exit 1" 1 "$rc"
check "알림 1회 유지" 1 "$(wc -l < "$NOTIFY_LOG" | tr -d ' ')"
check "마커 내용 불변" "$marker_before" "$(cat "$marker")"

echo "10) 세션 한도 문구는 여전히 재시도 경로 — 보류 마커 미생성"
runlog4="$tmp/orchestrator-runs.log"; : > "$runlog4"
state2="$tmp/state2"; : > "$state2"
limit_then_ok() {
  if [ ! -s "$state2" ]; then
    echo tried > "$state2"
    echo "You've hit your session limit · resets 9:30am (Asia/Seoul)"
    return 1
  fi
  echo "정상 출력"
  return 0
}
sleep() { :; }
run_claude_with_session_retry "$runlog4" limit_then_ok
check "최종 exit 0" 0 "$?"
check "재시도 로그 기록" 1 "$(grep -c '세션 한도 감지' "$runlog4")"
check "보류 마커 미생성" 0 "$([ -f "$tmp/markers/auth-pending-orchestrator" ] && echo 1 || echo 0)"
unset -f sleep

echo "11) 일반 실패 → 보류 마커 미생성"
runlog5="$tmp/news-hook-runs.log"; : > "$runlog5"
rc=0; run_claude_with_session_retry "$runlog5" fake_fail || rc=$?
check "exit code 전파" 3 "$rc"
check "보류 마커 미생성" 0 "$([ -f "$tmp/markers/auth-pending-news-hook" ] && echo 1 || echo 0)"

echo "12) 인증 문구는 있으나 자격증명은 정상 → 오탐하지 않는다"
# incidents.md 인용문을 오케스트레이터가 출력하다 타임아웃하면 이 문구가 출력에 섞인다.
export CLAUDE_CREDENTIALS_CMD="cat $tmp/cred-ok.json"
runlog6="$tmp/content-draft-runs.log"; : > "$runlog6"
notify_before=$(wc -l < "$NOTIFY_LOG" | tr -d ' ')
rc=0; run_claude_with_session_retry "$runlog6" auth_fail || rc=$?
check "exit code 전파" 1 "$rc"
check "보류 마커 미생성" 0 "$([ -f "$tmp/markers/auth-pending-content-draft" ] && echo 1 || echo 0)"
check "알림 누적 없음" "$notify_before" "$(wc -l < "$NOTIFY_LOG" | tr -d ' ')"
check "런로그 보류 문구 없음" 0 "$(grep -c '인증 만료 감지' "$runlog6")"

echo
echo "통과 $pass / 실패 $fail"
[ "$fail" -eq 0 ]
