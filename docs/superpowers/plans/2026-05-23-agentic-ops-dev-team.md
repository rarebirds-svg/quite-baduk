# Agentic Ops 개발팀 (하위 프로젝트 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** inkbaduk 운영에 개발팀 계층을 올린다 — GitHub 이슈 백로그, dev-ops 러닝북(스캔·트리아지·PR감시), 자율 버그 파이프라인(dev-cycle), 온디맨드 기능 파이프라인.

**Architecture:** 백로그는 GitHub 이슈다. 가벼운 dev-ops(bug-scan·backlog-triage·pr-watch)는 sub-project 0의 오케스트레이터가 12·18시에 실행한다. 긴 구현 작업은 cron에 안 맞으므로 분리한다 — `bug`·`small` 이슈는 매일 02:00 `com.inkbaduk.dev-cycle` launchd 세션이 1개씩 자율 수정→PR, `feature` 이슈는 온디맨드로 기존 superpowers 스킬을 쓴다. 자율 작업은 전용 worktree에서만, PR 머지는 사람이 게이트한다.

**Tech Stack:** bash, macOS launchd, git worktree, `gh` CLI(GitHub 이슈·PR·라벨), Claude Code CLI(헤드리스 `-p`), Markdown 러닝북.

**브랜치:** 모든 작업은 `feat/agentic-ops-dev-team`에서 수행한다(sub-project 1 브랜치 `feat/agentic-ops-sre`에서 분기, spec 커밋이 이미 올라가 있음). 앱 코드를 건드리지 않고 `ops/`·`docs/ops/`·`.github/` 파일만 추가·수정한다.

**전제:** sub-project 0·1 산출물(`docs/ops/`, `ops/stack.sh`, `ops/launchd/`, orchestrator-prompt.md, autonomy-policy.md, dashboard.md, `.worktrees/staging` 패턴)이 작업 트리에 존재한다. `gh` CLI는 인증돼 있다(repo `rarebirds-svg/quite-baduk`). prod는 launchd로 리포 작업 트리에서 직접 실행된다.

**경로 상수:** 리포 루트는 `/Users/daegong/projects/baduk`. `claude` 실행 파일은 `/opt/homebrew/bin/claude`.

---

### Task 1: GitHub 라벨 세트 + bug 이슈 템플릿

백로그를 운용할 라벨과 이슈 템플릿을 만든다.

**Files:**
- Create: `.github/ISSUE_TEMPLATE/bug.md`

- [ ] **Step 1: 라벨 생성**

Run:
```bash
gh label create feature     --description "새 기능"          --color 0e8a16 --force
gh label create chore       --description "잡무·유지보수"     --color fef2c0 --force
gh label create small       --description "소형 — 자율 처리 적격" --color c5def5 --force
gh label create prio:high   --description "높은 우선순위"      --color d93f0b --force
gh label create prio:low    --description "낮은 우선순위"      --color bfdadc --force
gh label create in-progress --description "자율 파이프라인 처리 중" --color fbca04 --force
```
Expected: 6개 라벨이 생성된다(`bug`는 GitHub 기본 라벨이라 생성 불필요). `--force`라 이미 있으면 갱신.

- [ ] **Step 2: 라벨 확인**

Run: `gh label list | grep -E 'feature|chore|small|prio:|in-progress'`
Expected: 6개 라벨이 모두 보인다.

- [ ] **Step 3: `.github/ISSUE_TEMPLATE/bug.md` 작성**

```markdown
---
name: 버그 신고
about: 동작 이상을 보고합니다
labels: bug
---

## 재현 절차

1.

## 기대 동작

## 실제 동작

## 환경 (선택)

- 브라우저 / OS:
```

- [ ] **Step 4: 커밋**

```bash
git add .github/ISSUE_TEMPLATE/bug.md
git commit -m "feat(ops): GitHub 백로그 라벨 세트 + bug 이슈 템플릿"
```

라벨은 GitHub 서버 상태라 커밋 대상이 아니다 — Step 1이 생성한다.

---

### Task 2: `bug-scan.md` 러닝북

