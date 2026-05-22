# Agentic Ops — 하위 프로젝트 2: 개발팀

- 작성일: 2026-05-23
- 상태: 설계 승인 완료, 구현 계획 대기
- 의존: 하위 프로젝트 0 (운영 기반), 1 (SRE)
- 범위: inkbaduk 운영의 **기능개발·버그픽스·PR 관리** 계층

## 배경

하위 프로젝트 0(운영 기반)과 1(SRE)이 prod/staging 분리, 오케스트레이터, 자율성
정책, 배포 러닝북을 구축했다. 이 2번은 그 위에 개발팀 — 요청 기반 구현, 백로그
관리, PR 리뷰·베이비시팅, 자율 버그 탐지 — 을 올린다.

### 현재 상태 (조사 확정)

- GitHub 저장소 `rarebirds-svg/quite-baduk`. 열린 이슈 0개. 3주 묵은 열린 PR
  5개(#5~#9)가 있다.
- prod는 launchd로 리포 작업 트리에서 직접 실행된다 — 개발 작업은 worktree에서.
- `.claude/agents/`에 프론트엔드 에이전트 5종이 이미 있다.

### 결정된 설계 축

- **백로그**: GitHub 이슈. PR이 `Closes #N`으로 연결, 폰에서도 이슈 등록.
- **워크플로**: 크기별 차등 — `bug`·`small`은 자율 수정→PR, `feature`는 설계 승인 후 구현.

## 접근 — B (cron 경량 dev-ops + 분리된 구현)

긴 구현 작업은 12·18시 cron 슬롯에 맞지 않고, 기능 brainstorm은 사용자 대화가
필요하다. 그래서.

- 가벼운 dev-ops(스캔·트리아지·PR감시)만 오케스트레이터 cron에 둔다.
- 버그 구현은 한정된(1주기 1개, PR 게이트) 자율 파이프라인으로 별도 스케줄.
- 기능 구현은 온디맨드 — 기존 superpowers 스킬(brainstorming·writing-plans·
  subagent-driven-development)을 사용하고 새 기계를 만들지 않는다.

## 설계

### 섹션 1 — 백로그 (GitHub 이슈 체계)

요청·버그탐지가 이슈로 모이고 PR이 `Closes #N`으로 소비한다.

- **라벨** — `bug` / `feature` / `chore`(종류), `small`(크기), `prio:high` /
  `prio:low`(우선순위), `in-progress`(자율 파이프라인 중복 선택 방지).
- **이슈 템플릿** — `.github/ISSUE_TEMPLATE/bug.md` 하나. 재현·기대·실제 필드.
- **인테이크** — ① 사용자가 Telegram으로 요청하면 에이전트가 `gh issue create`로
  이슈화·라벨링한다. ② `bug-scan`이 로그에서 버그를 발견하면 이슈를 생성한다.

### 섹션 2 — dev-ops 러닝북 (오케스트레이터가 12·18시 실행)

cron 슬롯에 맞는 빠른 작업. 전부 🟢 자율.

- **`bug-scan.md`** — `state/incidents.md`·`state/log/`·prod 에러 로그
  (`~/Library/Logs/baduk-api.err`)를 스캔. 반복되는 진짜 에러가 기존 이슈에 없으면
  `bug` 이슈를 생성한다. 중복 방지 — 이미 이슈가 있으면 건너뛴다.
- **`backlog-triage.md`** — 라벨 없는 열린 이슈를 읽고 `bug`/`feature`/`chore` +
  `small` + 우선순위 라벨을 부여한다. 사용자가 폰에서 올린 이슈가 여기서 분류된다.
- **`pr-watch.md`** — 열린 PR의 CI 상태·머지 가능 여부를 점검하고 정체·실패 PR을
  일일 요약에 보고한다. 실제 수정은 dev 작업이라 백로그 항목화하거나 온디맨드.

### 섹션 3 — 자율 버그 파이프라인

cron 슬롯에 맞지 않는 구현 작업을 위한 별도 스케줄 세션.

- **`com.inkbaduk.dev-cycle` launchd 작업** — 매일 02:00(백업 04:00 전). 헤드리스
  Claude 세션을 `dev-cycle-prompt.md`로 1회 기동한다.
- **dev-cycle 세션 동작** — 열린 이슈 중 `bug` 또는 `small`이고 `feature`·
  `in-progress`가 아닌 것에서 우선순위 최상위 1개를 선택 → `in-progress` 라벨 →
  전용 worktree(`.worktrees/dev-cycle`)에서 브랜치 생성 → TDD로 수정(실패 테스트
  작성→수정→통과) → 커밋 → 이슈에 핸드오프 코멘트(브랜치·SHA·사람이 1회 실행할
  `git push` + `gh pr create` 명령) → `in-progress` 제거.
- **푸시·PR 핸드오프** — `settings.json`이 `git push`를 deny하므로 헤드리스에서
  푸시·PR 생성이 불가능하다. 자율 세션은 커밋까지 하고 사람이 1회 푸시+PR을 만든다.
  사람의 부담은 단 한 줄 명령이지만 보안 경계는 유지된다.
- **한정·안전** — 1주기 1개. PR 머지는 어느 경우든 사람 게이트(🟡). 확신이 안 서거나
  테스트가 통과하지 않으면 커밋도 만들지 않고 이슈에 막힌 지점만 코멘트 + Telegram
  에스컬레이션한다. 전용 worktree만 쓰며 prod 트리는 절대 불가.
- 적격 이슈가 없으면 조용히 종료한다.

### 섹션 4 — 기능 파이프라인 (온디맨드) + dev-pipeline 러닝북

**`dev-pipeline.md`** — 이슈를 크기별로 처리하는 절차를 고정한 참조 러닝북.

- `bug`·`small` 이슈 → 자율 경로: worktree → TDD 수정 → PR. 섹션 3의 dev-cycle이
  실행하는 절차다.
- `feature` 이슈 → 온디맨드 경로: 사용자와 함께 `superpowers:brainstorming` →
  `writing-plans` → `subagent-driven-development` → PR. 사용자가 "이슈 #N 진행"으로
  트리거한다.

brainstorming·writing-plans 등은 이미 존재하는 스킬이다 — 재구현하지 않고 러닝북이
가리킬 뿐이다. 기능은 brainstorm이 사용자 대화라 cron 자동화가 불가능하다.

### 섹션 5 — 오케스트레이터 통합 + 자율성 정책

- **`orchestrator-prompt.md`** — 12·18시 러닝북 세트에 `bug-scan`·`backlog-triage`·
  `pr-watch`를 추가한다. 일일 요약에 백로그 건수·열린 PR 현황을 포함한다.
- **`autonomy-policy.md`** — 명시 추가: GitHub 이슈 생성·라벨링·worktree 구현·
  PR 생성은 🟢, PR 머지(= main 변경)는 🟡. 기존 "main 머지 🟡"의 구체화다.
- **`dashboard.md`** — 개발 현황 행(열린 이슈 수·열린 PR 수)을 추가한다.

### 섹션 6 — 범위 경계

**포함** — GitHub 라벨 세트 + bug 이슈 템플릿, dev-ops 러닝북 3개,
`com.inkbaduk.dev-cycle` launchd + dev-cycle 프롬프트 + dev worktree,
`dev-pipeline.md` 러닝북, 오케스트레이터 통합.

**제외** — 하위 프로젝트 3~4. brainstorming·writing-plans 재구현(기존 스킬 사용).
PR 자동 머지. 묵은 PR #5~#9의 실제 처리(`pr-watch`로 가시화만 — 처리는 백로그
항목화하거나 온디맨드).

