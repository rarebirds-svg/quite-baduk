# Agentic Ops 운영 기반 (하위 프로젝트 0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 맥 미니 한 대에서 라이브 중인 inkbaduk을 agentic AI로 운영하기 위한 기반 계층을 구축한다 — prod/staging 분리, `docs/ops/` 구조, 자율성 정책, Telegram 배선, launchd 오케스트레이터 골격.

**Architecture:** prod는 macOS launchd 서비스 둘(`com.baduk.api` uvicorn :8000, `com.baduk.web` npm start :3000)로 리포 작업 트리에서 직접 돈다 — Docker 미사용. staging은 `ops/stack.sh`가 별도 git worktree(`.worktrees/staging`)에서 :3100/:8100에 온디맨드로 띄우는 네이티브 스택이다. launchd가 매시 헤드리스 Claude Code 세션("오케스트레이터")을 깨워 `docs/ops/runbooks/`의 러닝북을 실행하고 상태를 `docs/ops/state/`에 파일로 고정한다. 라이브를 바꾸는 액션은 Telegram 승인을 거친다.

**Tech Stack:** bash, macOS launchd, git worktree, Python venv + uvicorn, Next.js, Claude Code CLI(헤드리스 `-p`), Telegram 플러그인, Markdown 러닝북.

**브랜치:** 모든 작업은 `feat/agentic-ops-foundation`에서 수행한다(spec·plan 커밋이 이미 올라가 있음). 이 sub-project 0은 새 ops 파일만 추가하고 앱 코드·`web/.next/`를 건드리지 않으므로 prod 작업 트리에서 진행해도 라이브에 영향이 없다. sub-project 1 이후의 실제 개발은 worktree에서 한다.

**경로 상수:** 리포 루트는 `/Users/daegong/projects/baduk` 다. 아래 `$ROOT`는 이 절대경로다.

---

### Task 1: 현재 라이브 구성 확인 — ✅ 완료 (조사 결과 기록)

이 태스크는 이미 실행되어 완료됐다. 조사로 확정된 사실은 다음과 같으며, 이후 태스크는 이 값을 전제로 한다.

- **prod 실행 방식:** macOS launchd. Docker는 이 머신에서 전혀 쓰지 않는다(daemon 꺼짐).
  - `com.baduk.api` → `/bin/bash backend/deploy/run_local_prod.sh` → uvicorn `--host 127.0.0.1 --port 8000 --workers 1`. `WorkingDirectory`는 `$ROOT/backend`.
  - `com.baduk.web` → `/opt/homebrew/bin/npm start -- -H 127.0.0.1 -p 3000`. `WorkingDirectory`는 `$ROOT/web`, `NODE_ENV=production`.
  - 두 plist 모두 `RunAtLoad=true`, `KeepAlive=true`. plist 원본은 `~/Library/LaunchAgents/` 와 `backend/deploy/com.baduk.api.plist`.
- **prod는 리포 작업 트리에서 직접 실행된다.** 앱 코드·`web/.next/`를 바꾸면 prod 재시작 시 반영된다 — 개발은 worktree에서.
- **DB:** `backend/data/baduk.db` (SQLite). prod backend는 `DATABASE_URL=sqlite+aiosqlite:///./data/baduk.db`.
- **시크릿:** `~/.baduk.env` (`run_local_prod.sh`가 source). 커밋 안 됨.
- **외부 노출:** cloudflared 터널 + Caddy 리버스 프록시(`.run/Caddyfile`).
- **포트:** web 3000 / backend 8000. health endpoint는 `GET /api/health` → `{"status":"ok","db":...,"katago_alive":...}`.

- [ ] **Step 1: 이 태스크는 조사로 완료됐음을 확인하고 다음으로 넘어간다**

커밋할 파일 없음.

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
- `orchestrator-prompt.md` — launchd가 깨운 헤드리스 세션이 실행하는 지시문.
- `state/` — 운영 상태의 단일 진실 공급원.
  - `dashboard.md` — 현재 상태 요약.
  - `pending-approvals.md` — 승인 대기 큐.
  - `incidents.md` — 장애 이력.
  - `log/YYYY-MM-DD.md` — 날짜별 실행 로그(감사 추적).

## 환경

맥 미니 한 대에서 prod와 staging 두 네이티브 스택이 돈다. Docker는 쓰지 않는다.

