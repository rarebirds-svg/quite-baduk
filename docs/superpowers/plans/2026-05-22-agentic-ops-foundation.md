# Agentic Ops 운영 기반 (하위 프로젝트 0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 맥 미니 한 대에서 라이브 중인 inkbaduk을 agentic AI로 운영하기 위한 기반 계층을 구축한다 — prod/staging 분리, `docs/ops/` 구조, 자율성 정책, Telegram 배선, launchd 오케스트레이터 골격.

**Architecture:** docker-compose 프로젝트 두 개(prod·staging)를 같은 머신에서 독립 포트로 운영한다. launchd가 매시 헤드리스 Claude Code 세션("오케스트레이터")을 깨우고, 그 세션이 `docs/ops/runbooks/`의 러닝북을 읽어 실행하며 상태를 `docs/ops/state/`에 파일로 고정한다. 라이브를 바꾸는 액션은 Telegram 승인을 거친다.

**Tech Stack:** docker compose, bash, macOS launchd, Claude Code CLI(헤드리스 `-p`), Telegram 플러그인, Markdown 러닝북.

**브랜치:** 모든 작업은 `feat/agentic-ops-foundation`에서 수행한다(이미 spec 커밋이 올라가 있음).

**경로 상수:** 리포 루트는 `/Users/daegong/projects/baduk` 다. 아래 `$ROOT`는 이 절대경로를 가리킨다.

---

### Task 1: 현재 라이브 구성 확인 및 기록

라이브 prod 스택의 실행 방식과 docker 프로젝트명·볼륨명을 확정한다. **prod 프로젝트명을 절대 바꾸지 않기 위해** 현재 값을 먼저 기록한다(이름이 바뀌면 기존 볼륨이 고아가 되어 실데이터가 끊긴다).

**Files:**
- 없음 (조사 + 결과를 Task 2의 `docs/ops/README.md`에 반영)

- [ ] **Step 1: 실행 중인 스택 확인**

Run:
```bash
cd /Users/daegong/projects/baduk
docker compose ls
docker ps --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}'
ls -la .run/ 2>/dev/null
```
Expected: 라이브 스택이 docker-compose면 `docker compose ls`에 프로젝트가 보이고, `docker ps`에 web/backend/backup 컨테이너가 3000/8000 포트로 나온다. `.run/`에 PID 파일이 있고 컨테이너가 없으면 native `start.sh` 스택이 라이브다.

- [ ] **Step 2: prod 프로젝트명과 볼륨명 기록**

Run:
```bash
docker volume ls | grep -i baduk
```
Expected: `<프로젝트명>_baduk_data`, `<프로젝트명>_baduk_backups`, `<프로젝트명>_katago_models` 형태. 접두사가 현재 prod 프로젝트명이다 (디렉터리명 기본값이면 `baduk`).

- [ ] **Step 3: 결과를 메모로 남긴다**

다음 세 값을 확정해 이후 태스크에서 쓴다. checklist에 적어둔다.
- `PROD_PROJECT` = (Step 2의 볼륨 접두사. 예: `baduk`)
- `PROD_LAUNCH` = `docker-compose` 또는 `native-start.sh`
- prod web/backend 포트 = (보통 3000 / 8000)

확인 불가하거나 모호하면 **여기서 멈추고 사용자에게 보고**한다 — 환경 분리 전체가 이 값에 의존한다.

- [ ] **Step 4: 커밋 없음**

이 태스크는 조사만 한다. 커밋할 파일이 없다.

---

### Task 2: `docs/ops/` 골격 — README · 자율성 정책 · 상태 파일

운영 체계의 파일 기반 뼈대를 만든다. 모든 후속 태스크가 이 디렉터리에 의존한다.

**Files:**
- Create: `docs/ops/README.md`
- Create: `docs/ops/autonomy-policy.md`
- Create: `docs/ops/state/dashboard.md`
- Create: `docs/ops/state/pending-approvals.md`
- Create: `docs/ops/state/incidents.md`
- Create: `docs/ops/state/log/.gitkeep`

- [ ] **Step 1: 디렉터리 생성**