오케스트레이터가 로그를 스캔해 반복 에러를 GitHub 이슈로 올리는 절차.

**Files:**
- Create: `docs/ops/runbooks/bug-scan.md`

- [ ] **Step 1: `docs/ops/runbooks/bug-scan.md` 작성**

`[FENCE]`는 실제 백틱 세 개(```)로 치환한다. 최종 파일에 `[FENCE]` 문자열이 남으면 안 된다.

```markdown
# 러닝북: 버그 스캔

- 주기: 매일 12시·18시 (오케스트레이터)
- 등급: 🟢 자율 (이슈 생성까지. 수정은 dev-cycle/온디맨드.)
- 목적: 로그에서 반복되는 진짜 에러를 찾아 GitHub `bug` 이슈로 올린다.

## 절차

### 1. 로그 수집

[FENCE]bash
tail -200 ~/Library/Logs/baduk-api.err 2>/dev/null
tail -100 docs/ops/state/incidents.md
[FENCE]

### 2. 후보 선별

수집한 로그에서 다음을 만족하는 에러만 후보로 삼는다.
- 스택 트레이스나 명확한 예외 메시지가 있다.
- 1회성이 아니라 반복된다(같은 에러가 2회 이상).
- 일시적 인프라 잡음(네트워크 타임아웃 등)이 아니다.

### 3. 중복 차단

[FENCE]bash
gh issue list --state open --label bug --json title --jq '.[].title'
[FENCE]
후보 에러가 이미 열린 `bug` 이슈로 있으면 건너뛴다.

### 4. 이슈 생성

새 후보만 이슈로 만든다.
[FENCE]bash
gh issue create --label bug --title "<한 줄 요약>" \
  --body "스캔 출처: <로그 파일>\n\n<에러 발췌>\n\n자동 탐지(bug-scan)."
[FENCE]

## 결과 처리

생성한 이슈 수를 `state/log/YYYY-MM-DD.md`에 기록한다. 0건이면 "신규 버그 없음"으로
기록한다. Telegram 보고는 오케스트레이터가 실행 요약으로 처리한다.
```

- [ ] **Step 2: 러닝북 명령 실측 검증**

bug-scan.md의 1·3번 bash 블록을 실행한다(4번 이슈 생성은 실제 새 버그가 있을 때만 — 검증에선 실행하지 않음).
Run: 1번(로그 수집)·3번(`gh issue list`) 블록을 실행.
Expected: 로그 tail 출력(파일 없으면 빈 출력), `gh issue list`가 정상 동작(빈 목록이어도 OK).

- [ ] **Step 3: 커밋**

```bash
git add docs/ops/runbooks/bug-scan.md
git commit -m "feat(ops): 버그 스캔 러닝북"
```

---

### Task 3: `backlog-triage.md` 러닝북

라벨 없는 열린 이슈를 분류하는 절차.

**Files:**
- Create: `docs/ops/runbooks/backlog-triage.md`

- [ ] **Step 1: `docs/ops/runbooks/backlog-triage.md` 작성**

`[FENCE]`는 실제 백틱 세 개(```)로 치환한다.

```markdown
# 러닝북: 백로그 트리아지

- 주기: 매일 12시·18시 (오케스트레이터)
- 등급: 🟢 자율
- 목적: 라벨 없는 열린 이슈를 읽고 분류 라벨을 부여한다.

## 절차

### 1. 미분류 이슈 수집

[FENCE]bash
gh issue list --state open --search "no:label" --json number,title,body
[FENCE]
출력이 빈 배열이면 할 일 없음 — 종료.

### 2. 분류

각 미분류 이슈를 읽고 라벨을 정한다.
- 종류: 동작 이상이면 `bug`, 새 기능이면 `feature`, 유지보수·잡무면 `chore`.
- 크기: 한 파일 안팎의 작은 변경이면 `small`.
- 우선순위: 라이브 장애·데이터 영향이면 `prio:high`, 사소하면 `prio:low`, 보통이면 생략.

### 3. 라벨 적용

[FENCE]bash
gh issue edit <번호> --add-label "<라벨1>,<라벨2>"
[FENCE]
판단이 모호한 이슈는 라벨을 강제하지 말고 그대로 두고 결과 처리에 "사람 분류 필요"로 적는다.

## 결과 처리

분류한 이슈 수와 "사람 분류 필요" 항목을 `state/log/YYYY-MM-DD.md`에 기록한다.
```

