#!/usr/bin/env bash
# Stop hook — 세션 턴 종료 시 터미널 벨 1회
# stdin: 무시
printf '\a' >&2
exit 0
