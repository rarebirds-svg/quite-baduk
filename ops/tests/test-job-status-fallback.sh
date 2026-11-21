#!/usr/bin/env bash
# job-status-fallback.sh가 래퍼 단계 실패를 job json에 fail로 대신 남기는지 픽스처로 검증한다.
set -uo pipefail
cd "$(dirname "$0")/../.."

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
# 라이브 트리 보호 — 헬퍼·report-job-status.sh 모두 ROOT 미설정 시 라이브 경로를 쓰므로 source 전에 고정한다.
export ROOT="$tmp/root"
JOBS="$ROOT/docs/ops/state/jobs"
. ops/lib/job-status-fallback.sh

pass=0; fail=0
check() { # $1=설명 $2=기대 $3=실제
  if [ "$2" = "$3" ]; then echo "  ok — $1"; pass=$((pass+1))
  else echo "  FAIL — $1 (기대 $2, 실제 $3)"; fail=$((fail+1)); fi
}
field() { # $1=json 경로 $2=키 — 파일·키가 없으면 "-"
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))[sys.argv[2]])' "$1" "$2" 2>/dev/null || echo "-"
}
write_ok() { # $1=잡 — 직전 성공 상태 픽스처
  mkdir -p "$JOBS"
  printf '{"job": "%s", "status": "ok", "summary": "이전 성공", "at": "2026-11-04T02:00:52+09:00"}\n' "$1" > "$JOBS/$1.json"
}
msg() { echo "래퍼 비정상 종료 — 실행 중 상태 보고 없음 ($1-runs.log 참조)"; }

echo "1) json 없음 → fail 생성"
report_fail_if_unreported t-none "$(date +%s)"
check "status fail" fail "$(field "$JOBS/t-none.json" status)"
check "job 이름" t-none "$(field "$JOBS/t-none.json" job)"
check "summary 문구" "$(msg t-none)" "$(field "$JOBS/t-none.json" summary)"

echo "2) 시작 전에 쓰인 ok → fail로 덮음"
write_ok t-stale
touch -t 202611040200 "$JOBS/t-stale.json"
report_fail_if_unreported t-stale "$(date +%s)"
check "status fail" fail "$(field "$JOBS/t-stale.json" status)"

echo "3) 시작 후에 쓰인 ok → 보존"
start=$(( $(date +%s) - 5 ))
write_ok t-fresh
report_fail_if_unreported t-fresh "$start"
check "status ok 유지" ok "$(field "$JOBS/t-fresh.json" status)"
check "summary 유지" "이전 성공" "$(field "$JOBS/t-fresh.json" summary)"

echo "4) report-job-status.sh 실패 → 함수 rc 0"
mkdir -p "$tmp/broken/docs/ops/state"; : > "$tmp/broken/docs/ops/state/jobs"   # jobs가 파일이라 mkdir -p 실패
rc=0; ROOT="$tmp/broken" report_fail_if_unreported t-broken "$(date +%s)" || rc=$?
check "rc 0" 0 "$rc"

echo "5) C 로케일(launchd 환경)에서도 한국어 summary 보존"
env -u LANG -u LC_CTYPE LC_ALL=C bash -c '. ops/lib/job-status-fallback.sh; report_fail_if_unreported t-locale 0'
check "summary 한국어 보존" "$(msg t-locale)" "$(field "$JOBS/t-locale.json" summary)"

echo "6) set -euo pipefail 래퍼 조합 — 기록이 실패해도 종료 마커까지 남는다"
RUNLOG="$tmp/t-wrap-runs.log"
ROOT="$tmp/broken" RUNLOG="$RUNLOG" bash -c '
  set -euo pipefail
  . ops/lib/job-status-fallback.sh
  START_EPOCH=$(date +%s)
  false \
    || { echo "[ts] 비정상 종료" >> "$RUNLOG"; report_fail_if_unreported t-wrap "$START_EPOCH"; }
  echo "[ts] t-wrap 종료" >> "$RUNLOG"
'
check "비정상 종료 마커" 1 "$(grep -c '비정상 종료' "$RUNLOG")"
check "종료 마커" 1 "$(grep -c 't-wrap 종료' "$RUNLOG")"

echo "7) 래퍼 배선 — json을 쓰는 네 잡만"
for job in dev-cycle content-draft analytics-weekly news-hook; do
  f="ops/run-$job.sh"
  check "$job source" 1 "$(grep -c '^\. ops/lib/job-status-fallback\.sh$' "$f")"
  check "$job START_EPOCH" 1 "$(grep -c '^START_EPOCH=\$(date +%s)$' "$f")"
  check "$job 호출" 1 "$(grep -c "report_fail_if_unreported $job \"\$START_EPOCH\"" "$f")"
  check "$job 문법" 0 "$(bash -n "$f" >/dev/null 2>&1; echo $?)"
done
check "orchestrator 미배선" 0 "$(grep -c 'report_fail_if_unreported' ops/run-orchestrator.sh)"

echo "8) 라이브 트리 미오염"
check "라이브 jobs에 t-*.json 없음" 0 "$(ls /Users/daegong/projects/baduk/docs/ops/state/jobs/ | grep -c '^t-')"

echo
echo "통과 $pass / 실패 $fail"
[ "$fail" -eq 0 ]