- [ ] **Step 2: 러닝북 명령 실측 검증**

Run: `gh issue list --state open --search "no:label" --json number,title`
Expected: JSON 배열 출력(빈 배열이어도 OK) — `gh` 검색 구문이 동작함을 확인.

- [ ] **Step 3: 커밋**

```bash
git add docs/ops/runbooks/backlog-triage.md
git commit -m "feat(ops): 백로그 트리아지 러닝북"
```

---

### Task 4: `pr-watch.md` 러닝북

열린 PR을 점검해 정체·실패를 보고하는 절차.

**Files:**
- Create: `docs/ops/runbooks/pr-watch.md`

- [ ] **Step 1: `docs/ops/runbooks/pr-watch.md` 작성**

`[FENCE]`는 실제 백틱 세 개(```)로 치환한다.

```markdown
# 러닝북: PR 감시

- 주기: 매일 12시·18시 (오케스트레이터)
- 등급: 🟢 자율 (보고까지. PR 수정은 dev 작업.)
- 목적: 열린 PR의 CI·머지 상태를 점검하고 정체·실패 PR을 보고한다.

## 절차

### 1. 열린 PR 수집

[FENCE]bash
gh pr list --state open --json number,title,createdAt,mergeable,statusCheckRollup
[FENCE]

### 2. 판정

각 PR을 다음으로 분류한다.
- CI 실패 — `statusCheckRollup`에 실패 체크가 있음.
- 충돌 — `mergeable`이 `CONFLICTING`.
- 정체 — `createdAt`이 7일 이상 지났는데 열려 있음.
- 정상 — 위에 해당 없음.

## 결과 처리

CI 실패·충돌·정체 PR의 번호와 사유를 `state/log/YYYY-MM-DD.md`에 기록하고,
일일 요약에 "주의 PR N건"으로 포함한다. 정상 PR만 있으면 "열린 PR 모두 정상".
실제 수정(rebase·CI 고치기)은 dev 작업이라 백로그 항목화하거나 온디맨드로 처리한다.
```

- [ ] **Step 2: 러닝북 명령 실측 검증**

Run: `gh pr list --state open --json number,title,mergeable,statusCheckRollup`
Expected: JSON 배열 출력 — 현재 열린 PR들이 보인다(`mergeable`·CI 필드 포함).

- [ ] **Step 3: 커밋**

```bash
git add docs/ops/runbooks/pr-watch.md
git commit -m "feat(ops): PR 감시 러닝북"
```

---

### Task 5: dev-cycle worktree 셋업

자율 버그 파이프라인이 격리되어 작업할 전용 worktree를 만든다.

**Files:**
- 없음 (worktree·의존성 생성. `.worktrees/`는 `.gitignore` 대상)

**주의:** `pip install`은 수 분 걸린다. timeout을 넉넉히(600000ms) 잡아라.

- [ ] **Step 1: dev-cycle worktree 생성**

Run:
```bash
cd /Users/daegong/projects/baduk
git worktree add --detach .worktrees/dev-cycle main
ls .worktrees/dev-cycle
```
Expected: `.worktrees/dev-cycle`에 리포 전체가 체크아웃된다.

- [ ] **Step 2: backend 독립 venv + 의존성**

Run:
```bash
cd /Users/daegong/projects/baduk/.worktrees/dev-cycle/backend
python3.11 -m venv .venv311
source .venv311/bin/activate
pip install -e ".[dev]"
KATAGO_MOCK=true python -c "import app.main; print('backend import OK')"
```
Expected: 설치 완료 후 `backend import OK`.

- [ ] **Step 3: web node_modules 심볼릭 링크**

Run:
```bash
ln -s /Users/daegong/projects/baduk/web/node_modules \
      /Users/daegong/projects/baduk/.worktrees/dev-cycle/web/node_modules
ls -ld /Users/daegong/projects/baduk/.worktrees/dev-cycle/web/node_modules
```
Expected: 심볼릭 링크가 prod `node_modules`를 가리킨다.

- [ ] **Step 4: 커밋 없음** — worktree·의존성은 `.gitignore` 대상이거나 작업 트리 밖이다.

---

### Task 6: `dev-pipeline.md` 러닝북 + `dev-cycle-prompt.md`

이슈를 크기별로 처리하는 절차(러닝북)와, 자율 버그 세션이 실행할 지시문.

**Files:**
- Create: `docs/ops/runbooks/dev-pipeline.md`
- Create: `docs/ops/dev-cycle-prompt.md`

- [ ] **Step 1: `docs/ops/runbooks/dev-pipeline.md` 작성**

```markdown
# 러닝북: 개발 파이프라인

GitHub 이슈를 크기별로 처리하는 절차다.

## bug · small 이슈 → 자율 경로

전용 worktree(`.worktrees/dev-cycle`)에서.

1. `git -C .worktrees/dev-cycle fetch origin`, `origin/main` 기준으로 `fix/issue-<N>` 브랜치 생성.
2. 수정한다.
   - 로직 버그 — TDD: 버그를 재현하는 실패 테스트 작성 → 수정 → 통과 확인.
   - 오타·주석·문구 등 비로직 수정 — 테스트 추가 없이 수정하고 기존 테스트가 깨지지
     않는지 확인.
3. 커밋, 브랜치 푸시, `gh pr create`로 PR 생성 — 본문에 `Closes #<N>`.
4. 확신이 안 서거나 테스트가 통과하지 않으면 PR을 만들지 말고 이슈에 코멘트로 막힌
   지점을 남기고 에스컬레이션한다.

## feature 이슈 → 온디맨드 경로

사용자가 "이슈 #N 진행"으로 트리거한다. cron 자동화하지 않는다.

1. `superpowers:brainstorming` — 사용자와 설계.
2. `superpowers:writing-plans` — 구현 계획.
3. `superpowers:subagent-driven-development` — 태스크별 구현·리뷰.
4. PR 생성.

PR 머지는 어느 경로든 🟡 — 사람이 한다.
```

- [ ] **Step 2: `docs/ops/dev-cycle-prompt.md` 작성**

```markdown
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
4. **마무리** — PR을 만들었으면 이슈에서 `in-progress`를 떼고(PR이 `Closes`로
   연결됨), 결과를 `state/log/YYYY-MM-DD.md`에 기록한다. 에스컬레이션했으면
   `in-progress`를 떼고 이슈에 코멘트를 남긴 뒤 기록한다.
5. **보고** — `docs/ops/runbooks/telegram-protocol.md` 알림 형식으로 Telegram에
   결과(처리한 이슈·PR 번호 또는 에스컬레이션)를 1건 보낸다.

## 끝낼 때

한 일을 2~3줄로 요약하고 종료한다. 이 세션은 1회성이다.
```

- [ ] **Step 3: 커밋**

```bash
git add docs/ops/runbooks/dev-pipeline.md docs/ops/dev-cycle-prompt.md
git commit -m "feat(ops): 개발 파이프라인 러닝북 + 자율 버그 사이클 프롬프트"
```

---

### Task 7: dev-cycle launchd 작업 + 래퍼

매일 02:00 자율 버그 사이클을 헤드리스 Claude로 깨우는 launchd 작업.

**Files:**
- Create: `ops/run-dev-cycle.sh`
- Create: `ops/launchd/com.inkbaduk.dev-cycle.plist`

- [ ] **Step 1: `ops/run-dev-cycle.sh` 작성**

```bash
#!/usr/bin/env bash
# launchd가 매일 02:00 호출 — 자율 버그 사이클 프롬프트로 헤드리스 Claude Code를 1회 실행.
set -euo pipefail
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT"

[ -f ops/ops.env ] && { set -a; . ops/ops.env; set +a; }

mkdir -p docs/ops/state/log
RUNLOG="docs/ops/state/log/dev-cycle-runs.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] dev-cycle 시작" >> "$RUNLOG"

/opt/homebrew/bin/claude -p "$(cat docs/ops/dev-cycle-prompt.md)" \
  --dangerously-skip-permissions \
  --channels plugin:telegram@claude-plugins-official \
  >> "$RUNLOG" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] 비정상 종료" >> "$RUNLOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] dev-cycle 종료" >> "$RUNLOG"