| | prod (라이브) | staging (에이전트 작업장) |
|---|---|---|
| 실행 | macOS launchd 상주 (`com.baduk.api`, `com.baduk.web`) | `ops/stack.sh up staging` 온디맨드 |
| web / backend 포트 | 3000 / 8000 | 3100 / 8100 |
| 코드 | 리포 작업 트리 | git worktree (`.worktrees/staging`) |
| DB | `backend/data/baduk.db` | worktree의 `backend/data/baduk-staging.db` |
| KataGo | `run_local_prod.sh` 설정 | `KATAGO_MOCK=true` |

prod는 리포 작업 트리에서 직접 실행되므로, 에이전트의 개발 작업은 반드시
`.worktrees/staging` worktree에서 한다.
```

- [ ] **Step 3: `docs/ops/autonomy-policy.md` 작성**

```markdown
# 자율성 정책

에이전트는 어떤 액션이든 실행 전에 이 표에서 등급을 확인한다.

| 등급 | 의미 | 해당 액션 |
|---|---|---|
| 🟢 자율 | 실행 후 `state/log/`에 사후 기록 | 헬스체크, 사용통계 리포트, staging 기동·검증, 콘텐츠·SEO 페이지 초안, 백업 검증 |
| 🟡 승인 | Telegram 제안 → 사람 승인 후 실행 | prod 승급/배포(launchd 서비스 재시작), 콘텐츠·페이지 라이브 게시, `main` 머지, DB 마이그레이션, 의존성 버전업 |
| 🔴 금지 | 에이전트 절대 불가 (사람 전용) | prod 데이터 삭제, 시크릿/`~/.baduk.env`·JWT 로테이션, 유료 인프라 결제, 사용자 PII 개별 열람 |

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

### Task 3: staging worktree + 의존성 셋업

staging 스택을 prod와 격리해 띄우려면 별도 git worktree와 그 안의 독립 의존성이 필요하다. 이 태스크는 그 일회성 셋업을 한다.

**Files:**
- 없음 (worktree·의존성 생성. `.worktrees/`는 이미 `.gitignore` 대상)

**주의:** `.venv311` 생성과 `pip install`은 수 분 걸린다. 정상이다.

- [ ] **Step 1: staging worktree 생성**

`main`의 트리를 detached 모드로 체크아웃한다(브랜치 `main`은 prod 트리가 점유 중이라 detached 필요).

Run:
```bash
cd /Users/daegong/projects/baduk
git worktree add --detach .worktrees/staging main
ls .worktrees/staging
```
Expected: `.worktrees/staging`에 `backend`, `web` 등 리포 전체가 체크아웃된다.

- [ ] **Step 2: staging backend 독립 venv + 의존성**

worktree backend는 자체 venv를 가져야 한다(prod venv 재사용 시 editable-install 경로 충돌로 prod 코드를 import할 위험).

Run:
```bash
cd /Users/daegong/projects/baduk/.worktrees/staging/backend
python3.11 -m venv .venv311
source .venv311/bin/activate
pip install -e ".[dev]"
python -c "import app.main; print('backend import OK')"
```
Expected: 설치 완료 후 `backend import OK`.

- [ ] **Step 3: staging web node_modules 심볼릭 링크**

web 의존성은 prod와 동일하므로(staging = main 트리) `npm install` 반복 대신 prod의 `node_modules`를 심볼릭 링크한다.

Run:
```bash
ln -s /Users/daegong/projects/baduk/web/node_modules \
      /Users/daegong/projects/baduk/.worktrees/staging/web/node_modules
ls -ld /Users/daegong/projects/baduk/.worktrees/staging/web/node_modules
```
Expected: 심볼릭 링크가 prod `node_modules`를 가리킨다.

- [ ] **Step 4: 커밋 없음**

worktree와 의존성은 모두 `.gitignore` 대상이거나 작업 트리 밖이다. 커밋할 파일 없음.

---

### Task 4: `ops/staging.env` + `ops/stack.sh` 스택 제어 래퍼

staging 네이티브 스택을 한 명령으로 띄우고 내리며, prod 상태를 읽기 전용으로 조회하는 래퍼.

**Files:**
- Create: `ops/staging.env`
- Create: `ops/stack.sh`

- [ ] **Step 1: `ops/staging.env` 작성**

시크릿이 아닌 staging 설정값(커밋 가능). `JWT_SECRET`은 staging 전용 더미라 비공개 가치가 없다.

