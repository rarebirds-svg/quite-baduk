#!/usr/bin/env bash
# launchd가 매주 일요일 03:00 호출 — prod venv에서 CWI 자동 수집 스크립트를 실행.
set -euo pipefail
# launchd는 로그인 셸 PATH를 상속하지 않는다 — Homebrew 경로(gh·claude 등)를 명시적으로 앞에 붙인다.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT/backend"

# prod backend의 .env 환경(DB_PATH 등)을 사용한다.
[ -f "$HOME/.baduk.env" ] && { set -a; . "$HOME/.baduk.env"; set +a; }

mkdir -p "$ROOT/docs/ops/state/log"
RUNLOG="$ROOT/docs/ops/state/log/content-ingest-runs.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] content-ingest 시작" >> "$RUNLOG"

# 신규 삽입 기보의 공개 URL을 받아둘 임시 파일 — ingest가 여기에 한 줄에 하나씩 쓴다.
NEWURLS="$(mktemp -t ingest-new-urls)"
trap 'rm -f "$NEWURLS"' EXIT
export CWI_NEW_URLS_FILE="$NEWURLS"

source .venv311/bin/activate
python -m scripts.ingest_cwi_weekly >> "$RUNLOG" 2>&1 \
  || echo "[$(date '+%Y-%m-%d %H:%M:%S')] 비정상 종료" >> "$RUNLOG"

# IndexNow 통보는 best-effort — 실패해도 ingest 결과에는 영향을 주지 않는다.
if [ -s "$NEWURLS" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] IndexNow 제출 $(wc -l < "$NEWURLS" | tr -d ' ')건" >> "$RUNLOG"
  bash "$ROOT/scripts/seo/indexnow-submit.sh" < "$NEWURLS" >> "$RUNLOG" 2>&1 \
    || echo "[$(date '+%Y-%m-%d %H:%M:%S')] IndexNow 제출 실패 — 무시하고 진행" >> "$RUNLOG"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 신규 0건 — IndexNow 생략" >> "$RUNLOG"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] content-ingest 종료" >> "$RUNLOG"
