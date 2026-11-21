# 래퍼 단계 실패 json fail 기록 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** json을 쓰는 네 잡의 래퍼가 비정상 종료로 끝났고 이번 실행 중 상태 보고가 없었으면 `state/jobs/<job>.json`에 `fail`을 대신 남긴다.

**Architecture:** `ops/lib/job-status-fallback.sh`에 함수 하나(`report_fail_if_unreported`)를 두고, 네 run-*.sh가 session-retry.sh처럼 source해 기존 `비정상 종료` 분기에서 호출한다. "이번 실행 중 보고"는 json mtime ≥ 실행 시작 epoch로 판정한다.

**Tech Stack:** bash(macOS BSD 유틸), 기존 `ops/report-job-status.sh`(python3로 json 기록).

**Spec:** `docs/superpowers/specs/2026-11-09-ops-wrapper-fail-status-design.md`

## Global Constraints

- macOS 전용 셸이다. mtime은 `stat -f %m`, GNU 전용 옵션 금지.
- 신규 소스 파일은 셰뱅 바로 다음 줄에 역할을 설명하는 한국어 한 줄 주석(AGENTS.md 규칙 6), 콜론으로 끝내지 않는다.
- 테스트는 `ROOT`를 임시 디렉터리로 export한 **뒤에** source·호출한다. 헬퍼와 `report-job-status.sh` 모두 ROOT 미설정 시 라이브 트리(`/Users/daegong/projects/baduk`)에 쓴다.
- run-*.sh는 `ROOT`가 라이브로 하드코딩돼 테스트에서 실행하지 않는다. `bash -n`과 grep 배선 검사만 한다.
- summary 문구는 정확히 `래퍼 비정상 종료 — 실행 중 상태 보고 없음 (<job>-runs.log 참조)`.
- 기존 ops 테스트 7종 무회귀(기준선 140 검사 통과, 실패 0).
- 커밋은 Conventional Commits, `fix(ops):` 프리픽스, 제목·본문 한국어, 트레일러 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- launchd의 C 로케일에서 한국어 summary가 깨지지 않고 json에 들어가야 한다 — 케이스 5가 고정.
- `set -euo pipefail` 래퍼에서 json 기록이 실패해도 `<잡> 종료` 마커는 반드시 남아야 한다(check-staleness 판정 문법) — 케이스 6이 고정.
- Claude가 상태를 쓴 뒤 래퍼가 비정상 종료(타임아웃 킬, 종료 시 오류)해도 Claude의 보고가 보존돼야 한다 — 케이스 3이 고정.
- 테스트가 라이브 `state/jobs/`에 `t-*.json`을 만들면 다이제스트 `jobs` 합산이 오염된다 — 케이스 8이 고정.
- 실행 중 git 조작(stash·checkout)이 json mtime을 바꾸면 보고한 것으로 오인해 fail을 남기지 않는다. 현행과 같은 미감지라 회귀가 아니므로 테스트 없이 리뷰어 확인 항목으로 둔다.

---

### Task 1: 래퍼 실패 시 job json에 fail 기록

**Files:**
- Create: `ops/lib/job-status-fallback.sh`
- Create: `ops/tests/test-job-status-fallback.sh`
- Modify: `ops/run-dev-cycle.sh`, `ops/run-content-draft.sh`, `ops/run-analytics-weekly.sh`, `ops/run-news-hook.sh` (각 15~21행 부근 실행 블록)
- Modify: `docs/ops/orchestrator-prompt.md` (`jobs` 항목, 38~42행)

**Interfaces:**
- Consumes: `ops/report-job-status.sh <job> <ok|warn|fail> <summary>` — `ROOT` 환경변수(기본 라이브 경로) 아래 `docs/ops/state/jobs/<job>.json`을 덮어쓴다. 실패 시 비0 종료.
- Produces: `report_fail_if_unreported <job> <start_epoch>` — 반환값은 항상 0.

- [ ] **Step 1: 실패하는 테스트 작성** — `ops/tests/test-job-status-fallback.sh`

```bash
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
```

- [ ] **Step 2: 실패 확인**