Run:
```bash
cd /Users/daegong/projects/baduk
mkdir -p docs/ops/runbooks docs/ops/state/log
touch docs/ops/state/log/.gitkeep
```

- [ ] **Step 2: `docs/ops/README.md` 작성**

```markdown
# inkbaduk 운영 체계 (Agentic Ops)

이 디렉터리는 inkbaduk을 agentic AI로 운영하기 위한 러닝북·상태·정책을 담는다.
설계 근거: `docs/superpowers/specs/2026-05-22-agentic-ops-foundation-design.md`.

## 구조

- `autonomy-policy.md` — 액션 자율성 3등급 정책. 에이전트는 행동 전 이 표를 따른다.
- `runbooks/` — 선언적 작업 절차. 오케스트레이터가 읽어 실행한다.
- `state/` — 운영 상태의 단일 진실 공급원.
  - `dashboard.md` — 현재 상태 요약.
  - `pending-approvals.md` — 승인 대기 큐.
  - `incidents.md` — 장애 이력.
  - `log/YYYY-MM-DD.md` — 날짜별 실행 로그(감사 추적).

## 환경

맥 미니 한 대에서 두 docker-compose 스택이 돈다.

| | prod (라이브) | staging (에이전트 작업장) |
|---|---|---|
| web / backend 포트 | 3000 / 8000 | 3100 / 8100 |
| docker 프로젝트명 | <Task 1에서 확정한 PROD_PROJECT> | inkbaduk-staging |
| KataGo | 실제 모델 | KATAGO_MOCK=true |

스택 제어는 `ops/stack.sh` 로 한다. 라이브 실행 방식: <Task 1의 PROD_LAUNCH 기록>.
```
`<...>` 부분은 Task 1에서 확정한 실제 값으로 채운다.

- [ ] **Step 3: `docs/ops/autonomy-policy.md` 작성**

```markdown
# 자율성 정책

에이전트는 어떤 액션이든 실행 전에 이 표에서 등급을 확인한다.

| 등급 | 의미 | 해당 액션 |
|---|---|---|
| 🟢 자율 | 실행 후 `state/log/`에 사후 기록 | 헬스체크, 사용통계 리포트, staging 배포·검증, 콘텐츠·SEO 페이지 초안, 백업 검증 |
| 🟡 승인 | Telegram 제안 → 사람 승인 후 실행 | prod 승급/배포, 콘텐츠·페이지 라이브 게시, `main` 머지, DB 마이그레이션, 의존성 버전업 |
| 🔴 금지 | 에이전트 절대 불가 (사람 전용) | prod 데이터 삭제, 시크릿/JWT 로테이션, 유료 인프라 결제, 사용자 PII 개별 열람 |

## 원칙

- 읽기·staging·초안은 자율.
- 라이브를 바꾸는 모든 것은 승인.
- 비가역적인 것은 금지.
- 등급이 모호하면 한 단계 보수적으로(자율→승인, 승인→금지) 처리하고 사람에게 보고한다.

## 승인 절차

🟡 액션은 `runbooks/telegram-protocol.md`의 절차를 따른다 — `state/pending-approvals.md`에
항목 기록 → Telegram 제안 → 답신 도착 시 실행.
```

- [ ] **Step 4: `docs/ops/state/dashboard.md` 작성**

```markdown
# 운영 대시보드

- 갱신: (오케스트레이터가 매 실행 시 갱신)

## 스택 상태

| 스택 | 상태 | 마지막 확인 |
|---|---|---|
| prod | 미확인 | - |
| staging | 미확인 | - |

## 보류 승인

`state/pending-approvals.md` 참조 — 0건.

## 최근 장애

`state/incidents.md` 참조 — 0건.
```

- [ ] **Step 5: `docs/ops/state/pending-approvals.md` 작성**

```markdown
# 승인 대기 큐

🟡 액션 제안이 여기 쌓인다. 형식은 `runbooks/telegram-protocol.md` 참조.
처리 완료 항목은 큐에서 제거하고 `state/log/`로 옮긴다.

## 대기 중

(없음)
```

- [ ] **Step 6: `docs/ops/state/incidents.md` 작성**

