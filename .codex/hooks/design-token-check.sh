#!/usr/bin/env bash
# PostToolUse hook — Write/Edit 이후 하드코딩 색상/이모지 검출
# stdin: { tool_input:{file_path}, tool_response:{filePath} }
# stdout: { systemMessage } if violations found
set -euo pipefail

payload=$(cat)
file=$(echo "$payload" | jq -r '.tool_response.filePath // .tool_input.file_path // empty' 2>/dev/null)

# 대상 경로가 아니면 종료 (웹 UI 소스만)
case "$file" in
  */web/components/*|*/web/app/*|*/web/lib/tokens.*) ;;
  *) exit 0 ;;
esac

[ -f "$file" ] || exit 0

# .tsx / .ts / .css 만
case "$file" in
  *.tsx|*.ts|*.css|*.jsx|*.js) ;;
  *) exit 0 ;;
esac

# 6자리 hex 색상 검출 (최대 5건)
colors=$(grep -nE '#[0-9a-fA-F]{6}\b' "$file" 2>/dev/null | head -5 || true)
# 이모지: 공통 UI 이모지만 정확히 매칭
emojis=$(grep -nE '🌑|🌓|🌕|🎯|🔔|⭐|✨|🎨|🌙|☀️|🌞|🏆|🎮|♟️|🀄' "$file" 2>/dev/null | head -3 || true)

warnings=""
if [ -n "$colors" ]; then
  warnings="${warnings}⚠ 하드코딩 색상 — bg-paper/text-ink/border-oxblood 등 토큰 권장:"$'\n'"${colors}"$'\n'
fi
if [ -n "$emojis" ]; then
  warnings="${warnings}⚠ 이모지 — Lucide 아이콘 권장:"$'\n'"${emojis}"$'\n'
fi

if [ -n "$warnings" ]; then
  jq -n --arg msg "$warnings" '{systemMessage: $msg, continue: true}'
fi
exit 0
