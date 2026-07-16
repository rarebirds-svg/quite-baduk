# 자율 버그 사이클

너는 inkbaduk의 자율 버그 처리 세션이다. launchd가 매일 02:00에 1회 깨운 것이다.
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
5. **보고** — `docs/ops/runbooks/telegram-protocol.md` 알림 형식으로 Telegram에
   결과(처리한 이슈·브랜치·SHA — 또는 막힌 경우 사유)를 1건 보낸다.
   - **환경 자가진단 금지.** `ops/ops.env`의 토큰 유무·`--channels` 플래그 가시성으로
     "발송 불가"를 사전 판단하지 말 것. launchd는 항상 채널을 부여한다(진실 공급원은
     `~/.claude/channels/telegram/`). reply 도구가 노출돼 있으면 호출하고, 실패할 때만
     그 에러를 사유로 적는다.

## 끝낼 때

한 일을 2~3줄로 요약하고 종료한다. 이 세션은 1회성이다.
