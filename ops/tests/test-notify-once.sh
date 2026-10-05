#!/usr/bin/env bash
# notify-once.sh의 날짜별 중복 억제(발송 성공 시에만 마커 생성)를 픽스처 NOTIFY로 검증한다.
set -euo pipefail
cd "$(dirname "$0")/../.."
. ops/lib/notify-once.sh

pass=0; fail=0
check() { # $1=설명 $2=기대값 $3=실제값
  if [ "$2" = "$3" ]; then echo "  ok — $1"; pass=$((pass+1))
  else echo "  FAIL — $1 (기대 $2, 실제 $3)"; fail=$((fail+1)); fi
}

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# 픽스처 NOTIFY — 호출 1건마다 로그에 한 줄, 종료코드는 FAKE_NOTIFY_RC로 제어.
cat > "$tmp/fake-notify.sh" <<'FIX'
#!/usr/bin/env bash
echo "$1" >> "$FAKE_NOTIFY_LOG"
exit "${FAKE_NOTIFY_RC:-0}"
FIX
chmod +x "$tmp/fake-notify.sh"

export MARKER_DIR="$tmp/markers"
export NOTIFY="$tmp/fake-notify.sh"
export FAKE_NOTIFY_LOG="$tmp/calls.log"
export NOTIFY_ONCE_DATE="2026-09-04"
: > "$FAKE_NOTIFY_LOG"

calls() { grep -c . "$FAKE_NOTIFY_LOG" || true; }

echo "1) 첫 호출 — 발송 1회 + 마커 생성"
rc=0; notify_once claude-auth "인증 만료" || rc=$?
check "exit 0" 0 "$rc"
check "발송 1회" 1 "$(calls)"
check "마커 생성" 1 "$([ -f "$MARKER_DIR/notify-once-claude-auth-2026-09-04" ] && echo 1 || echo 0)"

echo "2) 같은 키·같은 날 두 번째 호출 — 발송 없음"
rc=0; notify_once claude-auth "인증 만료" || rc=$?
check "exit 0" 0 "$rc"
check "발송 누적 1회 유지" 1 "$(calls)"

echo "3) 날짜가 바뀌면 다시 발송"
NOTIFY_ONCE_DATE="2026-09-05" notify_once claude-auth "인증 만료"
check "발송 누적 2회" 2 "$(calls)"
check "새 날짜 마커 생성" 1 "$([ -f "$MARKER_DIR/notify-once-claude-auth-2026-09-05" ] && echo 1 || echo 0)"

echo "4) 발송 실패 — 마커 미생성·exit 전파, 다음 호출에서 재시도"
rc=0; FAKE_NOTIFY_RC=7 notify_once claude-auth-warn "D-3 경고" || rc=$?
check "실패 exit code 전파" 7 "$rc"
check "발송 누적 3회" 3 "$(calls)"
check "마커 미생성" 0 "$([ -f "$MARKER_DIR/notify-once-claude-auth-warn-2026-09-04" ] && echo 1 || echo 0)"
rc=0; notify_once claude-auth-warn "D-3 경고" || rc=$?
check "재호출은 다시 발송" 4 "$(calls)"
check "재시도 성공 후 마커 생성" 1 "$([ -f "$MARKER_DIR/notify-once-claude-auth-warn-2026-09-04" ] && echo 1 || echo 0)"

echo "5) 다른 키는 독립"
notify_once content-stale "콘텐츠 stale"
check "발송 누적 5회" 5 "$(calls)"
check "claude-auth 마커 유지" 1 "$([ -f "$MARKER_DIR/notify-once-claude-auth-2026-09-04" ] && echo 1 || echo 0)"

echo
echo "통과 $pass / 실패 $fail"
[ "$fail" -eq 0 ]
