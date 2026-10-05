#!/usr/bin/env bash
# check-auth-recovery.sh의 인증 상태별 알림·보류 잡 재트리거·루프 가드를 임시 ROOT 픽스처로 검증한다.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET="$REPO/ops/check-auth-recovery.sh"

pass=0
fail=0
now=$(date +%s)
uid=$(id -u)

check() {  # check <설명> <기대> <실제>
  local desc="$1" expect="$2" got="$3"
  if [ "$expect" = "$got" ]; then
    echo "  ok — $desc"
    pass=$(( pass + 1 ))
  else
    echo "  FAIL — $desc (기대 [$expect], 실제 [$got])"
    fail=$(( fail + 1 ))
  fi
}

count_lines() {  # 파일이 없으면 0
  [ -f "$1" ] || { echo 0; return 0; }
  wc -l < "$1" | tr -d ' '
}

# 임시 ROOT. ops/는 실제 worktree를 심볼릭 링크해 스크립트가 상대경로로 형제 스크립트를 찾게 한다.
make_fixture() {  # make_fixture <만료까지 남은 초>
  local remain="$1"
  local root
  root=$(mktemp -d -t auth-recovery-fixture)
  mkdir -p "$root/docs/ops/state/log" "$root/markers"
  : > "$root/docs/ops/state/incidents.md"
  ln -s "$REPO/ops" "$root/ops"

  printf '{"claudeAiOauth":{"refreshTokenExpiresAt":%s}}' "$(( (now + remain) * 1000 ))" > "$root/cred.json"

  cat > "$root/fake-launchctl" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$(dirname "$0")/launchctl-calls"
EOF
  cat > "$root/fake-notify" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$(dirname "$0")/notify-calls"
EOF
  chmod +x "$root/fake-launchctl" "$root/fake-notify"
  echo "$root"
}

# 표준출력을 반환한다. 종료코드는 서브셸 밖으로 못 나가므로 $root/rc 파일에 남긴다.
run_recovery() {
  local root="$1" rc=0
  ROOT="$root" MARKER_DIR="$root/markers" LAUNCHCTL="$root/fake-launchctl" \
    NOTIFY="$root/fake-notify" CLAUDE_CREDENTIALS_CMD="cat $root/cred.json" NOW="$now" \
    bash "$TARGET" 2>"$root/stderr" || rc=$?
  echo "$rc" > "$root/rc"
}

echo "1) ok + dev-cycle 보류 → 재트리거"
root=$(make_fixture 2592000)
echo "$(( now - 7200 ))" > "$root/markers/auth-pending-dev-cycle"
out=$(run_recovery "$root")
check "종료코드 0" 0 "$(cat "$root/rc")"
check "launchctl 1회" 1 "$(count_lines "$root/launchctl-calls")"
check "라벨·인자" "kickstart gui/$uid/com.inkbaduk.dev-cycle" "$(cat "$root/launchctl-calls" 2>/dev/null)"
check "pending 마커 삭제" no "$([ -f "$root/markers/auth-pending-dev-cycle" ] && echo yes || echo no)"
check "retriggered 마커 생성" yes "$([ -f "$root/markers/auth-retriggered-dev-cycle" ] && echo yes || echo no)"
check "런로그 1줄" 1 "$(count_lines "$root/docs/ops/state/log/dev-cycle-runs.log")"
check "런로그 문구" yes "$(grep -q '인증 회복 — watchdog 재트리거' "$root/docs/ops/state/log/dev-cycle-runs.log" && echo yes || echo no)"
check "stdout 요약" yes "$(echo "$out" | grep -q '재트리거: dev-cycle' && echo yes || echo no)"
check "알림 없음" 0 "$(count_lines "$root/notify-calls")"
rm -rf "$root"

echo "2) ok + orchestrator 보류 → 라벨 매핑이 다르다"
root=$(make_fixture 2592000)
echo "$(( now - 7200 ))" > "$root/markers/auth-pending-orchestrator"
out=$(run_recovery "$root")
check "종료코드 0" 0 "$(cat "$root/rc")"
check "orchestrator 라벨" "kickstart gui/$uid/com.inkbaduk.ops-orchestrator" "$(cat "$root/launchctl-calls" 2>/dev/null)"
rm -rf "$root"

echo "3) ok + 1h 전 재트리거 이력 → 루프 가드"
root=$(make_fixture 2592000)
echo "$(( now - 7200 ))" > "$root/markers/auth-pending-dev-cycle"
echo "$(( now - 3600 ))" > "$root/markers/auth-retriggered-dev-cycle"
out=$(run_recovery "$root")
check "종료코드 0" 0 "$(cat "$root/rc")"
check "launchctl 0회" 0 "$(count_lines "$root/launchctl-calls")"
check "incident 1건" 1 "$(grep -c '재트리거 실패(🟡 격상)' "$root/docs/ops/state/incidents.md")"
check "incident 제목에 잡 이름" 1 "$(grep -cE '^### WD-[0-9]+-[0-9]+ — dev-cycle 인증 회복 후 재트리거 실패' "$root/docs/ops/state/incidents.md")"
check "pending 마커 삭제" no "$([ -f "$root/markers/auth-pending-dev-cycle" ] && echo yes || echo no)"
rm -rf "$root"

