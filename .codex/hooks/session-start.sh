#!/usr/bin/env bash
# SessionStart hook — 프로젝트 상태 요약
# stdin: session context JSON (무시)
# stdout: { systemMessage: "..." } for Claude Code UI
set -euo pipefail

repo="/Users/daegong/projects/baduk"
cd "$repo" 2>/dev/null || exit 0

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "detached")
uncommitted=$(git status --short 2>/dev/null | wc -l | tr -d ' ')
ahead=$(git rev-list --count '@{upstream}..HEAD' 2>/dev/null || echo 0)

web_status="down"; api_status="down"
lsof -i :3000 -sTCP:LISTEN >/dev/null 2>&1 && web_status="up"
lsof -i :8000 -sTCP:LISTEN >/dev/null 2>&1 && api_status="up"

msg="📝 baduk · branch=${branch} · uncommitted=${uncommitted} · ahead=${ahead} · web:${web_status} api:${api_status}"
printf '{"systemMessage":"%s","continue":true}\n' "$msg"
