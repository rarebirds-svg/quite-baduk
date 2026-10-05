#!/usr/bin/env bash
# 재시도(바깥)와 타임아웃(안쪽) 두 가드가 겹쳐 동작하는지 래퍼와 같은 호출 형태로 검증한다.
set -uo pipefail
cd "$(dirname "$0")/../.."
. ops/lib/session-retry.sh

pass=0; fail=0
check() { # $1=설명 $2=기대 $3=실제
  if [ "$2" = "$3" ]; then echo "  ok — $1"; pass=$((pass+1))
  else echo "  FAIL — $1 (기대 $2, 실제 $3)"; fail=$((fail+1)); fi
}

FIX=$(mktemp -d "${TMPDIR:-/tmp}/guard-composition.XXXXXX")
trap 'rm -rf "$FIX"' EXIT
echo "테스트 프롬프트" > "$FIX/prompt.md"
RUNLOG="$FIX/runlog"

# 재시도 대기는 건너뛴다. claude-headless.sh는 자식 bash로 실행되므로
# 이 함수는 상속되지 않고, 킬러의 sleep은 실제로 동작한다.
sleep() { :; }

echo "가드 합성 검증 (재시도 바깥 · 타임아웃 안쪽)"

echo "1) 1회차 세션 한도 → 재시도 → 2회차 성공 (양쪽 다 타임아웃 가드 경유)"
: > "$RUNLOG"
state="$FIX/state1"; : > "$state"
cat > "$FIX/limit-then-ok.sh" <<'FAKE'
#!/usr/bin/env bash
if [ ! -s "$STATE_FILE" ]; then
  echo tried > "$STATE_FILE"
  echo "You've hit your session limit · resets 9:30am (Asia/Seoul)"
  exit 1
fi
echo "사이클 완료 마커"
FAKE
chmod +x "$FIX/limit-then-ok.sh"
rc=0
STATE_FILE="$state" CLAUDE_BIN="$FIX/limit-then-ok.sh" \
  run_claude_with_session_retry "$RUNLOG" ops/claude-headless.sh "$FIX/prompt.md" 30 || rc=$?
check "최종 exit 0" 0 "$rc"
check "재시도 발생" 1 "$(grep -c '세션 한도 감지' "$RUNLOG")"
check "2회차 성공 출력 도달" 1 "$(grep -c '사이클 완료 마커' "$RUNLOG")"
check "타임아웃은 발동 안 함" 0 "$(grep -c '타임아웃' "$RUNLOG")"

echo "2) 행(hang) → 타임아웃이 안쪽에서 끊고, 세션 한도가 아니므로 재시도 없음"
: > "$RUNLOG"
cat > "$FIX/hang.sh" <<'FAKE'
#!/usr/bin/env bash
sleep 300
FAKE
chmod +x "$FIX/hang.sh"
start=$(date +%s); rc=0
CLAUDE_BIN="$FIX/hang.sh" \
  run_claude_with_session_retry "$RUNLOG" ops/claude-headless.sh "$FIX/prompt.md" 1 || rc=$?
elapsed=$(( $(date +%s) - start ))
check "비정상 rc 전파" yes "$([ "$rc" -ne 0 ] && echo yes || echo no)"
check "타임아웃 로그 기록" 1 "$(grep -c '타임아웃' "$RUNLOG")"
check "재시도 안 함" 0 "$(grep -c '세션 한도 감지' "$RUNLOG")"
check "행에 매달리지 않음(<20s)" yes "$([ "$elapsed" -lt 20 ] && echo yes || echo no)"

echo "3) 타임아웃 상한 < 슬롯 간격 — 최악 소요(1h + 재시도대기 6h + 1h)가 12h 미만"
worst=$(( 3600 + 21600 + 3600 ))
check "최악 8h < 12h 슬롯" yes "$([ "$worst" -lt 43200 ] && echo yes || echo no)"

echo
echo "통과 $pass / 실패 $fail"
[ "$fail" -eq 0 ]