```markdown
# 장애 이력

헬스체크 실패·복구 이력을 시간순으로 기록한다.

## 이력

(없음)
```

- [ ] **Step 7: 생성 확인**

Run: `find docs/ops -type f | sort`
Expected: README.md, autonomy-policy.md, state/dashboard.md, state/pending-approvals.md, state/incidents.md, state/log/.gitkeep 6개가 보인다.

- [ ] **Step 8: 커밋**

```bash
git add docs/ops
git commit -m "feat(ops): docs/ops 골격 — README·자율성 정책·상태 파일"
```

---

### Task 3: staging 환경 파일

staging 스택을 prod와 독립된 포트·프로젝트·DB로 띄우기 위한 override 파일을 만든다.

**Files:**
- Create: `docker-compose.staging.yml`
- Create: `.env.staging.example`
- Modify: `.gitignore`

- [ ] **Step 1: `docker-compose.staging.yml` 작성**

prod `docker-compose.yml` 위에 겹쳐 적용하는 override. 호스트 포트만 3100/8100으로 옮기고 staging은 KataGo를 mock으로 돌린다.

```yaml
# staging 스택 override — prod docker-compose.yml 위에 겹쳐 포트·KataGo만 분리.
services:
  web:
    ports:
      - "3100:3000"

  backend:
    ports:
      - "8100:8000"
    environment:
      KATAGO_MOCK: "true"
      CORS_ORIGINS: "http://localhost:3100"
```

- [ ] **Step 2: `.env.staging.example` 작성**

```
JWT_SECRET=staging-only-not-a-secret
KATAGO_MOCK=true
CORS_ORIGINS=http://localhost:3100
```

- [ ] **Step 3: `.gitignore`에 실제 env 파일 추가**

`.gitignore`의 `# Env & data` 블록 안 `.env.local` 줄 바로 아래에 다음을 추가한다.

```
.env.staging
.env.prod
ops/ops.env
```
`.example` 접미사 파일은 커밋되고, 실제 값 파일은 무시된다.

- [ ] **Step 4: staging env 파일 생성**

Run:
```bash
cd /Users/daegong/projects/baduk
cp .env.staging.example .env.staging
```

- [ ] **Step 5: 무시 동작 확인**

Run: `git status --porcelain | grep -E 'env.staging'`
Expected: `.env.staging.example`만 보이고 `.env.staging`은 안 보인다.

- [ ] **Step 6: 커밋**

```bash
git add docker-compose.staging.yml .env.staging.example .gitignore
git commit -m "feat(ops): staging 스택 override + env 예시"
```

---

### Task 4: `ops/stack.sh` 스택 제어 래퍼

prod·staging 두 docker 스택을 한 명령으로 제어한다. native `start.sh`(개발용)는 건드리지 않는다 — prod는 docker-compose이므로 docker 전용 래퍼가 맞다.

**Files:**
- Create: `ops/stack.sh`

- [ ] **Step 1: `ops/stack.sh` 작성**

`<PROD_PROJECT>`는 Task 1에서 확정한 prod 프로젝트명으로 치환한다.

```bash
#!/usr/bin/env bash
# prod·staging docker 스택을 프로젝트·포트 분리해 제어하는 래퍼.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

PROD_PROJECT="<PROD_PROJECT>"        # Task 1에서 확정
STAGING_PROJECT="inkbaduk-staging"

usage() { echo "사용법: ops/stack.sh {up|down|ps} {prod|staging}" >&2; exit 1; }

ACTION="${1:-}"; ENV="${2:-}"
[ -z "$ACTION" ] || [ -z "$ENV" ] && usage

case "$ENV" in
  prod)
    COMPOSE=(docker compose -p "$PROD_PROJECT" -f docker-compose.yml)
    ENVFILE=".env.prod"
    ;;
  staging)
    COMPOSE=(docker compose -p "$STAGING_PROJECT" \
             -f docker-compose.yml -f docker-compose.staging.yml)
    ENVFILE=".env.staging"
    ;;
  *) usage ;;
esac

[ -f "$ENVFILE" ] && COMPOSE+=(--env-file "$ENVFILE")

case "$ACTION" in
  up)
    if [ "$ENV" = "staging" ]; then
      "${COMPOSE[@]}" up -d --build --scale backup=0
    else
      "${COMPOSE[@]}" up -d --build
    fi
    ;;
  down) "${COMPOSE[@]}" down ;;
  ps)   "${COMPOSE[@]}" ps ;;
  *)    usage ;;
esac
```