```
# staging 네이티브 스택 설정값 — 시크릿 아님, 커밋 대상.
STAGING_BACKEND_PORT=8100
STAGING_WEB_PORT=3100
DATABASE_URL=sqlite+aiosqlite:///./data/baduk-staging.db
KATAGO_MOCK=true
JWT_SECRET=staging-only-not-a-secret
CORS_ORIGINS=http://localhost:3100
```

- [ ] **Step 2: `ops/stack.sh` 작성**

```bash
#!/usr/bin/env bash
# prod(launchd) 상태 조회와 staging 네이티브 스택 기동·중지를 담당하는 운영 래퍼.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

WORKTREE="$ROOT/.worktrees/staging"
RUN_DIR="$ROOT/.run"
ENVFILE="$ROOT/ops/staging.env"

usage() { echo "사용법: ops/stack.sh {up|down|ps} staging | ops/stack.sh ps prod" >&2; exit 1; }

ACTION="${1:-}"; TARGET="${2:-}"
{ [ -z "$ACTION" ] || [ -z "$TARGET" ]; } && usage

# shellcheck disable=SC1090
[ -f "$ENVFILE" ] && { set -a; . "$ENVFILE"; set +a; }

staging_up() {
  [ -d "$WORKTREE" ] || { echo "staging worktree 없음. 계획 Task 3을 먼저 수행하세요." >&2; exit 1; }
  mkdir -p "$RUN_DIR" "$WORKTREE/backend/data"

  ( cd "$WORKTREE/backend"
    # shellcheck disable=SC1091
    source .venv311/bin/activate
    export DATABASE_URL KATAGO_MOCK JWT_SECRET CORS_ORIGINS
    alembic upgrade head >> "$RUN_DIR/staging-backend.log" 2>&1
    exec nohup uvicorn app.main:app --host 127.0.0.1 --port "$STAGING_BACKEND_PORT" \
      >> "$RUN_DIR/staging-backend.log" 2>&1
  ) & echo $! > "$RUN_DIR/staging-backend.pid"

  ( cd "$WORKTREE/web"
    export NEXT_PUBLIC_API_URL="http://localhost:$STAGING_BACKEND_PORT"
    exec nohup npm run dev -- -p "$STAGING_WEB_PORT" \
      >> "$RUN_DIR/staging-web.log" 2>&1
  ) & echo $! > "$RUN_DIR/staging-web.pid"

  echo "staging 기동 요청: backend :$STAGING_BACKEND_PORT, web :$STAGING_WEB_PORT"
  echo "준비까지 30~60초. 확인: ops/stack.sh ps staging"
}

staging_down() {
  for svc in backend web; do
    pf="$RUN_DIR/staging-$svc.pid"
    if [ -f "$pf" ] && kill -0 "$(cat "$pf")" 2>/dev/null; then
      kill "$(cat "$pf")" 2>/dev/null && echo "staging-$svc 중지"
    fi
    rm -f "$pf"
  done
  # next dev 는 자식 프로세스를 띄우므로 포트 기준으로도 정리한다.
  for port in "$STAGING_BACKEND_PORT" "$STAGING_WEB_PORT"; do
    pids="$(lsof -ti ":$port" 2>/dev/null || true)"
    [ -n "$pids" ] && kill $pids 2>/dev/null || true
  done
}

staging_ps() {
  for svc in backend web; do
    pf="$RUN_DIR/staging-$svc.pid"
    if [ -f "$pf" ] && kill -0 "$(cat "$pf")" 2>/dev/null; then
      echo "staging-$svc: 가동 (pid $(cat "$pf"))"
    else
      echo "staging-$svc: 중단됨"
    fi
  done
  curl -fs --max-time 10 "http://localhost:$STAGING_BACKEND_PORT/api/health" \
    && echo " <- staging backend health" || echo "staging backend health: 응답 없음"
}

prod_ps() {
  launchctl list | grep -E 'com\.baduk\.(api|web)' || echo "launchd: com.baduk.* 미등록"
  curl -fs --max-time 10 "http://localhost:8000/api/health" \
    && echo " <- prod backend health" || echo "prod backend health: 응답 없음"
  curl -fs --max-time 10 "http://localhost:3000" >/dev/null \
    && echo "prod web :3000 OK" || echo "prod web :3000 응답 없음"
}

case "$ACTION/$TARGET" in
  up/staging)   staging_up ;;
  down/staging) staging_down ;;
  ps/staging)   staging_ps ;;
  ps/prod)      prod_ps ;;
  *)            usage ;;
esac
```

