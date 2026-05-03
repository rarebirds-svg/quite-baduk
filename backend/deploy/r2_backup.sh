#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

DB="data/baduk.db"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP="/tmp/baduk-${STAMP}.db"

# .backup is atomic and respects WAL.
sqlite3 "${DB}" ".backup '${TMP}'"
gzip -9 "${TMP}"
rclone copy "${TMP}.gz" "r2:baduk-backups/" --progress
rm -f "${TMP}.gz"

# Keep last 30 days
rclone delete --min-age 30d "r2:baduk-backups/"