- [ ] **Step 2: 실행 권한 부여**

Run: `chmod +x /Users/daegong/projects/baduk/ops/stack.sh`

- [ ] **Step 3: 사용법 출력 확인**

Run: `ops/stack.sh`
Expected: `사용법: ops/stack.sh {up|down|ps} {prod|staging}` 출력 후 종료 코드 1.

- [ ] **Step 4: prod 스택 인식 확인 (읽기 전용, 라이브 안전)**

Run: `ops/stack.sh ps prod`
Expected: 현재 라이브 중인 web/backend 컨테이너가 그대로 나온다. **컨테이너가 재생성되거나 멈추면 안 된다** — `ps`는 읽기 전용이다. 만약 빈 목록이면 `PROD_PROJECT` 값이 틀린 것이니 멈추고 Task 1을 재확인한다.

- [ ] **Step 5: 커밋**

```bash
git add ops/stack.sh
git commit -m "feat(ops): prod·staging 스택 제어 래퍼 stack.sh"
```

---

### Task 5: staging 스택 기동 검증 (검증 기준 #1)

staging 스택을 실제로 띄워 prod와 독립 포트로 동시에 돌고 간섭이 없음을 확인한다.

**Files:**
- 없음 (실행 검증만)

- [ ] **Step 1: staging 스택 기동**

Run: `ops/stack.sh up staging`
Expected: `inkbaduk-staging` 프로젝트로 web/backend 컨테이너가 빌드·기동된다. backup 사이드카는 `--scale backup=0`으로 뜨지 않는다.

- [ ] **Step 2: 두 스택 동시 가동 확인**

Run:
```bash
docker ps --format 'table {{.Names}}\t{{.Ports}}' | grep -E 'baduk|inkbaduk'
```
Expected: prod 컨테이너(3000/8000)와 staging 컨테이너(3100/8100)가 **동시에** 보인다.

- [ ] **Step 3: staging 헬스 확인**

Run: `curl -fs http://localhost:8100/api/health && echo OK`
Expected: backend 응답 JSON 뒤에 `OK`. prod(`:8000`)는 영향 없이 그대로 응답해야 한다.

- [ ] **Step 4: 볼륨 격리 확인**

Run: `docker volume ls | grep -E 'baduk_data'`
Expected: prod 볼륨(`<PROD_PROJECT>_baduk_data`)과 staging 볼륨(`inkbaduk-staging_baduk_data`)이 **서로 다른 이름**으로 존재 — DB가 분리됐다.

- [ ] **Step 5: prod 무손상 확인**

Run: `curl -fs http://localhost:8000/api/health && echo PROD-OK`
Expected: `PROD-OK`. 라이브가 검증 작업에 영향받지 않았음을 확인한다.

- [ ] **Step 6: 커밋 없음**

실행 검증 태스크다. 생성된 파일이 없다. staging 스택은 띄운 채로 둔다(Task 6에서 사용).

---

### Task 6: healthcheck 러닝북 (검증 기준 #2)

오케스트레이터가 매시 실행할 헬스체크 절차를 러닝북으로 고정한다. 러닝북은 사람·에이전트 모두 읽고 그대로 실행할 수 있어야 한다.

**Files:**
- Create: `docs/ops/runbooks/healthcheck.md`

- [ ] **Step 1: `docs/ops/runbooks/healthcheck.md` 작성**

`<PROD_PROJECT>`는 Task 1 확정값으로 치환한다.

