#!/usr/bin/env bash
# 헤드리스 Claude 1회 실행 + 타임아웃 가드 — run-*.sh 래퍼들의 공용 러너.
#
# 배경: launchd는 같은 라벨의 인스턴스가 살아있으면 다음 슬롯을 건너뛴다. 따라서
# 타임아웃 없는 헤드리스 호출이 한 번 행(hang)에 걸리면 그 잡의 슬롯을 무기한 막는다.
# 실제 사고를 겪은 가드는 아니다 — 2026-08-30 WD-20260830-* 연쇄의 실제 원인은
# 09:00 세션 한도 종료(09:03:42 마커 존재, 행 아님)와 20:59:17 재부팅에 따른 21:00
# 트리거 유실이었다(incidents OPS-20260830-01). 이 가드는 아직 겪지 않은 행에 대한
# 예방책이다. macOS에는 GNU timeout이 기본 없어 백그라운드 킬러 프로세스로 구현한다.
#
# 사용: claude-headless.sh <프롬프트파일> [타임아웃초]
# - 타임아웃 기본 3600s (env CLAUDE_TIMEOUT_SECS로도 지정). 전 잡 정상 소요의
#   여유 배수다(최장 content-draft ~8분). 어떤 잡도 슬롯 간격(최소 12h)을 넘겨
#   매달릴 수 없다.
# - 타임아웃 시 프로세스 그룹째 TERM → 15s 유예 → KILL. claude가 띄운 자식
#   (MCP 서버·플러그인 프로세스)까지 함께 정리된다 — claude PID만 죽이면 고아
#   자식이 런로그 fd를 물고 살아남는다. exit code는 비정상(≠0)으로 전파돼
#   호출측 "비정상 종료" 기록과 check-staleness의 실패 판정 문법에 그대로 얹힌다.
# - stdout/stderr는 호출측 리다이렉션을 따른다(런로그 append).
set -euo pipefail

PROMPT_FILE="${1:?usage: claude-headless.sh <prompt-file> [timeout-secs]}"
TIMEOUT_SECS="${2:-${CLAUDE_TIMEOUT_SECS:-3600}}"
CLAUDE_BIN="${CLAUDE_BIN:-/opt/homebrew/bin/claude}"   # 테스트가 가짜 바이너리로 덮어쓴다

if [ ! -f "$PROMPT_FILE" ]; then
  echo "claude-headless.sh: 프롬프트 파일 없음 — $PROMPT_FILE" >&2
  exit 2
fi

# set -m: 백그라운드 claude가 독립 프로세스 그룹(PGID=PID)을 갖게 해
# 타임아웃 시 그룹째 kill 할 수 있게 한다.
set -m
"$CLAUDE_BIN" -p "$(cat "$PROMPT_FILE")" \
  --dangerously-skip-permissions \
  --channels plugin:telegram@claude-plugins-official &
claude_pid=$!
set +m

(
  # sleep의 stdout/stderr를 닫는다 — 킬러가 죽은 뒤 고아 sleep이 호출자의
  # 파이프 fd를 물고 있으면 파이프/명령치환 호출자가 sleep 만료까지 기다리게 된다.
  sleep "$TIMEOUT_SECS" >/dev/null 2>&1
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 타임아웃 ${TIMEOUT_SECS}s 초과 — claude(PGID ${claude_pid}) 그룹 강제 종료"
  kill -- -"$claude_pid" 2>/dev/null || exit 0
  sleep 15 >/dev/null 2>&1
  kill -9 -- -"$claude_pid" 2>/dev/null || true
) &
killer_pid=$!

rc=0
wait "$claude_pid" || rc=$?
kill "$killer_pid" 2>/dev/null || true
exit "$rc"
