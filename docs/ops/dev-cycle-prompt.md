# 자율 버그 사이클

너는 inkbaduk의 자율 버그 처리 세션이다. launchd가 매일 04:30에 1회 깨운 것이다.
작업 디렉터리는 리포 루트(`/Users/daegong/projects/baduk`)다.

## 시작 전 필수

1. `docs/ops/autonomy-policy.md`를 읽는다. PR 머지는 절대 하지 않는다(🟡).
2. `docs/ops/runbooks/dev-pipeline.md`의 "bug · small 이슈 → 자율 경로"를 따른다.

## 1회 실행

1. **이슈 선택** — 열린 이슈 중 `bug` 또는 `small` 라벨이 있고 `feature`·`in-progress`가
   없는 것에서 우선순위 최상위 1개를 고른다.
   [gh issue list --state open --json number,title,labels 로 조회]
   - 적격 이슈가 없으면 "처리할 버그 없음"을 로그에 남기고 종료.
2. **선점** — 고른 이슈에 `in-progress` 라벨을 단다.
3. **처리** — `dev-pipeline.md`의 자율 경로 1~4단계를 `.worktrees/dev-cycle`
   worktree에서 수행한다. 한 번에 이슈 1개만.
4. **마무리** — `dev-pipeline.md` 3단계대로 push + `gh pr create`까지 **자율로**
   끝낸다(feature 패턴 브랜치 push·PR 생성은 🟢). 이슈에 브랜치·SHA·PR 링크를
   코멘트로 남기고 `in-progress`를 뗀다. 결과를 `state/log/YYYY-MM-DD.md`에
   기록한다. **PR 머지는 하지 않는다**(🟡 — 사람).
5. **보고** — Telegram으로 직접 보내지 않는다. 대신 실행 결과를 상태 파일에 기록한다.

   ```bash
   ops/report-job-status.sh dev-cycle <ok|warn|fail> "<한 줄 요약 — 40자 이내>"
   ```

   09:00 다이제스트가 이 파일을 읽어 `자동화` 행에 합산한다. 새벽 2시에 알림을 울리지 않기
   위해 발송을 오케스트레이터로 모았다.

   **예외 — `fail`이면 즉시 경보도 보낸다.** 자동화가 죽은 것은 다음 정기 보고까지 기다릴 수 없다.

   ```bash
   echo '{"kind":"alert","project":"inkbaduk","at":"<ISO8601 KST>",
          "what":"<무엇이 실패했나>","impact":"<무엇이 멈추나>","action":"<사람이 할 일>",
          "once_key":"dev_cycle_fail"}' \
     | python3 /Users/daegong/projects/scripts/ops-report/send.py \
         --env-file=$HOME/.claude/channels/telegram/.env \
         --env-file=/Users/daegong/projects/baduk/ops/ops.env
   ```

   `--env-file`은 반복 가능하다. 토큰은 첫 파일, `TELEGRAM_CHAT_ID`는 `ops/ops.env`에 있으므로
   둘을 다 넘긴다 — 하나만 넘기면 종료 코드 `4`로 발송이 무산된다.

   발송이 실패해도(비0 종료) 이 세션의 작업 판정을 바꾸지 않는다.

## 끝낼 때

한 일을 2~3줄로 요약하고 종료한다. 이 세션은 1회성이다.