```markdown
# 러닝북: 헬스체크

- 주기: 매시 정각 (오케스트레이터)
- 등급: 🟢 자율
- 목적: prod·staging 스택과 백업의 정상 여부를 확인하고, 이상 시에만 Telegram 경보.

## 절차

### 1. prod 헬스

\`\`\`bash
curl -fs --max-time 10 http://localhost:8000/api/health && echo " prod-backend OK"
curl -fs --max-time 10 http://localhost:3000 >/dev/null && echo "prod-web OK"
docker compose -p <PROD_PROJECT> -f docker-compose.yml ps
\`\`\`
판정: 두 curl이 성공하고 컨테이너가 모두 `running`이면 정상.

### 2. staging 헬스

\`\`\`bash
curl -fs --max-time 10 http://localhost:8100/api/health && echo " staging-backend OK"
\`\`\`
판정: staging은 상시 가동이 필수는 아니다. 응답 없으면 `중단됨`으로만 기록(경보 아님).

### 3. 디스크 여유

\`\`\`bash
df -h / | tail -1 | awk '{print $5}'
\`\`\`
판정: 사용률 90% 이상이면 경보.

### 4. 백업 신선도

\`\`\`bash
docker run --rm -v <PROD_PROJECT>_baduk_backups:/b alpine:3.19 \
  sh -c 'ls -t /b/baduk-*.db 2>/dev/null | head -1'
\`\`\`
판정: 가장 최근 백업 파일이 36시간보다 오래됐으면 경보(백업 사이드카 점검 필요).

## 결과 처리

1. 결과를 `state/log/YYYY-MM-DD.md`에 추가한다 (시각·항목별 OK/실패).
2. `state/dashboard.md`의 스택 상태 표를 갱신한다.
3. **이상이 하나라도 있으면** `runbooks/telegram-protocol.md`의 알림 형식으로
   Telegram 경보를 보내고, prod 관련 이상이면 `state/incidents.md`에 항목을 추가한다.
4. 모두 정상이면 Telegram을 보내지 않는다 (조용한 성공).
```

- [ ] **Step 2: 러닝북 명령 실측 검증**

러닝북의 1~4번 bash 블록을 그대로 터미널에서 실행한다.
Run: 각 블록의 명령을 순서대로 실행.
Expected: prod 항목은 `OK` 출력, staging은 Task 5에서 띄웠으면 `OK`, 디스크 사용률·백업 파일명이 출력된다. 명령이 깨지면 러닝북을 고친다 — 러닝북의 명령은 실제로 동작해야 한다.

- [ ] **Step 3: 커밋**

```bash
git add docs/ops/runbooks/healthcheck.md
git commit -m "feat(ops): healthcheck 러닝북"
```

---

### Task 7: telegram-protocol 러닝북 + chat_id 설정 (검증 기준 #3)

알림·승인 메시지 규약을 고정하고, 아웃바운드 알림에 필요한 Telegram chat_id를 기록한다.

**Files:**
- Create: `docs/ops/runbooks/telegram-protocol.md`
- Create: `ops/ops.env` (gitignore 대상)

- [ ] **Step 1: chat_id 확보 안내**

사용자에게 Telegram 봇으로 아무 메시지나 보내달라고 요청한다. 인바운드 메시지의
`<channel ... chat_id="...">` 태그에서 `chat_id` 값을 읽는다. 이미 알고 있으면 생략.

- [ ] **Step 2: `ops/ops.env` 작성**

`<CHAT_ID>`는 Step 1에서 확보한 값으로 치환한다.

```
# 운영 오케스트레이터 런타임 설정 (커밋 금지 — .gitignore 대상).
TELEGRAM_CHAT_ID=<CHAT_ID>
```

- [ ] **Step 3: `docs/ops/runbooks/telegram-protocol.md` 작성**