echo "4) ok + 25h 전 재트리거 이력 → 가드 만료, 다시 재트리거"
root=$(make_fixture 2592000)
echo "$(( now - 7200 ))" > "$root/markers/auth-pending-dev-cycle"
echo "$(( now - 90000 ))" > "$root/markers/auth-retriggered-dev-cycle"
out=$(run_recovery "$root")
check "종료코드 0" 0 "$(cat "$root/rc")"
check "launchctl 1회" 1 "$(count_lines "$root/launchctl-calls")"
check "incident 없음" 0 "$(grep -c '재트리거 실패' "$root/docs/ops/state/incidents.md")"
rm -rf "$root"

echo "5) 만료 + 보류 → 알림만, 재트리거 없음"
root=$(make_fixture -3600)
echo "$(( now - 7200 ))" > "$root/markers/auth-pending-dev-cycle"
out=$(run_recovery "$root")
check "종료코드 0" 0 "$(cat "$root/rc")"
check "launchctl 0회" 0 "$(count_lines "$root/launchctl-calls")"
check "알림 1회" 1 "$(count_lines "$root/notify-calls")"
check "알림 문구" yes "$(grep -q '⛔ Claude 인증 만료' "$root/notify-calls" && echo yes || echo no)"
check "pending 마커 유지" yes "$([ -f "$root/markers/auth-pending-dev-cycle" ] && echo yes || echo no)"
rm -rf "$root"

echo "6) D-2 임박 → 경고 알림"
root=$(make_fixture 172800)
out=$(run_recovery "$root")
check "종료코드 0" 0 "$(cat "$root/rc")"
check "알림 1회" 1 "$(count_lines "$root/notify-calls")"
check "경고 문구" yes "$(grep -q '⚠️ Claude 인증 D-2' "$root/notify-calls" && echo yes || echo no)"
check "warn: 접두 제거" 0 "$(grep -c 'warn: ' "$root/notify-calls")"
check "launchctl 0회" 0 "$(count_lines "$root/launchctl-calls")"
rm -rf "$root"

echo "7) 확인 불가 warn → 알림 없음"
root=$(make_fixture 2592000)
echo "not json" > "$root/cred.json"
out=$(run_recovery "$root")
check "종료코드 0" 0 "$(cat "$root/rc")"
check "알림 0회" 0 "$(count_lines "$root/notify-calls")"
check "stdout에 확인 불가" yes "$(echo "$out" | grep -q '확인 불가' && echo yes || echo no)"
rm -rf "$root"

echo "8) ok + 보류 없음 → 무동작"
root=$(make_fixture 2592000)
out=$(run_recovery "$root")
check "종료코드 0" 0 "$(cat "$root/rc")"
check "launchctl 0회" 0 "$(count_lines "$root/launchctl-calls")"
check "알림 0회" 0 "$(count_lines "$root/notify-calls")"
check "런로그 생성 없음" 0 "$(ls "$root/docs/ops/state/log" | wc -l | tr -d ' ')"
check "incidents 빈 상태" 0 "$(count_lines "$root/docs/ops/state/incidents.md")"
rm -rf "$root"

echo "9) ok + 보류 → launchctl kickstart 실패"
root=$(make_fixture 2592000)
cat > "$root/fake-launchctl" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$(dirname "$0")/launchctl-calls"
exit 1
EOF
chmod +x "$root/fake-launchctl"
echo "$(( now - 7200 ))" > "$root/markers/auth-pending-dev-cycle"
out=$(run_recovery "$root")
check "종료코드 0" 0 "$(cat "$root/rc")"
check "런로그 실패 문구" 1 "$(grep -c '재트리거 실패(launchctl rc=1)' "$root/docs/ops/state/log/dev-cycle-runs.log")"
check "성공 문구는 없다" 0 "$(grep -c 'watchdog 재트리거' "$root/docs/ops/state/log/dev-cycle-runs.log")"
check "incident 1건" 1 "$(grep -cE '^### WD-[0-9]+-[0-9]+ — dev-cycle 재트리거 실패\(launchctl rc=1\)$' "$root/docs/ops/state/incidents.md")"
check "stdout 요약" yes "$(echo "$out" | grep -q '재트리거 실패: dev-cycle' && echo yes || echo no)"
check "pending 마커 삭제" no "$([ -f "$root/markers/auth-pending-dev-cycle" ] && echo yes || echo no)"
check "retriggered 마커 기록" yes "$([ -f "$root/markers/auth-retriggered-dev-cycle" ] && echo yes || echo no)"
rm -rf "$root"

echo ""
echo "통과 $pass / 실패 $fail"
[ "$fail" -eq 0 ]
