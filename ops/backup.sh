#!/usr/bin/env bash
# prod SQLite DB의 로컬 다중 세대(일·주·월) 백업 생성 + 보존 정책 정리.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

DB="$ROOT/backend/data/baduk.db"
DEST="$HOME/baduk-backups"
DAILY_KEEP=14
WEEKLY_KEEP=8
MONTHLY_KEEP=12

[ -f "$DB" ] || { echo "prod DB 없음: $DB" >&2; exit 1; }
mkdir -p "$DEST/daily" "$DEST/weekly" "$DEST/monthly"

STAMP="$(date +%Y%m%dT%H%M%S)"
TMP="$(mktemp -t baduk-backup.XXXXXX)"

# .backup 은 원자적이고 WAL을 존중한다.
sqlite3 "$DB" ".backup '$TMP'"
gzip -9 "$TMP"
SNAP="baduk-$STAMP.db.gz"
mv "$TMP.gz" "$DEST/daily/$SNAP"
echo "daily 백업 생성: $DEST/daily/$SNAP"

if [ "$(date +%u)" = "7" ]; then
  cp "$DEST/daily/$SNAP" "$DEST/weekly/$SNAP"
  echo "weekly 티어 복사: $SNAP"
fi
if [ "$(date +%d)" = "01" ]; then
  cp "$DEST/daily/$SNAP" "$DEST/monthly/$SNAP"
  echo "monthly 티어 복사: $SNAP"
fi

# 티어별 보존 정리 — 최신순 정렬 후 keep 개수 초과분(오래된 것) 삭제.
prune() {
  local dir="$1" keep="$2" f
  for f in $(ls -1t "$dir" 2>/dev/null | tail -n +"$((keep + 1))"); do
    rm -f "$dir/$f"
    echo "보존 정리: $dir/$f"
  done
}
prune "$DEST/daily" "$DAILY_KEEP"
prune "$DEST/weekly" "$WEEKLY_KEEP"
prune "$DEST/monthly" "$MONTHLY_KEEP"

echo "백업 완료."