```markdown
# 러닝북: Telegram 알림·승인 규약

Telegram Bot API는 히스토리 조회가 불가능하다(도착 메시지만 봄). 그래서 제안 시점과
승인 시점을 `state/pending-approvals.md` 파일로 분리한다.

chat_id는 `ops/ops.env`의 `TELEGRAM_CHAT_ID`에서 읽는다.

## 알림 (단방향)

상태 요약·장애 경보·일일 리포트를 Telegram `reply` 도구로 푸시한다. 응답 불필요.

형식:
\`\`\`
[inkbaduk 운영] <제목>
<본문 — 한 줄당 한 항목>
시각: YYYY-MM-DD HH:MM
\`\`\`

## 승인 (양방향)

🟡 액션은 다음 절차를 따른다.

### 제안 (액션을 만난 에이전트)

1. 승인 ID를 만든다: `AP-YYYYMMDD-NN` (NN은 그날 일련번호).
2. `state/pending-approvals.md`의 "대기 중"에 항목을 추가한다:
   \`\`\`
   ### AP-YYYYMMDD-NN
   - 액션: <한 줄 요약>
   - 근거: <왜 필요한가>
   - 영향: <무엇이 바뀌나>
   - 실행 절차: <승인 시 그대로 수행할 명령/단계>
   - 상태: 대기
   \`\`\`
3. Telegram으로 같은 내용을 보낸다 (ID 포함). 끝에 안내:
   `승인하려면 "승인 AP-...", 반려는 "반려 AP-..."`

### 처리 (답신이 도착한 세션)

1. 답신에서 ID와 승인/반려를 파싱한다.
2. `state/pending-approvals.md`에서 해당 ID 항목을 찾는다 — 없으면 사용자에게 알린다.
3. 승인이면 "실행 절차"를 그대로 수행하고, 반려면 수행하지 않는다.
4. 항목을 큐에서 제거하고 결과를 `state/log/YYYY-MM-DD.md`에 기록한다.
5. Telegram으로 처리 결과를 회신한다.

### 미처리 리마인드

오케스트레이터는 매 실행 시 "대기 중" 항목 수를 세어, 1건 이상이면 일일 요약에
"보류 승인 N건"으로 포함한다.
```

- [ ] **Step 4: 알림 왕복 검증 (더미 항목)**

`state/pending-approvals.md`에 `AP-20260522-99` 더미 항목(액션: "검증용 더미, 실제 동작 없음")을 추가하고, telegram-protocol.md의 알림 형식으로 Telegram에 제안 메시지를 보낸다. 사용자가 `승인 AP-20260522-99`로 답신하면 처리 절차대로 항목을 큐에서 제거하고 `state/log/`에 기록한 뒤 Telegram으로 결과를 회신한다.
Expected: 제안 메시지 도착 → 답신 → 큐에서 제거 + 로그 기록 + 회신. 왕복이 끊기면 규약을 고친다.

- [ ] **Step 5: ops.env 무시 확인**

Run: `git status --porcelain | grep -c 'ops/ops.env' || echo 0`
Expected: `0` — `ops/ops.env`는 추적되지 않는다.

- [ ] **Step 6: 커밋**

```bash
git add docs/ops/runbooks/telegram-protocol.md docs/ops/state
git commit -m "feat(ops): Telegram 알림·승인 규약 러닝북"
```

---

### Task 8: 운영 오케스트레이터 프롬프트

launchd가 깨운 헤드리스 세션이 실행할 지시문을 작성한다. 이 프롬프트가 "러닝북을 읽어 due한 것을 실행하고 상태를 기록한다"는 1회 루프를 정의한다.

**Files:**
- Create: `docs/ops/orchestrator-prompt.md`

- [ ] **Step 1: `docs/ops/orchestrator-prompt.md` 작성**

```markdown
# 운영 오케스트레이터

너는 inkbaduk의 운영 오케스트레이터다. 이 세션은 launchd가 매시 정각에 1회 깨운 것이다.
작업 디렉터리는 리포 루트(`/Users/daegong/projects/baduk`)다.

## 시작 전 필수

1. `docs/ops/autonomy-policy.md`를 읽는다. 🟡 액션은 절대 자율 실행하지 않는다.
2. 현재 시각을 확인한다.

## 1회 실행 루프

1. **due한 러닝북 선별**
   - `docs/ops/runbooks/healthcheck.md` — 매시 실행. 항상 due.
   - 현재 시각이 09:00~09:59 이면 일일 작업도 due:
     - `state/pending-approvals.md`의 "대기 중" 건수를 세어 일일 요약에 포함.
     - (하위 프로젝트 1~4에서 백업검증·사용통계 러닝북이 추가되면 여기에 포함된다.)

2. **실행** — 각 러닝북의 "절차"를 그대로 수행한다. 헬스체크는 직접 실행해도 되고,
   범위가 크면 `Agent` 도구로 서브에이전트에 위임한다.

3. **상태 갱신** — `state/dashboard.md`를 갱신하고, 한 일을 `state/log/YYYY-MM-DD.md`에
   추가한다(없으면 생성). 장애가 있으면 `state/incidents.md`에 기록한다.

4. **보고** — `docs/ops/runbooks/telegram-protocol.md` 형식으로 Telegram에 보낸다.
   - 매시 실행: 이상이 있을 때만 경보. 모두 정상이면 침묵.
   - 09시 실행: 이상 여부와 무관하게 일일 요약을 1건 보낸다.

5. **승인 답신 처리** — 이 세션이 Telegram 답신으로 트리거된 것이면(인바운드 메시지가
   있으면), 위 루프 대신 telegram-protocol.md의 "처리" 절차를 수행한다.

## 끝낼 때

한 일을 2~3줄로 요약하고 종료한다. 이 세션은 1회성이다 — 다음 실행은 launchd가 깨운다.
```

