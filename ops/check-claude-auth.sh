#!/usr/bin/env bash
# 키체인의 Claude OAuth refresh 토큰 만료 시각을 읽어 남은 기간을 ok/warn/fail 한 줄로 보고한다.
set -euo pipefail
# 예기치 못한 실패는 warn(2)로 떨어뜨린다 — rc 1은 "만료" 단정에만 쓴다.
trap 'exit 2' ERR

# 자격증명 취득 명령. 테스트는 픽스처 파일 cat으로 대체한다.
# 기본값을 별도 변수에 둔다 — ${VAR:-...} 안에 겹따옴표를 중첩하면 따옴표가 벗겨져
# 서비스명이 두 인자로 쪼개진다.
DEFAULT_CREDENTIALS_CMD="security find-generic-password -s 'Claude Code-credentials' -w"
CREDENTIALS_CMD="${CLAUDE_CREDENTIALS_CMD:-$DEFAULT_CREDENTIALS_CMD}"
NOW="${NOW:-$(date +%s)}"
WARN_SECS=259200   # 72h — 이 안쪽이면 재로그인을 권고한다

unknown() {  # 확인 불가는 만료 단정이 아니라 warn(2)이다
  echo "warn: Claude 인증 확인 불가 ($1)"
  exit 2
}

# 토큰 값은 어떤 경로로도 출력하지 않는다 — 아래에서 만료 epoch(ms)만 꺼내 쓴다.
raw=$(eval "$CREDENTIALS_CMD" 2>/dev/null) || unknown "자격증명 명령 실패"
[ -n "$raw" ] || unknown "자격증명 응답 없음"

py_rc=0
expires_ms=$(printf '%s' "$raw" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(3)
try:
    print(int(data["claudeAiOauth"]["refreshTokenExpiresAt"]))
except (KeyError, TypeError, ValueError):
    sys.exit(4)
' 2>/dev/null) || py_rc=$?

case "$py_rc" in
  0) ;;
  3) unknown "JSON 파싱 실패" ;;
  *) unknown "만료 필드 없음" ;;
esac

expires_s=$(( expires_ms / 1000 ))
expires_str=$(date -r "$expires_s" '+%m-%d %H:%M')
remain=$(( expires_s - NOW ))

if [ "$remain" -lt 0 ]; then
  echo "fail: Claude 인증 만료 ($expires_str) — claude /login 필요"
  exit 1
fi

days=$(( remain / 86400 ))
if [ "$remain" -le "$WARN_SECS" ]; then
  echo "warn: Claude 인증 D-$days (만료 $expires_str) — claude /login 권장"
  exit 2
fi

echo "ok: Claude 인증 D-$days (만료 $expires_str)"
exit 0
