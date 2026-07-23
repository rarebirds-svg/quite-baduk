#!/usr/bin/env bash
# 네이버 IndexNow 제출 — 새·변경 URL을 검색엔진에 즉시 통보해 재크롤을 앞당긴다.
# 사용: indexnow-submit.sh <url> [url...]   또는   cat urls.txt | indexnow-submit.sh
set -euo pipefail

KEY="57a57895c60e723b0f37a1a41c0fce2d"
HOST="inkbaduk.com"
ENDPOINT="https://searchadvisor.naver.com/indexnow"
KEYLOC="https://${HOST}/${KEY}.txt"

# 인자로 URL을 받거나, 없으면 stdin에서 한 줄에 하나씩 읽는다.
urls=("$@")
if [ ${#urls[@]} -eq 0 ]; then
  while IFS= read -r line; do
    line="${line%%#*}"; line="$(echo "$line" | tr -d '[:space:]')"
    [ -n "$line" ] && urls+=("$line")
  done
fi
if [ ${#urls[@]} -eq 0 ]; then
  echo "제출할 URL이 없습니다." >&2
  exit 1
fi

# JSON urlList 구성.
list=""
for u in "${urls[@]}"; do list="${list}\"${u}\","; done
list="[${list%,}]"

body="{\"host\":\"${HOST}\",\"key\":\"${KEY}\",\"keyLocation\":\"${KEYLOC}\",\"urlList\":${list}}"

echo "IndexNow → ${ENDPOINT} (${#urls[@]}개 URL)"
curl -sS -X POST "$ENDPOINT" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d "$body" \
  -w "\nHTTP %{http_code}\n"