- [ ] **Step 2: 커밋**

```bash
git add docs/ops/orchestrator-prompt.md
git commit -m "feat(ops): 운영 오케스트레이터 프롬프트"
```

---

### Task 9: launchd 작업 + 래퍼 스크립트 (검증 기준 #4)

매시 정각 오케스트레이터를 헤드리스 Claude Code로 깨우는 launchd 작업을 등록한다.

**Files:**
- Create: `ops/run-orchestrator.sh`
- Create: `ops/launchd/com.inkbaduk.ops-orchestrator.plist`

- [ ] **Step 1: `claude` 실행 파일 경로 확인**

Run: `which claude`
Expected: 절대경로 출력(예: `/Users/daegong/.local/bin/claude`). launchd는 최소 PATH를 쓰므로 이 절대경로를 래퍼에 박는다. 비어 있으면 멈추고 사용자에게 Claude Code CLI 설치 위치를 묻는다.

- [ ] **Step 2: `ops/run-orchestrator.sh` 작성**

`<CLAUDE_BIN>`은 Step 1의 절대경로로 치환한다.

```bash
#!/usr/bin/env bash
# launchd가 매시 호출 — 오케스트레이터 프롬프트로 헤드리스 Claude Code를 1회 실행.
set -euo pipefail
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT"

[ -f ops/ops.env ] && { set -a; . ops/ops.env; set +a; }

mkdir -p docs/ops/state/log
RUNLOG="docs/ops/state/log/orchestrator-runs.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] orchestrator 시작" >> "$RUNLOG"

# 헤드리스 실행. 무인 스케줄이므로 권한 프롬프트가 불가능 — 가드레일은
# autonomy-policy.md(🟡 액션은 Telegram 승인)이지 OS 권한창이 아니다.
<CLAUDE_BIN> -p "$(cat docs/ops/orchestrator-prompt.md)" \
  --dangerously-skip-permissions \
  >> "$RUNLOG" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] 비정상 종료" >> "$RUNLOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] orchestrator 종료" >> "$RUNLOG"
```

- [ ] **Step 3: 실행 권한 부여**

Run: `chmod +x /Users/daegong/projects/baduk/ops/run-orchestrator.sh`

- [ ] **Step 4: launchd plist 작성**

Run: `mkdir -p /Users/daegong/projects/baduk/ops/launchd`

`ops/launchd/com.inkbaduk.ops-orchestrator.plist`:

```xml
<!-- 매시 정각 운영 오케스트레이터를 깨우는 launchd 작업 정의. -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.inkbaduk.ops-orchestrator</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/daegong/projects/baduk/ops/run-orchestrator.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/daegong/projects/baduk/docs/ops/state/log/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/daegong/projects/baduk/docs/ops/state/log/launchd.err.log</string>
</dict>
</plist>
```

- [ ] **Step 5: launchd에 등록**

Run:
```bash
cp /Users/daegong/projects/baduk/ops/launchd/com.inkbaduk.ops-orchestrator.plist \
   ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.inkbaduk.ops-orchestrator.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.inkbaduk.ops-orchestrator.plist
launchctl list | grep com.inkbaduk.ops-orchestrator
```
Expected: 마지막 줄에 `com.inkbaduk.ops-orchestrator`가 보인다.

