# 래퍼 단계 실패를 job json에 fail로 남기기 — 설계

- 날짜: 2026-11-09
- 계기: OPS-20261107-01. 11/7 `/opt/homebrew/bin/claude` 소실로 content-draft 02:00 실행이 claude 기동 전에 죽었다. job json은 Claude가 실행 중에 `ops/report-job-status.sh`를 불러야만 갱신되므로 직전 성공(11/4)의 `ok`가 그대로 남았다. 오케스트레이터 `jobs` 행은 json `status`만 합산하므로 11/8 am·pm과 11/9 am 다이제스트가 모두 "4/4 ok"였고, watchdog은 마지막 성공 기준 5d 임계라 실패 48.5h 뒤에야 첫 stale을 기록했다. 실패에서 재트리거까지 67h가 걸렸다. 9/14 월간 지출 한도(OPS-20260914-01)와 OAuth 만료 사고도 같은 구조였다.
- 목표: json을 쓰는 네 잡(`dev-cycle`·`content-draft`·`analytics-weekly`·`news-hook`)의 래퍼가 비정상 종료로 끝났고 이번 실행 중 상태 보고가 없었다면, 래퍼가 json에 `status: fail`을 대신 남긴다. 다음 다이제스트의 `jobs` 행이 곧바로 ❌가 된다.

## 범위 밖 (Non-goals)

- 오케스트레이터 재트리거 정책(`docs/ops/autonomy-policy.md`)은 바꾸지 않는다. 지금 화이트리스트는 watchdog stale 잡만 재트리거하므로 json `fail`은 ❌로 드러날 뿐이고, 재트리거 범위 확대는 별도 판단이다.
- watchdog 임계(`ops/check-staleness.sh`)는 바꾸지 않는다.
- `run-orchestrator.sh`·`run-content-ingest.sh`는 손대지 않는다. 둘 다 job json을 쓰지 않는다.
- Claude가 rc 0으로 끝났지만 상태 보고를 빠뜨린 경우는 다루지 않는다(래퍼가 실패를 알 수 없다).
- 런로그에서 실패 원인 문구를 뽑아 summary에 넣지 않는다. 원인은 런로그에 있고 summary는 그 위치만 가리킨다.

## 설계

### 공용 헬퍼 `ops/lib/job-status-fallback.sh`

`ops/lib/session-retry.sh`처럼 run-*.sh가 source하는 함수 하나를 둔다.

- `report_fail_if_unreported <job> <start_epoch>`
- json 경로는 `${ROOT:-/Users/daegong/projects/baduk}/docs/ops/state/jobs/<job>.json`이다. `report-job-status.sh`와 같은 해석이다.
- json이 있고 mtime(`stat -f %m`)이 `start_epoch` 이상이면 이번 실행 중 Claude가 이미 쓴 것으로 보고 아무것도 하지 않는다. Claude가 남긴 `ok`·`warn`·`fail`이 래퍼의 추정보다 구체적이다.
- 그 밖의 경우(json 없음, 또는 시작 전에 쓰인 json)에는 `ops/report-job-status.sh <job> fail "래퍼 비정상 종료 — 실행 중 상태 보고 없음 (<job>-runs.log 참조)"`를 호출한다. 스크립트 위치는 헬퍼 파일 기준 상대 경로(`../report-job-status.sh`)로 찾고, 앞에서 해석한 ROOT를 환경변수로 명시 전달한다.
- 항상 0을 반환한다. 래퍼는 `set -euo pipefail`이라 이 호출이 실패하면 뒤따르는 `<잡> 종료` 마커가 기록되지 않고, check-staleness의 판정 문법(`비정상 종료` → `종료` 쌍)이 깨진다.

### 래퍼 4종 배선

`run-dev-cycle.sh`·`run-content-draft.sh`·`run-analytics-weekly.sh`·`run-news-hook.sh` 각각에 세 가지를 더한다.

1. `. ops/lib/session-retry.sh` 다음 줄에 `. ops/lib/job-status-fallback.sh`
2. `run_claude_with_session_retry` 호출 직전에 `START_EPOCH=$(date +%s)`
3. 기존 실패 분기 `|| echo "[…] 비정상 종료" >> "$RUNLOG"`를 `|| { echo "[…] 비정상 종료" >> "$RUNLOG"; report_fail_if_unreported <job> "$START_EPOCH"; }`로 넓힌다.

### 문서

`docs/ops/orchestrator-prompt.md`의 `jobs` 항목에 한 문장을 더한다. 래퍼 단계 실패도 래퍼가 `fail`(summary `래퍼 비정상 종료 — …`)로 남기며 원인은 `<잡>-runs.log`에서 확인한다는 내용이다.

## 결정 메모

- **mtime vs `at` 필드.** mtime은 python 없이 `stat -f %m` 한 번으로 끝난다. ops 스크립트는 이미 macOS 전용(`date -j` 등)이라 BSD stat을 써도 된다. 같은 초 경계는 `-ge`로 "이번 실행 중 보고"로 친다. 직전 실행의 json이 이번 시작과 같은 초에 쓰일 수는 없다(슬롯 간격이 시간 단위).
- **공용 헬퍼 vs 래퍼 인라인.** 같은 로직을 네 벌 복제하지 않고 session-retry.sh와 같은 source 패턴을 따른다.
- **session-retry 함수에 넣지 않은 이유.** 오케스트레이터도 `run_claude_with_session_retry`를 쓰지만 job json이 없다. 그 안에 넣으면 `orchestrator.json`이 생겨 다이제스트 `jobs` 합산 대상이 바뀐다.
- **fail vs warn.** 잡이 아예 돌지 못한 것이므로 `fail`이다. `jobs` 행은 fail이 하나라도 있으면 ❌이고, 다음 실행이 성공해 Claude가 `ok`로 덮을 때까지 남는다(기존 설계 그대로).
- **인증 만료 경로.** session-retry가 `auth-pending-<job>` 마커를 남기고 rc≠0을 돌려주면 래퍼가 json에 fail을 남긴다. check-auth-recovery·check-staleness는 json을 읽지 않아 상호작용이 없다. 재로그인 뒤 재트리거가 성공하면 Claude가 `ok`로 덮는다.
- **세션 한도 재시도.** `START_EPOCH`는 1회차 직전에 잡으므로, 어느 회차에서든 Claude가 보고했다면 보존한다.

## 테스트

`ops/tests/test-job-status-fallback.sh`(기존 ops 테스트와 같은 `check` 관례, 수동 실행). ROOT는 임시 디렉터리로 export해 라이브 트리를 건드리지 않는다.

- json 없음 → fail json 생성
- 시작 전에 쓰인 `ok` → fail로 덮음
- 시작 후에 쓰인 `ok` → 보존
- `report-job-status.sh` 실패 → 함수는 여전히 rc 0
- C 로케일(launchd 환경)에서도 한국어 summary 보존
- `set -euo pipefail` 래퍼 조합에서 기록이 실패해도 `종료` 마커까지 기록
- 네 래퍼의 배선(source·`START_EPOCH`·호출) 존재, 오케스트레이터 래퍼는 미배선