## 검증 기준

이 4가지가 실제 명령 실행으로 통과하면 하위 프로젝트 2 완료. 문서만으로 완료 선언 금지.

1. GitHub 라벨 세트가 생성되고, `backlog-triage`가 라벨 없는 테스트 이슈를 정확히
   라벨링한다.
2. `bug-scan`·`pr-watch` 러닝북의 명령이 실측 동작한다.
3. dev-cycle이 자명한 시드 `bug` 이슈 1개에 대해 worktree 수정·커밋 + 핸드오프
   코멘트(`git push` + `gh pr create` 명령 포함)를 생성한다. 사람이 그 명령 1회로
   푸시하면 PR(`Closes #N`)이 만들어진다. `com.inkbaduk.dev-cycle` launchd 작업이
   등록된다.
4. 오케스트레이터가 dev-ops 러닝북 3개를 루프에 포함하고, 일일 요약에 백로그·PR
   현황을 표시한다.

## 리스크와 완화

| 리스크 | 완화 |
|---|---|
| 자율 dev-cycle이 나쁜 PR을 양산 | 1주기 1개, PR 게이트(머지는 사람), TDD 필수, 불확실 시 PR 대신 에스컬레이션 |
| dev-cycle이 prod 트리를 오염 | 전용 `.worktrees/dev-cycle` worktree만 사용 |
| bug-scan이 이슈를 중복·남발 | 기존 이슈와 대조해 중복 차단, 반복되는 진짜 에러만 |
| 기능을 brainstorm 없이 잘못 구현 | `feature` 라벨은 자율 경로에서 제외, 온디맨드 설계 승인 필수 |

## 다음 단계

이 spec 승인 후 `writing-plans` 스킬로 하위 프로젝트 2의 구현 계획을 작성한다.
하위 3~4(콘텐츠팀·지원분석팀)는 각자 brainstorm → spec → plan 사이클을 거친다.
