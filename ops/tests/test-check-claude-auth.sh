#!/usr/bin/env bash
# check-claude-auth.sh의 만료 판정(ok/warn/fail)과 종료코드를 픽스처 자격증명으로 검증한다.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET="$REPO/ops/check-claude-auth.sh"

pass=0; fail=0
check() { # $1=설명 $2=기대값 $3=실제값
  if [ "$2" = "$3" ]; then echo "  ok — $1"; pass=$((pass+1))
  else echo "  FAIL — $1 (기대 $2, 실제 $3)"; fail=$((fail+1)); fi
}

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# now 픽스처: 2026-09-04 12:00:00 KST → epoch
NOW=$(date -j -f "%Y-%m-%d %H:%M:%S" "2026-09-04 12:00:00" +%s)
TOKEN="sk-ant-fixture-DO-NOT-PRINT"

write_cred() {  # write_cred <refreshTokenExpiresAt(ms)>
  printf '{"claudeAiOauth":{"accessToken":"%s","refreshToken":"%s","refreshTokenExpiresAt":%s}}\n' \
    "$TOKEN" "$TOKEN" "$1" > "$tmp/cred.json"
}

out=""; rc=0
run() {  # run [자격증명 명령] — 기본은 픽스처 파일 cat
  local cmd="${1:-cat $tmp/cred.json}"
  rc=0
  out=$(NOW="$NOW" CLAUDE_CREDENTIALS_CMD="$cmd" bash "$TARGET" 2>/dev/null) || rc=$?
}

prefix() { echo "$out" | head -1 | cut -d: -f1; }

echo "1) 만료까지 10일 12시간 → ok D-10"
write_cred $(( (NOW + 10 * 86400 + 43200) * 1000 ))
run
check "종료코드 0" 0 "$rc"
check "접두 ok" "ok" "$(prefix)"
check "D-10 표기" 1 "$(echo "$out" | grep -c 'D-10')"
check "토큰 미노출" 0 "$(echo "$out" | grep -c "$TOKEN")"

echo "2) 만료까지 71시간 (72h 경계 안쪽) → warn"
write_cred $(( (NOW + 71 * 3600) * 1000 ))
run
check "종료코드 2" 2 "$rc"
check "접두 warn" "warn" "$(prefix)"
check "/login 권장 문구" 1 "$(echo "$out" | grep -c 'claude /login 권장')"

echo "3) 이미 만료 (1시간 전) → fail"
write_cred $(( (NOW - 3600) * 1000 ))
run
check "종료코드 1" 1 "$rc"
check "접두 fail" "fail" "$(prefix)"
check "/login 필요 문구" 1 "$(echo "$out" | grep -c 'claude /login 필요')"

echo "4) JSON 깨짐 → 확인 불가 warn"
printf 'not a json {{{\n' > "$tmp/cred.json"
run
check "종료코드 2" 2 "$rc"
check "접두 warn" "warn" "$(prefix)"
check "확인 불가 문구" 1 "$(echo "$out" | grep -c '확인 불가')"

echo "5) 자격증명 명령 실패 → 확인 불가 warn"
run false
check "종료코드 2" 2 "$rc"
check "접두 warn" "warn" "$(prefix)"
check "확인 불가 문구" 1 "$(echo "$out" | grep -c '확인 불가')"

echo "6) 필드 없음 (다른 JSON) → 확인 불가 warn"
printf '{"other":{"x":1}}\n' > "$tmp/cred.json"
run
check "종료코드 2" 2 "$rc"
check "접두 warn" "warn" "$(prefix)"
check "확인 불가 문구" 1 "$(echo "$out" | grep -c '확인 불가')"

echo "7) 기본 자격증명 명령 — security에 넘기는 인자가 쪼개지지 않는다"
# 회귀 대상. 서비스명 "Claude Code-credentials"의 공백이 두 인자로 갈리면
# 실기에서만 '확인 불가'가 나고 테스트는 전부 통과해 버린다.
mkdir -p "$tmp/bin"
cat > "$tmp/bin/security" <<SHIM
#!/usr/bin/env bash
[ "\$1" = "find-generic-password" ] && [ "\$2" = "-s" ] \\
  && [ "\$3" = "Claude Code-credentials" ] && [ "\$4" = "-w" ] || exit 1
cat "$tmp/cred.json"
SHIM
chmod +x "$tmp/bin/security"
write_cred $(( (NOW + 10 * 86400 + 43200) * 1000 ))
rc=0
out=$(NOW="$NOW" PATH="$tmp/bin:$PATH" bash "$TARGET" 2>/dev/null) || rc=$?
check "종료코드 0" 0 "$rc"
check "접두 ok" "ok" "$(prefix)"

echo ""
echo "통과 $pass / 실패 $fail"
[ "$fail" -eq 0 ]