```

- [ ] **Step 2: 실행 권한 부여**

Run: `chmod +x /Users/daegong/projects/baduk/ops/run-dev-cycle.sh`

- [ ] **Step 3: `ops/launchd/com.inkbaduk.dev-cycle.plist` 작성**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- 매일 02:00 자율 버그 사이클을 깨우는 launchd 작업 정의. -->
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.inkbaduk.dev-cycle</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/daegong/projects/baduk/ops/run-dev-cycle.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>2</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/daegong/projects/baduk/docs/ops/state/log/dev-cycle.out.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/daegong/projects/baduk/docs/ops/state/log/dev-cycle.err.log</string>
</dict>
</plist>
```

- [ ] **Step 4: launchd에 등록**

Run:
```bash
cp /Users/daegong/projects/baduk/ops/launchd/com.inkbaduk.dev-cycle.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.inkbaduk.dev-cycle.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.inkbaduk.dev-cycle.plist
launchctl list | grep com.inkbaduk.dev-cycle
```
Expected: 마지막 줄에 `com.inkbaduk.dev-cycle`가 보인다.

- [ ] **Step 5: 문법·plist 검사**

Run:
```bash
bash -n /Users/daegong/projects/baduk/ops/run-dev-cycle.sh && echo "스크립트 문법 OK"
plutil -lint /Users/daegong/projects/baduk/ops/launchd/com.inkbaduk.dev-cycle.plist
xmllint --noout /Users/daegong/projects/baduk/ops/launchd/com.inkbaduk.dev-cycle.plist && echo "xmllint OK"
```
Expected: 스크립트 문법 OK, plist OK, xmllint OK.

