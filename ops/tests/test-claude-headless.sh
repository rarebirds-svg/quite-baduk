#!/usr/bin/env bash
# claude-headless.sh의 타임아웃·exit code 전파를 가짜 claude 바이너리로 검증한다.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET="$REPO/ops/claude-headless.sh"

pass=0
fail=0

check() {  # check <설명> <기대> <실제>
  local desc="$1" expect="$2" got="$3"
  if [ "$got" = "$expect" ]; then
    echo "  ok — $desc"
    pass=$(( pass + 1 ))
  else
    echo "  FAIL — $desc (기대 $expect, 실제 $got)"
    fail=$(( fail + 1 ))
  fi
}

# mktemp -t의 템플릿 규칙이 macOS/Linux에서 달라 경로 직접 지정(양쪽 동작).
FIX=$(mktemp -d "${TMPDIR:-/tmp}/claude-headless-fixture.XXXXXX")
trap 'rm -rf "$FIX"' EXIT
echo "테스트 프롬프트" > "$FIX/prompt.md"

make_fake() {  # make_fake <파일명> <본문…> → 실행권한 있는 가짜 claude 경로 출력
  local path="$FIX/$1"; shift
  printf '#!/usr/bin/env bash\n%s\n' "$*" > "$path"
  chmod +x "$path"
  echo "$path"
}

echo "claude-headless.sh 검증"

# 1) 정상 종료 — rc 0, 출력 통과, 타임아웃 메시지 없음
fake=$(make_fake ok.sh 'echo "사이클 완료 마커"')
out=$(CLAUDE_BIN="$fake" bash "$TARGET" "$FIX/prompt.md" 5 2>&1); rc=$?
check "정상 종료 rc" 0 "$rc"
echo "$out" | grep -q "사이클 완료 마커" && got=yes || got=no
check "stdout 통과" yes "$got"
echo "$out" | grep -q "타임아웃" && got=yes || got=no
check "정상 종료엔 타임아웃 메시지 없음" no "$got"

# 2) 실패 exit code 그대로 전파 — 호출측 '비정상 종료' 기록의 전제
fake=$(make_fake fail.sh 'exit 7')
CLAUDE_BIN="$fake" bash "$TARGET" "$FIX/prompt.md" 5 >/dev/null 2>&1; rc=$?
check "실패 코드 전파" 7 "$rc"

# 3) 행(hang) → 타임아웃 강제 종료 — 비정상 rc + 타임아웃 로그, 슬롯을 막지 않는다
fake=$(make_fake hang.sh 'sleep 60')
t0=$(date +%s)
out=$(CLAUDE_BIN="$fake" bash "$TARGET" "$FIX/prompt.md" 2 2>&1); rc=$?
elapsed=$(( $(date +%s) - t0 ))
[ "$rc" -ne 0 ] && got=yes || got=no
check "타임아웃 시 비정상 rc" yes "$got"
echo "$out" | grep -q "타임아웃 2s 초과" && got=yes || got=no
check "타임아웃 로그 기록" yes "$got"
[ "$elapsed" -lt 25 ] && got=yes || got=no
check "행에 매달리지 않고 복귀(${elapsed}s)" yes "$got"

# 4) 프롬프트 파일 없음 — rc 2
fake=$(make_fake noop.sh 'exit 0')
CLAUDE_BIN="$fake" bash "$TARGET" "$FIX/없는파일.md" 5 >/dev/null 2>&1; rc=$?
check "프롬프트 파일 없음 rc" 2 "$rc"

echo
echo "결과: pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
