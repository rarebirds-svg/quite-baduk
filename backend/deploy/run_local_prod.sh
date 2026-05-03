#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Activate venv
source .venv311/bin/activate

# Production env. Real secrets come from a sourced ~/.baduk.env on the
# Mac mini (see deploy/README.md). This script is checked in; the .env
# is not.
if [ -f "$HOME/.baduk.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$HOME/.baduk.env"
  set +a
fi

export APP_ENV=production
export KATAGO_MOCK=${KATAGO_MOCK:-false}
export KATAGO_BIN_PATH="$(pwd)/katago/bin/katago"
export DATABASE_URL=${DATABASE_URL:-"sqlite+aiosqlite:///./data/baduk.db"}

# launchd captures stdout/stderr; uvicorn already JSON-logs via structlog.
exec uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