- [ ] **Step 6: 커밋**

```bash
git add ops/run-dev-cycle.sh ops/launchd/com.inkbaduk.dev-cycle.plist
git commit -m "feat(ops): 자율 버그 사이클 launchd 작업 + 래퍼"
```

`~/Library/LaunchAgents/`의 plist 사본은 머신 로컬 상태라 커밋 대상이 아니다.

---

### Task 8: 오케스트레이터 + 자율성 정책 + 대시보드 통합

dev-ops 러닝북을 오케스트레이터 루프에 연결하고, 정책·대시보드를 갱신한다.

**Files:**
- Modify: `docs/ops/orchestrator-prompt.md`
- Modify: `docs/ops/autonomy-policy.md`
- Modify: `docs/ops/state/dashboard.md`

- [ ] **Step 1: `orchestrator-prompt.md`의 러닝북 선별 블록 갱신**

`docs/ops/orchestrator-prompt.md`에서 다음 블록을 찾는다:
```markdown
1. **due한 러닝북 선별**
   - `docs/ops/runbooks/healthcheck.md` — 매 실행마다 수행.
   - `docs/ops/runbooks/backup-verify.md` — 매 실행마다 수행.
   - healthcheck가 prod 실패를 잡으면 `docs/ops/runbooks/incident.md`로 연결한다.
   - (sub-project 2~4에서 사용통계 러닝북이 추가되면 여기에 포함된다.)
```
다음으로 교체한다:
```markdown
1. **due한 러닝북 선별**
   - `docs/ops/runbooks/healthcheck.md` — 매 실행마다 수행.
   - `docs/ops/runbooks/backup-verify.md` — 매 실행마다 수행.
   - `docs/ops/runbooks/bug-scan.md` — 매 실행마다 수행.
   - `docs/ops/runbooks/backlog-triage.md` — 매 실행마다 수행.
   - `docs/ops/runbooks/pr-watch.md` — 매 실행마다 수행.
   - healthcheck가 prod 실패를 잡으면 `docs/ops/runbooks/incident.md`로 연결한다.
   - (sub-project 3~4에서 사용통계 러닝북이 추가되면 여기에 포함된다.)
```