Run: `bash ops/tests/test-job-status-fallback.sh`
Expected: `ops/lib/job-status-fallback.sh: No such file or directory`로 source 실패, 비0 종료.

- [ ] **Step 3: `report_fail_if_unreported <job> <start_epoch>`를 `ops/lib/job-status-fallback.sh`에 구현**

헤더는 `#!/usr/bin/env bash` + 한국어 역할 주석(예: `# 래퍼 단계 실패로 잡이 상태를 못 남겼을 때 job json에 fail을 대신 기록하는 공용 헬퍼 (run-*.sh가 source).`). session-retry.sh처럼 `set` 옵션을 바꾸지 않는다(source하는 쪽 옵션을 따른다). 함수 규칙은 다음과 같다.
- `local root="${ROOT:-/Users/daegong/projects/baduk}"`, json = `$root/docs/ops/state/jobs/$job.json`
- json이 있고 `stat -f %m` ≥ `start_epoch`이면 `return 0`
- 아니면 `ROOT="$root" bash "$(dirname "${BASH_SOURCE[0]}")/../report-job-status.sh" "$job" fail "<summary>"`, 출력은 버리고 실패는 무시
- 마지막은 `return 0`

- [ ] **Step 4: 네 래퍼 배선** — 각 run-*.sh의 `. ops/lib/session-retry.sh`부터 실패 분기까지를 다음 모양으로 바꾼다(`<job>`·프롬프트 경로는 파일별 기존 값).

```bash
# 비정상 종료인데 이번 실행 중 상태 보고가 없었으면 job json에 fail을 대신 남긴다(ops/lib/job-status-fallback.sh).
. ops/lib/session-retry.sh
. ops/lib/job-status-fallback.sh
START_EPOCH=$(date +%s)
run_claude_with_session_retry "$RUNLOG" \
  ops/claude-headless.sh docs/ops/<job-prompt>.md \
  || { echo "[$(date '+%Y-%m-%d %H:%M:%S')] 비정상 종료" >> "$RUNLOG"
       report_fail_if_unreported <job> "$START_EPOCH"; }
```

기존 15~17행 주석(재시도 바깥·타임아웃 안쪽 설명)은 그대로 두고, 새 주석 한 줄은 그 아래에 붙인다.

- [ ] **Step 5: 오케스트레이터 지침 한 문장** — `docs/ops/orchestrator-prompt.md` `jobs` 항목 끝("…다이제스트에 남는다.") 다음에 같은 들여쓰기로 추가한다.

`래퍼 단계에서 죽은 실행(claude 기동 전 사망·한도·타임아웃)도 래퍼가 \`fail\`(summary \`래퍼 비정상 종료 — …\`)로 남기므로, 이 summary면 원인은 \`state/log/<잡>-runs.log\`에서 확인한다.`

- [ ] **Step 6: 통과 확인**

Run: `bash ops/tests/test-job-status-fallback.sh`
Expected: 마지막 줄 `통과 N / 실패 0`, rc 0.
Run: 기존 7종 각각 `bash ops/tests/test-<name>.sh`
Expected: 모두 `실패 0`(`test-claude-headless.sh`는 `fail=0`).

- [ ] **Step 7: 커밋**

```bash
git add ops/lib/job-status-fallback.sh ops/tests/test-job-status-fallback.sh \
  ops/run-dev-cycle.sh ops/run-content-draft.sh ops/run-analytics-weekly.sh ops/run-news-hook.sh \
  docs/ops/orchestrator-prompt.md
git commit -m "fix(ops): 래퍼 단계 실패 시 job json에 fail을 대신 기록"
```

## 결정 메모 (context notes)

- 태스크를 하나로 묶었다. 헬퍼만으로는 효과가 없고 배선만으로는 동작하지 않아, 리뷰어가 한쪽만 승인할 이유가 없다.
- 체크리스트·결정 메모는 이 리포 관례(별도 checklist.md 미커밋)에 맞춰 이 문서 안에 둔다.
- 오케스트레이터 재트리거 정책 확대는 범위 밖이다. PR 본문에 후속 후보로 적는다.
