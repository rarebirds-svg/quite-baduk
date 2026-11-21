#!/usr/bin/env bash
# 헤드리스 잡이 쓰는 Claude 인증의 남은 기간을 ok/warn/fail 한 줄로 보고한다.
# - 장기 토큰 파일(claude setup-token, 1년)이 있으면 그것이 헤드리스 잡의 인증이므로
#   파일 저장 시각 + 365일을 만료로 추정해 판정한다.
# - 없으면 키체인의 /login OAuth refresh 토큰(약 30일) 만료 시각으로 판정한다.
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

# 장기 토큰 파일. claude-headless.sh가 같은 경로를 읽어 CLAUDE_CODE_OAUTH_TOKEN으로 쓴다.
TOKEN_FILE="${CLAUDE_TOKEN_FILE:-$HOME/.config/inkbaduk/claude-oauth-token}"
TOKEN_LIFETIME_SECS=31536000   # setup-token 유효기간 1년(공식 문서). 저장 시각 기준 추정
TOKEN_WARN_SECS=1209600        # 14일 — 사람이 재발급할 여유를 넉넉히 준다

fmt_date() {  # epoch → MM-DD HH:MM. macOS(date -r)와 GNU(date -d @) 모두 지원
  date -r "$1" '+%m-%d %H:%M' 2>/dev/null || date -d "@$1" '+%m-%d %H:%M'
}
# GNU stat를 먼저 시도한다. GNU의 `stat -f`는 실패해도 파일시스템 정보를 stdout에
# 찍어 결과를 오염시키지만, BSD(macOS) stat은 `-c`를 거부할 때 stdout이 비어 있다.
file_mtime() { stat -c %Y "$1" 2>/dev/null || stat -f %m "$1"; }
file_mode() { stat -c %a "$1" 2>/dev/null || stat -f %Lp "$1"; }

if [ -s "$TOKEN_FILE" ]; then
  # 토큰 값은 읽지 않는다 — 파일의 존재·권한·저장 시각만 본다.
  mode=$(file_mode "$TOKEN_FILE")
  case "$mode" in
    600|400) ;;
    *) echo "warn: Claude 장기 토큰 파일 권한 $mode — chmod 600 필요"; exit 2 ;;
  esac
  expires_s=$(( $(file_mtime "$TOKEN_FILE") + TOKEN_LIFETIME_SECS ))
  expires_str=$(fmt_date "$expires_s")
  remain=$(( expires_s - NOW ))
  if [ "$remain" -lt 0 ]; then
    echo "fail: Claude 장기 토큰 만료 추정 ($expires_str) — claude setup-token 재발급 필요"
    exit 1
  fi
  days=$(( remain / 86400 ))
  if [ "$remain" -le "$TOKEN_WARN_SECS" ]; then
    echo "warn: Claude 장기 토큰 D-$days (만료 추정 $expires_str) — claude setup-token 재발급 권장"
    exit 2
  fi
  echo "ok: Claude 장기 토큰 D-$days (만료 추정 $expires_str)"
  exit 0
fi

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
expires_str=$(fmt_date "$expires_s")
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