- [ ] **Step 3: 실행 권한 부여**

Run: `chmod +x /Users/daegong/projects/baduk/ops/stack.sh`

- [ ] **Step 4: 사용법 출력 확인**

Run: `ops/stack.sh`
Expected: `사용법: ...` 출력 후 종료 코드 1.

- [ ] **Step 5: prod 상태 조회 확인 (읽기 전용, 라이브 안전)**

Run: `ops/stack.sh ps prod`
Expected: `com.baduk.api`·`com.baduk.web`가 launchctl 목록에 보이고, prod backend health JSON과 `prod web :3000 OK`가 출력된다. **prod 프로세스를 멈추거나 재시작하지 않는다** — `ps`는 읽기 전용이다.

- [ ] **Step 6: 커밋**

```bash
git add ops/staging.env ops/stack.sh
git commit -m "feat(ops): staging 스택 제어 래퍼 stack.sh + staging.env"
```

---

### Task 5: staging 스택 기동 검증 (검증 기준 #1)

staging 스택을 실제로 띄워 prod와 독립 포트로 동시에 돌고 간섭이 없음을 확인한다.

**Files:**
- 없음 (실행 검증만)

- [ ] **Step 1: staging 스택 기동**

Run: `ops/stack.sh up staging`
Expected: backend·web 기동 요청 메시지. 30~60초 대기.

- [ ] **Step 2: staging 가동 확인**

Run:
```bash
sleep 45
ops/stack.sh ps staging
```
Expected: `staging-backend: 가동`, `staging-web: 가동`, staging backend health JSON 출력. 안 뜨면 `.run/staging-backend.log`·`.run/staging-web.log`를 읽고 원인을 고친다.

- [ ] **Step 3: 두 스택 동시 가동 + 포트 분리 확인**

Run:
```bash
lsof -ti :8000 :3000 :8100 :3100 | wc -l
curl -fs http://localhost:8100/api/health && echo " staging-OK"
```
Expected: 네 포트 모두 점유(프로세스 PID 4개 이상), staging backend가 `staging-OK`. prod(:8000/:3000)와 staging(:8100/:3100)이 동시에 산다.

- [ ] **Step 4: DB 격리 확인**

Run:
```bash
ls -la /Users/daegong/projects/baduk/backend/data/baduk.db
ls -la /Users/daegong/projects/baduk/.worktrees/staging/backend/data/baduk-staging.db
```
Expected: prod DB와 staging DB가 **서로 다른 파일**로 존재한다 — 데이터가 분리됐다.

- [ ] **Step 5: prod 무손상 확인**

Run: `curl -fs http://localhost:8000/api/health && echo " PROD-OK"`
Expected: `PROD-OK`. 라이브가 검증 작업에 영향받지 않았음을 확인한다.

- [ ] **Step 6: 커밋 없음**

실행 검증 태스크다. 생성된 파일이 없다. staging 스택은 띄운 채로 둔다(Task 6에서 사용).

---

### Task 6: healthcheck 러닝북 (검증 기준 #2)

오케스트레이터가 매시 실행할 헬스체크 절차를 러닝북으로 고정한다. 러닝북은 사람·에이전트 모두 읽고 그대로 실행할 수 있어야 한다.

**Files:**
- Create: `docs/ops/runbooks/healthcheck.md`

- [ ] **Step 1: `docs/ops/runbooks/healthcheck.md` 작성**