- [ ] **Step 6: 수동 1회 트리거로 검증**

Run:
```bash
launchctl start com.inkbaduk.ops-orchestrator
sleep 30
tail -20 /Users/daegong/projects/baduk/docs/ops/state/log/orchestrator-runs.log
```
Expected: `orchestrator 시작` / `종료` 로그가 찍히고, 헤드리스 세션이 헬스체크를 수행한 흔적이 보인다. 권한 오류로 막히면 Step 2의 플래그를 점검한다.

- [ ] **Step 7: 커밋**

```bash
git add ops/run-orchestrator.sh ops/launchd
git commit -m "feat(ops): launchd 오케스트레이터 작업 + 래퍼"
```

`~/Library/LaunchAgents/`의 plist 사본은 머신 로컬 상태라 커밋 대상이 아니다.

---

### Task 10: 통합 검증 + 대시보드 갱신

검증 기준 4가지를 처음부터 끝까지 한 번에 통과시키고, 결과를 대시보드에 기록한다.

**Files:**
- Modify: `docs/ops/state/dashboard.md`
- Create: `docs/ops/state/log/2026-05-22.md` (없으면)

- [ ] **Step 1: 검증 기준 #1 — 두 스택 동시 가동**

Run:
```bash
ops/stack.sh ps prod
ops/stack.sh ps staging
docker ps --format '{{.Names}} {{.Ports}}' | grep -E 'baduk|inkbaduk'
```
Expected: prod(3000/8000)·staging(3100/8100) 컨테이너가 동시에 `running`.

- [ ] **Step 2: 검증 기준 #2 — healthcheck 러닝북**

Run: `healthcheck.md`의 1~4번 bash 블록을 순서대로 실행.
Expected: prod·staging 양쪽 상태가 정확히 보고된다(prod OK, staging OK, 디스크·백업 출력).

- [ ] **Step 3: 검증 기준 #3 — Telegram 승인 왕복**

Task 7 Step 4를 재확인한다. 이미 통과했으면 `pending-approvals.md`에 더미 항목이
남아있지 않은지, `state/log/`에 처리 기록이 있는지 확인한다.
Expected: 큐 비어 있음 + 로그에 `AP-20260522-99` 처리 기록.

- [ ] **Step 4: 검증 기준 #4 — launchd 스케줄**

Run:
```bash
launchctl list | grep com.inkbaduk.ops-orchestrator
tail -5 docs/ops/state/log/orchestrator-runs.log
```
Expected: 작업이 등록돼 있고, Task 9 Step 6의 수동 트리거 실행 기록이 로그에 있다.

- [ ] **Step 5: 대시보드 갱신**

`docs/ops/state/dashboard.md`의 스택 상태 표를 Step 1~2 실측값으로 채우고, 갱신 시각을
적는다. `docs/ops/state/log/2026-05-22.md`에 "운영 기반 구축 완료 — 검증 기준 4/4 통과"를
기록한다(파일 없으면 생성).

- [ ] **Step 6: 커밋**

```bash
git add docs/ops/state
git commit -m "feat(ops): 운영 기반 구축 완료 — 검증 기준 4/4 통과"
```

- [ ] **Step 7: 최종 보고**

검증 기준 4가지의 실제 출력을 사용자에게 보여주고, 하위 프로젝트 0 완료를 보고한다.
다음 단계는 하위 프로젝트 1(운영팀 SRE)의 brainstorm이다.

---

## 검증 기준 (spec)

이 4가지가 실제 명령 실행으로 통과하면 하위 프로젝트 0 완료. 문서만으로 "완료" 선언 금지.

1. staging 스택이 prod와 독립 포트로 동시 기동되고 서로 간섭이 없다. → Task 5, 10
2. healthcheck 러닝북이 prod·staging 양쪽 상태를 정확히 보고한다. → Task 6, 10
3. Telegram 알림 도착 + 승인 큐 왕복이 더미 항목으로 동작한다. → Task 7, 10
4. launchd가 스케줄에 오케스트레이터를 깨우고 로그가 남는다. → Task 9, 10