- [ ] **Step 2: `autonomy-policy.md`에 개발 작업 명시 추가**

`docs/ops/autonomy-policy.md` 맨 끝(마지막 줄 다음, 빈 줄 하나 띄우고)에 추가한다. 기존 내용은 수정하지 마라:

```markdown

## 개발 작업 등급

| 액션 | 등급 |
|---|---|
| GitHub 이슈 생성·라벨링 | 🟢 자율 |
| worktree에서 코드 구현·테스트 | 🟢 자율 |
| 브랜치 푸시·PR 생성 | 🟢 자율 (PR은 제안이다) |
| PR 머지 (= `main` 변경) | 🟡 승인 |

자율 버그 사이클(dev-cycle)은 PR까지만 만든다. 머지는 사람이 한다.
```

- [ ] **Step 3: `dashboard.md`에 개발 현황 행 추가**

`docs/ops/state/dashboard.md`에서 `## 백업 상태` 섹션 전체(제목 + 표)를 찾는다. 그 표의 마지막 행 다음, `## 보류 승인` 섹션 앞에 빈 줄 하나 띄우고 아래를 삽입한다:
```markdown
## 개발 현황

| 항목 | 값 |
|---|---|
| 열린 이슈 | 미확인 |
| 열린 PR | 미확인 |
```

- [ ] **Step 4: 커밋**

```bash
git add docs/ops/orchestrator-prompt.md docs/ops/autonomy-policy.md docs/ops/state/dashboard.md
git commit -m "feat(ops): dev-ops 러닝북 오케스트레이터 연결 + 정책·대시보드 갱신"
```

---

### Task 9: dev-cycle 검증 (검증 기준 #3)

자명한 시드 `bug` 이슈로 자율 버그 사이클이 worktree 수정→PR을 만드는지 실증한다.

**Files:**
- 없음 (실행 검증. 시드 이슈·PR은 GitHub 상태)

- [ ] **Step 1: `origin/main`에 실재하는 자명한 버그 후보 찾기**

dev-cycle은 `origin/main`에서 브랜치를 따므로, 시드 버그는 **`origin/main`에 실제로
존재하는** 사소한 결함이어야 한다(브랜치에 일부러 심으면 dev-cycle이 못 본다).

Run:
```bash
git fetch origin
git show origin/main:web/lib/i18n/ko.json | head -40
git show origin/main:web/lib/i18n/en.json | head -40
```
`origin/main`의 i18n 문구나 주석에서 명백한 오타·문구 오류를 하나 찾는다 — 한 단어
수준의 자명한 것. 파일·정확한 위치·현재 값·올바른 값을 기록한다.
적당한 후보를 못 찾으면 BLOCKED로 보고한다(컨트롤러가 다른 시드를 지정).

- [ ] **Step 2: 시드 `bug` 이슈 생성**

Run:
```bash
gh issue create --label bug --label small \
  --title "<오타 요약 — 예: docs/ops/README.md 오타 수정>" \
  --body "<파일·위치·올바른 값>. dev-cycle 검증용 시드 이슈."
```
Expected: 이슈 번호가 출력된다.

- [ ] **Step 3: dev-cycle 1회 실행**

Run:
```bash
launchctl start com.inkbaduk.dev-cycle
sleep 120
tail -40 /Users/daegong/projects/baduk/docs/ops/state/log/dev-cycle-runs.log
```
Expected: `dev-cycle 시작`/`종료` 로그. 헤드리스 세션이 시드 이슈를 선택해 처리한 흔적. 헤드리스 실행이 길면 60초씩 더 기다렸다 재확인(최대 5분).

- [ ] **Step 4: PR 생성 확인**

Run: `gh pr list --state open --json number,title,headRefName,body --jq '.[] | select(.body | contains("Closes"))'`
Expected: 시드 이슈를 `Closes #<N>`으로 닫는 PR이 보인다. PR이 없고 dev-cycle이 이슈에 에스컬레이션 코멘트를 남겼으면(`gh issue view <N> --comments`로 확인) DONE_WITH_CONCERNS로 보고 — 메커니즘은 동작했으나 자율 수정이 실패한 경우다.