아래 내용에서 `[FENCE]`로 표시된 자리에는 실제 백틱 세 개(```)를 넣는다 — 러닝북 안의 bash 코드 블록이다.

```markdown
# 러닝북: 헬스체크

- 주기: 매시 정각 (오케스트레이터)
- 등급: 🟢 자율
- 목적: prod·staging 스택 정상 여부를 확인하고, 이상 시에만 Telegram 경보.

## 절차

### 1. prod 헬스

[FENCE]bash
curl -fs --max-time 10 http://localhost:8000/api/health && echo " prod-backend OK"
curl -fs --max-time 10 http://localhost:3000 >/dev/null && echo "prod-web OK"
launchctl list | grep -E 'com\.baduk\.(api|web)'
[FENCE]
판정: 두 curl이 성공하고 `com.baduk.api`·`com.baduk.web`가 launchctl 목록에 있으면 정상.
launchctl 행의 첫 컬럼이 PID(숫자)면 가동, `-`면 중단.

### 2. staging 헬스

[FENCE]bash
ops/stack.sh ps staging
[FENCE]
판정: staging은 상시 가동이 필수가 아니다. `중단됨`이면 `중단`으로만 기록(경보 아님).

### 3. 디스크 여유

[FENCE]bash
df -h / | tail -1 | awk '{print $5}'
[FENCE]
판정: 사용률 90% 이상이면 경보.

## 결과 처리

1. 결과를 `state/log/YYYY-MM-DD.md`에 추가한다 (시각·항목별 OK/실패).
2. `state/dashboard.md`의 스택 상태 표를 갱신한다.
3. **prod 이상이 하나라도 있으면** `runbooks/telegram-protocol.md`의 알림 형식으로
   Telegram 경보를 보내고 `state/incidents.md`에 항목을 추가한다.
4. 모두 정상이면 Telegram을 보내지 않는다 (조용한 성공).

## 범위 메모

백업 신선도·공개 도메인(cloudflared) 점검은 sub-project 1(SRE)의 백업·배포 러닝북에서
다룬다. 이 러닝북은 로컬 prod·staging 가용성에 집중한다.
```

- [ ] **Step 2: 러닝북 명령 실측 검증**

러닝북의 1~3번 bash 블록을 그대로 터미널에서 실행한다.
Run: 각 블록의 명령을 순서대로 실행.
Expected: prod 항목 `OK` 출력 + launchctl 목록, staging 가동 상태, 디스크 사용률이 출력된다. 명령이 깨지면 러닝북을 고친다 — 러닝북의 명령은 실제로 동작해야 한다.

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
- Modify: `.gitignore`

- [ ] **Step 1: `.gitignore`에 `ops/ops.env` 추가**

`.gitignore`의 `# Env & data` 블록 안 `.env.local` 줄 바로 아래에 추가한다.

```
ops/ops.env
```

- [ ] **Step 2: chat_id 확보**

이 태스크는 사용자 입력이 필요하다 — **컨트롤러가 사용자에게 Telegram chat_id를 받아 전달한다.** 사용자가 Telegram 봇으로 메시지를 보내면 인바운드 `<channel ... chat_id="...">` 태그에서 값을 읽는다.

- [ ] **Step 3: `ops/ops.env` 작성**

`<CHAT_ID>`는 Step 2에서 확보한 값으로 치환한다.

```
# 운영 오케스트레이터 런타임 설정 (커밋 금지 — .gitignore 대상).
TELEGRAM_CHAT_ID=<CHAT_ID>
```

- [ ] **Step 4: `docs/ops/runbooks/telegram-protocol.md` 작성**

아래에서 `[FENCE]`는 실제 백틱 세 개(```)로 치환한다.

```markdown
# 러닝북: Telegram 알림·승인 규약

Telegram Bot API는 히스토리 조회가 불가능하다(도착 메시지만 봄). 그래서 제안 시점과
승인 시점을 `state/pending-approvals.md` 파일로 분리한다.

chat_id는 `ops/ops.env`의 `TELEGRAM_CHAT_ID`에서 읽는다.

## 알림 (단방향)

상태 요약·장애 경보·일일 리포트를 Telegram `reply` 도구로 푸시한다. 응답 불필요.

형식:
[FENCE]
[inkbaduk 운영] <제목>
<본문 — 한 줄당 한 항목>
시각: YYYY-MM-DD HH:MM
[FENCE]

## 승인 (양방향)

🟡 액션은 다음 절차를 따른다.

### 제안 (액션을 만난 에이전트)

1. 승인 ID를 만든다: `AP-YYYYMMDD-NN` (NN은 그날 일련번호).
2. `state/pending-approvals.md`의 "대기 중"에 항목을 추가한다:
   [FENCE]
   ### AP-YYYYMMDD-NN
   - 액션: <한 줄 요약>
   - 근거: <왜 필요한가>
   - 영향: <무엇이 바뀌나>
   - 실행 절차: <승인 시 그대로 수행할 명령/단계>
   - 상태: 대기
   [FENCE]
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

- [ ] **Step 5: 알림 왕복 검증 (더미 항목)**

`state/pending-approvals.md`에 `AP-20260522-99` 더미 항목(액션: "검증용 더미, 실제 동작 없음")을 추가하고, telegram-protocol.md의 알림 형식으로 Telegram에 제안 메시지를 보낸다. 사용자가 `승인 AP-20260522-99`로 답신하면 처리 절차대로 항목을 큐에서 제거하고 `state/log/`에 기록한 뒤 Telegram으로 결과를 회신한다.
Expected: 제안 메시지 도착 → 답신 → 큐에서 제거 + 로그 기록 + 회신. 왕복이 끊기면 규약을 고친다.

- [ ] **Step 6: ops.env 무시 확인**

Run: `git status --porcelain | grep -c 'ops/ops.env' || echo 0`
Expected: `0` — `ops/ops.env`는 추적되지 않는다.

- [ ] **Step 7: 커밋**

```bash
git add docs/ops/runbooks/telegram-protocol.md docs/ops/state .gitignore
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
     - (sub-project 1~4에서 백업검증·사용통계 러닝북이 추가되면 여기에 포함된다.)

2. **실행** — 각 러닝북의 "절차"를 그대로 수행한다. 헬스체크는 직접 실행해도 되고,
   범위가 크면 `Agent` 도구로 서브에이전트에 위임한다.

3. **상태 갱신** — `state/dashboard.md`를 갱신하고, 한 일을 `state/log/YYYY-MM-DD.md`에
   추가한다(없으면 생성). 장애가 있으면 `state/incidents.md`에 기록한다.

4. **보고** — `docs/ops/runbooks/telegram-protocol.md` 형식으로 Telegram에 보낸다.
   - 매시 실행: prod 이상이 있을 때만 경보. 모두 정상이면 침묵.
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

# 헤드리스 실행. 무인 스케줄이라 권한 프롬프트가 불가능 — 가드레일은
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
sleep 60
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
lsof -ti :8000 :3000 :8100 :3100 | wc -l
```
Expected: prod·staging 모두 health 응답, 네 포트 점유. staging이 내려가 있으면 `ops/stack.sh up staging` 후 재확인.

- [ ] **Step 2: 검증 기준 #2 — healthcheck 러닝북**

Run: `healthcheck.md`의 1~3번 bash 블록을 순서대로 실행.
Expected: prod·staging 양쪽 상태가 정확히 보고된다(prod OK + launchctl 목록, staging 상태, 디스크 사용률).

- [ ] **Step 3: 검증 기준 #3 — Telegram 승인 왕복**

Task 7 Step 5를 재확인한다. `pending-approvals.md`에 더미 항목이 남아있지 않은지,
`state/log/`에 `AP-20260522-99` 처리 기록이 있는지 확인한다.
Expected: 큐 비어 있음 + 로그에 처리 기록.

- [ ] **Step 4: 검증 기준 #4 — launchd 스케줄**

Run:
```bash
launchctl list | grep com.inkbaduk.ops-orchestrator
tail -5 docs/ops/state/log/orchestrator-runs.log
```
Expected: 작업이 등록돼 있고, Task 9 Step 6의 수동 트리거 실행 기록이 로그에 있다.

- [ ] **Step 5: 대시보드 갱신**

`docs/ops/state/dashboard.md`의 스택 상태 표를 Step 1~2 실측값으로 채우고 갱신 시각을
적는다. `docs/ops/state/log/2026-05-22.md`에 "운영 기반 구축 완료 — 검증 기준 4/4 통과"를
기록한다(파일 없으면 생성).

- [ ] **Step 6: 커밋**

```bash
git add docs/ops/state
git commit -m "feat(ops): 운영 기반 구축 완료 — 검증 기준 4/4 통과"
```

- [ ] **Step 7: 최종 보고**

검증 기준 4가지의 실제 출력을 사용자에게 보여주고, sub-project 0 완료를 보고한다.
다음 단계는 sub-project 1(운영팀 SRE)의 brainstorm이다.

---

## 검증 기준 (spec)

이 4가지가 실제 명령 실행으로 통과하면 sub-project 0 완료. 문서만으로 "완료" 선언 금지.

1. staging 스택이 prod와 독립 포트로 동시 기동되고 서로 간섭이 없다. → Task 5, 10
2. healthcheck 러닝북이 prod·staging 양쪽 상태를 정확히 보고한다. → Task 6, 10
3. Telegram 알림 도착 + 승인 큐 왕복이 더미 항목으로 동작한다. → Task 7, 10
4. launchd가 스케줄에 오케스트레이터를 깨우고 로그가 남는다. → Task 9, 10
