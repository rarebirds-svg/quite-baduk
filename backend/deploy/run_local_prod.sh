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

# 기동 전에 스키마를 코드의 head에 맞춘다. 새 코드로 재기동되면서 마이그레이션이
# 빠져 세션 발급이 500으로 죽었던 OPS-20260907-01 재발 방지. 이미 head면 no-op.
# (백업 잡이 매일 04:00에 복원점을 남기므로 자동 적용의 위험은 낮다.)
alembic upgrade head

# launchd captures stdout/stderr; uvicorn already JSON-logs via structlog.
exec uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