- [ ] **Step 5: 커밋 없음** — 실행 검증 태스크다. 시드 이슈·PR은 GitHub 상태.

---

### Task 10: 통합 검증 + 대시보드 갱신

검증 기준 4가지를 한 번에 통과시키고 대시보드를 갱신한다.

**Files:**
- Modify: `docs/ops/state/dashboard.md`
- Modify: `docs/ops/state/log/2026-05-23.md`

- [ ] **Step 1: 검증 기준 #1 — 라벨 + 트리아지**

Run:
```bash
gh label list | grep -E 'feature|chore|small|prio:|in-progress' | wc -l
gh issue create --title "검증용 무라벨 이슈" --body "backlog-triage 검증용."
```
그 다음 `backlog-triage.md` 절차대로 방금 만든 무라벨 이슈를 읽고 적절한 라벨을 `gh issue edit <N> --add-label`로 부여한다. 부여 후 `gh issue view <N> --json labels`로 확인하고, 검증이 끝나면 `gh issue close <N> --comment "검증 완료"`로 닫는다.
Expected: 라벨 6개 존재, 무라벨 이슈가 트리아지로 라벨링됨.

- [ ] **Step 2: 검증 기준 #2 — bug-scan·pr-watch 명령**

Run:
```bash
tail -50 ~/Library/Logs/baduk-api.err 2>/dev/null | tail -3
gh issue list --state open --label bug --json title --jq '.[].title'
gh pr list --state open --json number,mergeable,statusCheckRollup
```
Expected: 세 명령 모두 정상 동작(빈 출력이어도 OK).

- [ ] **Step 3: 검증 기준 #3 — dev-cycle**

Task 9 결과를 확인한다 — `launchctl list | grep com.inkbaduk.dev-cycle`로 등록 확인, 시드 이슈에 대한 PR 또는 에스컬레이션 코멘트 존재 확인.
Expected: launchd 등록됨, dev-cycle이 시드 이슈를 처리(PR 또는 에스컬레이션).

- [ ] **Step 4: 검증 기준 #4 — 오케스트레이터 통합**

Run: `grep -E 'bug-scan|backlog-triage|pr-watch' docs/ops/orchestrator-prompt.md`
Expected: 세 러닝북이 모두 orchestrator-prompt.md에 참조됨.

- [ ] **Step 5: 대시보드 + 로그 갱신**

`docs/ops/state/dashboard.md`의 개발 현황 행을 실측값으로 채운다 — "열린 이슈"에 `gh issue list --state open | wc -l`, "열린 PR"에 `gh pr list --state open | wc -l` 결과. `docs/ops/state/log/2026-05-23.md`에 다음을 추가한다(기존 항목 보존, 시간순 추가):
```markdown
## (현재시각) — 개발팀(sub-project 2) 구축 완료
- 검증 기준 4/4 통과: ① 라벨+트리아지 ② bug-scan·pr-watch ③ dev-cycle ④ 오케스트레이터 통합
```
`(현재시각)`은 `date '+%H:%M'` 출력으로 채운다.

- [ ] **Step 6: 커밋**

```bash
git add docs/ops/state
git commit -m "feat(ops): 개발팀 구축 완료 — 검증 기준 4/4 통과"
```

- [ ] **Step 7: 최종 보고** — 검증 기준 4가지의 실제 출력을 보고하고 sub-project 2 완료를 알린다.

---

## 검증 기준 (spec)

1. GitHub 라벨 세트 생성 + `backlog-triage`가 무라벨 테스트 이슈를 정확히 라벨링. → Task 1, 3, 10
2. `bug-scan`·`pr-watch` 러닝북 명령 실측 동작. → Task 2, 4, 10
3. dev-cycle이 시드 `bug` 이슈에 대해 worktree 수정→PR 생성. `com.inkbaduk.dev-cycle` launchd 등록. → Task 7, 9, 10
4. 오케스트레이터가 dev-ops 러닝북 3개를 루프에 포함, 일일 요약에 백로그·PR 현황. → Task 8, 10
