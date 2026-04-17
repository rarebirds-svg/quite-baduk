#!/bin/sh
# Standalone backup script invoked by the backup service in docker-compose.
# Copies the SQLite DB to /backups with a dated filename and prunes >30-day files.
set -eu
SRC=${SRC:-/data/baduk.db}
DEST_DIR=${DEST_DIR:-/backups}
DATE=$(date +%Y-%m-%d)
mkdir -p "$DEST_DIR"
if [ -f "$SRC" ]; then
  cp "$SRC" "$DEST_DIR/baduk-$DATE.db"
  echo "backed up to $DEST_DIR/baduk-$DATE.db"
fi
find "$DEST_DIR" -name 'baduk-*.db' -mtime +30 -delete || true
