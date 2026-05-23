# Agentic Ops 운영팀 SRE (하위 프로젝트 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** inkbaduk 운영에 배포·백업·장애 대응(SRE) 계층을 올린다 — 로컬 다중 세대 백업, staging→prod 승급 러닝북, 장애 안전 복구 화이트리스트.

**Architecture:** 백업 생성은 순수 셸 스크립트(`ops/backup.sh`) + 매일 04:00 launchd 작업 — LLM 불개입. 판단이 필요한 배포·장애·백업검증은 `docs/ops/runbooks/`의 러닝북으로 두고 sub-project 0의 오케스트레이터/범용 서브에이전트가 실행한다. 자율성 정책에 "장애 안전 복구 화이트리스트"를 더해 감지된 장애 중 한정된 복구 동작을 자율 허용한다.

**Tech Stack:** bash, sqlite3 `.backup`, gzip, macOS launchd, git, Markdown 러닝북.

**브랜치:** 모든 작업은 `feat/agentic-ops-sre`에서 수행한다(sub-project 0 브랜치 `feat/agentic-ops-foundation`에서 분기, spec 커밋이 이미 올라가 있음). 이 sub-project 1은 새 `ops/`·`docs/ops/` 파일 추가와 sub-project 0 파일 수정만 하며 앱 코드를 건드리지 않는다.

**전제:** sub-project 0의 산출물(`docs/ops/`, `ops/stack.sh`, `ops/staging.env`, `.worktrees/staging` worktree, autonomy-policy.md, orchestrator-prompt.md, healthcheck.md)이 작업 트리에 존재한다. prod는 launchd `com.baduk.api`(:8000)·`com.baduk.web`(:3000)로 돈다. prod DB는 `backend/data/baduk.db`.

**경로 상수:** 리포 루트는 `/Users/daegong/projects/baduk`. 아래 `$ROOT`는 이 절대경로다.

---

### Task 1: `ops/backup.sh` — 로컬 다중 세대 백업 스크립트

prod SQLite DB의 원자적 스냅샷을 만들어 일·주·월 티어로 보관한다.

**Files:**
- Create: `ops/backup.sh`

- [x] **Step 1: `ops/backup.sh` 작성**

```bash
#!/usr/bin/env bash
# prod SQLite DB의 로컬 다중 세대(일·주·월) 백업 생성 + 보존 정책 정리.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

DB="$ROOT/backend/data/baduk.db"
DEST="$HOME/baduk-backups"
DAILY_KEEP=14
WEEKLY_KEEP=8
MONTHLY_KEEP=12

[ -f "$DB" ] || { echo "prod DB 없음: $DB" >&2; exit 1; }
mkdir -p "$DEST/daily" "$DEST/weekly" "$DEST/monthly"

STAMP="$(date +%Y%m%dT%H%M%S)"
TMP="$(mktemp -t baduk-backup.XXXXXX)"

# .backup 은 원자적이고 WAL을 존중한다.
sqlite3 "$DB" ".backup '$TMP'"
gzip -9 "$TMP"
SNAP="baduk-$STAMP.db.gz"
mv "$TMP.gz" "$DEST/daily/$SNAP"
echo "daily 백업 생성: $DEST/daily/$SNAP"

if [ "$(date +%u)" = "7" ]; then
  cp "$DEST/daily/$SNAP" "$DEST/weekly/$SNAP"
  echo "weekly 티어 복사: $SNAP"
fi
if [ "$(date +%d)" = "01" ]; then
  cp "$DEST/daily/$SNAP" "$DEST/monthly/$SNAP"
  echo "monthly 티어 복사: $SNAP"
fi

# 티어별 보존 정리 — 최신순 정렬 후 keep 개수 초과분(오래된 것) 삭제.
prune() {
  local dir="$1" keep="$2" f
  for f in $(ls -1t "$dir" 2>/dev/null | tail -n +"$((keep + 1))"); do
    rm -f "$dir/$f"
    echo "보존 정리: $dir/$f"
  done
}
prune "$DEST/daily" "$DAILY_KEEP"
prune "$DEST/weekly" "$WEEKLY_KEEP"
prune "$DEST/monthly" "$MONTHLY_KEEP"

echo "백업 완료."
```

- [x] **Step 2: 실행 권한 부여**

Run: `chmod +x /Users/daegong/projects/baduk/ops/backup.sh`

- [x] **Step 3: 백업 1회 실행 검증**

Run: `ops/backup.sh`
Expected: `daily 백업 생성: .../baduk-<stamp>.db.gz` + `백업 완료.` 출력. 에러 없이 종료.

- [x] **Step 4: 산출물 확인**

Run:
```bash
ls -la ~/baduk-backups/daily/
gunzip -t ~/baduk-backups/daily/*.db.gz && echo "gzip 무결성 OK"
```
Expected: `daily/`에 `baduk-*.db.gz` 파일 1개, gzip 무결성 OK. 깨지면 스크립트를 고친다.

- [x] **Step 5: 커밋**

```bash
git add ops/backup.sh
git commit -m "feat(ops): 로컬 다중 세대 백업 스크립트 backup.sh"
```

---

### Task 2: 백업 launchd 작업 (검증 기준 #1)

매일 04:00 백업을 자동 실행하는 launchd 작업을 등록한다.

**Files:**
- Create: `ops/launchd/com.inkbaduk.backup.plist`

- [x] **Step 1: `ops/launchd/com.inkbaduk.backup.plist` 작성**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- 매일 04:00 prod DB 로컬 다중 세대 백업을 실행하는 launchd 작업 정의. -->
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.inkbaduk.backup</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/daegong/projects/baduk/ops/backup.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>4</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/daegong/projects/baduk/docs/ops/state/log/backup.out.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/daegong/projects/baduk/docs/ops/state/log/backup.err.log</string>
</dict>
</plist>
```

- [x] **Step 2: launchd에 등록**

Run:
```bash
cp /Users/daegong/projects/baduk/ops/launchd/com.inkbaduk.backup.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.inkbaduk.backup.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.inkbaduk.backup.plist
launchctl list | grep com.inkbaduk.backup
```
Expected: 마지막 줄에 `com.inkbaduk.backup`가 보인다.

- [x] **Step 3: 수동 트리거로 검증**

Run:
```bash
launchctl start com.inkbaduk.backup
sleep 10
ls -la ~/baduk-backups/daily/
tail -5 /Users/daegong/projects/baduk/docs/ops/state/log/backup.out.log
```
Expected: `daily/`에 백업 파일이 늘었고, `backup.out.log`에 `백업 완료.`가 보인다. `backup.err.log`가 비어 있어야 한다.

- [x] **Step 4: 커밋**

```bash
git add ops/launchd/com.inkbaduk.backup.plist
git commit -m "feat(ops): 매일 04시 백업 launchd 작업"
```

`~/Library/LaunchAgents/`의 plist 사본은 머신 로컬 상태라 커밋 대상이 아니다.

---

### Task 3: `backup-verify.md` 러닝북 (검증 기준 #2)

오케스트레이터가 12·18시에 수행하는 백업 검증 절차. 신선도·티어 개수 확인 + 복원 드릴.

**Files:**
- Create: `docs/ops/runbooks/backup-verify.md`

- [x] **Step 1: `docs/ops/runbooks/backup-verify.md` 작성**

`[FENCE]`는 실제 백틱 세 개(```)로 치환한다. 최종 파일에 `[FENCE]` 문자열이 남으면 안 된다.

```markdown
# 러닝북: 백업 검증

- 주기: 매일 12시·18시 (오케스트레이터)
- 등급: 🟢 자율
- 목적: 로컬 백업이 신선하고 복원 가능한 상태인지 확인한다.

## 절차

### 1. 신선도

[FENCE]bash
NEWEST=$(ls -1t ~/baduk-backups/daily/*.db.gz 2>/dev/null | head -1)
echo "최신 백업: ${NEWEST:-없음}"
[ -n "$NEWEST" ] && find "$NEWEST" -mtime +1 -print
[FENCE]
판정: 최신 백업이 없거나, `find ... -mtime +1`이 파일을 출력하면(=30시간 이상 오래됨) 경보.

### 2. 티어 개수

[FENCE]bash
for t in daily weekly monthly; do
  echo "$t: $(ls -1 ~/baduk-backups/$t/*.db.gz 2>/dev/null | wc -l | tr -d ' ')개"
done
[FENCE]
판정: `daily`가 0개면 경보(백업 미생성). weekly·monthly는 0이어도 정상(아직 해당 요일/날짜가 안 옴).

### 3. 복원 드릴

[FENCE]bash
NEWEST=$(ls -1t ~/baduk-backups/daily/*.db.gz 2>/dev/null | head -1)
DRILL=/tmp/baduk-restore-drill.db
rm -f "$DRILL"
gunzip -c "$NEWEST" > "$DRILL"
sqlite3 "$DRILL" "PRAGMA integrity_check;"
sqlite3 "$DRILL" "SELECT count(*) FROM sqlite_master WHERE type='table';"
rm -f "$DRILL"
[FENCE]
판정: `integrity_check`가 `ok`를 출력하고 테이블 수가 1 이상이면 정상. 그 외는 경보(백업 손상).

## 결과 처리

1. 결과를 `state/log/YYYY-MM-DD.md`에 추가한다.
2. `state/dashboard.md`의 백업 상태 행을 갱신한다.
3. 경보 사유가 있으면 `state/incidents.md`에 기록한다. Telegram 보고는
   오케스트레이터가 실행 요약으로 처리한다.
```

- [x] **Step 2: 러닝북 명령 실측 검증**

backup-verify.md의 1~3번 bash 블록을 그대로 터미널에서 실행한다.
Run: 각 블록을 순서대로 실행.
Expected: 최신 백업 경로 출력, daily ≥ 1개, `integrity_check` → `ok`, 테이블 수 ≥ 1. 명령이 깨지면 러닝북을 고친다.

- [x] **Step 3: 커밋**

```bash
git add docs/ops/runbooks/backup-verify.md
git commit -m "feat(ops): 백업 검증 러닝북"
```

---

### Task 4: `ops/stack.sh`에 `restart prod` 추가

prod launchd 두 서비스를 재시작하는 서브커맨드. 배포 승급·장애 복구가 쓴다.

**Files:**
- Modify: `ops/stack.sh`

- [x] **Step 1: `usage` 함수 갱신**

`ops/stack.sh`의 다음 줄을 찾는다:
```bash
usage() { echo "사용법: ops/stack.sh {up|down|ps} staging | ops/stack.sh ps prod" >&2; exit 1; }
```
다음으로 교체한다:
```bash
usage() { echo "사용법: ops/stack.sh {up|down|ps} staging | ops/stack.sh {ps|restart} prod" >&2; exit 1; }
```

- [x] **Step 2: `prod_restart` 함수 추가**

`ops/stack.sh`에서 `prod_ps()` 함수 정의가 끝나는 닫는 중괄호 `}` 바로 다음 줄에 아래 함수를 추가한다(빈 줄 하나 띄우고):

```bash
prod_restart() {
  local uid; uid="$(id -u)"
  for svc in com.baduk.api com.baduk.web; do
    launchctl kickstart -k "gui/$uid/$svc"
    echo "$svc 재시작 요청"
  done
  echo "기동 대기 20초..."
  sleep 20
  prod_ps
}
```

- [x] **Step 3: `case` 분기에 `restart/prod` 추가**

`ops/stack.sh`의 다음 블록을 찾는다:
```bash
  ps/staging)   staging_ps ;;
  ps/prod)      prod_ps ;;
  *)            usage ;;
```
다음으로 교체한다:
```bash
  ps/staging)   staging_ps ;;
  ps/prod)      prod_ps ;;
  restart/prod) prod_restart ;;
  *)            usage ;;
```

- [x] **Step 4: 문법 검사**

Run: `bash -n /Users/daegong/projects/baduk/ops/stack.sh`
Expected: 출력 없음, 종료 코드 0.

- [x] **Step 5: 사용법 출력 확인**

Run: `ops/stack.sh`
Expected: `사용법: ops/stack.sh {up|down|ps} staging | ops/stack.sh {ps|restart} prod` 출력.

- [x] **Step 6: 커밋**

```bash
git add ops/stack.sh
git commit -m "feat(ops): stack.sh에 restart prod 추가"
```

`restart prod`의 실제 실행 검증은 Task 8(배포 검증)에서 한다.

---

### Task 5: `deploy.md` 러닝북

staging→prod 승급 절차. 🟡 승인 게이트.

**Files:**
- Create: `docs/ops/runbooks/deploy.md`

- [x] **Step 1: `docs/ops/runbooks/deploy.md` 작성**

`[FENCE]`는 실제 백틱 세 개(```)로 치환한다.

```markdown
# 러닝북: 배포 (staging → prod 승급)

- 등급: 🟡 승인 — prod를 바꾸므로 Telegram 승인 후에만 3단계를 실행한다.
- 전제: 승급할 변경이 feature 브랜치에 커밋돼 있다.

## 1. staging 검증

feature 브랜치를 staging worktree에 체크아웃하고 빌드+테스트한다.

[FENCE]bash
BR=<feature-branch>
git -C .worktrees/staging fetch origin
git -C .worktrees/staging checkout "$BR"
( cd .worktrees/staging/backend && source .venv311/bin/activate \
    && pip install -e ".[dev]" -q && alembic upgrade head && pytest -q )
( cd .worktrees/staging/web && npm run build && npm test -- --run )
[FENCE]
판정: pytest·npm test·npm build가 모두 통과해야 다음 단계로. 하나라도 실패하면 중단하고
실패를 보고한다 — prod는 건드리지 않는다.

## 2. 제안 (🟡)

`runbooks/telegram-protocol.md`의 승인 절차대로 `state/pending-approvals.md`에 항목을
추가하고 Telegram으로 제안한다. 항목의 "실행 절차"에는 아래 3단계를 적는다 —
브랜치명과, 승급 직전 기록할 `main` SHA 자리를 포함한다.

## 3. 승급 (승인 후에만)

[FENCE]bash
PREV=$(git rev-parse main)            # 롤백 대상 — 반드시 먼저 기록
echo "롤백 SHA: $PREV"
git checkout main && git merge --no-ff <feature-branch>
( cd backend && source .venv311/bin/activate \
    && pip install -e ".[dev]" -q && alembic upgrade head )
( cd web && npm run build )
ops/stack.sh restart prod
[FENCE]
주의: prod web은 `npm start`가 `.next`를 서빙하므로 `npm run build` 없이는 새 코드가
반영되지 않는다. backend 의존성이 안 바뀌었으면 `pip install`은 건너뛰어도 된다.

## 4. 사후 확인 + 롤백

[FENCE]bash
curl -fs --max-time 10 http://localhost:8000/api/health && echo " prod-backend OK"
curl -fs --max-time 10 http://localhost:3000 >/dev/null && echo "prod-web OK"
[FENCE]
판정: 둘 다 OK면 승급 성공 — `state/log/`에 기록하고 Telegram으로 결과 회신.

헬스체크가 실패하면 **롤백**한다(3단계에서 기록한 `$PREV` 사용):

[FENCE]bash
git checkout main && git reset --hard <PREV-SHA>
( cd web && npm run build )
ops/stack.sh restart prod
curl -fs --max-time 10 http://localhost:8000/api/health && echo " 롤백 후 OK"
[FENCE]
롤백 후에도 실패하면 `incident.md`로 전환하고 Telegram 긴급 경보.
```

- [x] **Step 2: 커밋**

```bash
git add docs/ops/runbooks/deploy.md
git commit -m "feat(ops): 배포 승급 러닝북"
```

---

### Task 6: `incident.md` 러닝북 + 자율성 정책 보강

장애 대응 절차와, 그것이 의존하는 안전 복구 화이트리스트를 자율성 정책에 박는다.

**Files:**
- Create: `docs/ops/runbooks/incident.md`
- Modify: `docs/ops/autonomy-policy.md`

- [x] **Step 1: `docs/ops/autonomy-policy.md`에 화이트리스트 절 추가**

`docs/ops/autonomy-policy.md` 맨 끝(마지막 줄 다음)에 아래를 추가한다:

```markdown

## 장애 안전 복구 화이트리스트

아래 동작은 **healthcheck가 감지한 장애에 대응하는 중**, **장애당 1회**에 한해 🟢 자율이다.
장애 맥락 밖에서 prod를 재시작하는 것은 여전히 🟡다 — 이것은 명시적 예외다.

- prod launchd 서비스 재시작 — 프로세스는 떠 있으나 `/api/health` 무응답이거나 다운일 때 `ops/stack.sh restart prod`.
- 디스크 압박 해소 — 보존 정책 초과 백업·오래된 `.run/staging-*.log` 삭제. prod 데이터는 불가.
- staging 스택 재시작 — `ops/stack.sh down staging` 후 `ops/stack.sh up staging`.

루프 가드 — 직전 실행에서 같은 대상을 이미 복구했는데 또 실패면 재시도하지 않고 에스컬레이션한다.
```

- [x] **Step 2: `docs/ops/runbooks/incident.md` 작성**

`[FENCE]`는 실제 백틱 세 개(```)로 치환한다.

```markdown
# 러닝북: 장애 대응

- 등급: 🟢 안전 복구 한정 (`autonomy-policy.md`의 화이트리스트). 그 외 에스컬레이션.
- 입력: healthcheck가 보고한 실패 항목 (예: prod backend 무응답, staging backend 다운).
- 트리거: 오케스트레이터가 healthcheck 실패를 잡으면 이 러닝북으로 연결한다.

## 절차

### 1. 실패 분류

실패 항목이 `autonomy-policy.md`의 "장애 안전 복구 화이트리스트"에 해당하는가.
- 해당하면 → 2번(안전 복구).
- 해당하지 않으면(DB 손상, 재시작 루프, prod 데이터 디스크 풀, 코드 오류 등) → 4번(에스컬레이션).

### 2. 루프 가드

`state/incidents.md`를 읽는다. 직전 실행에서 같은 대상을 이미 복구한 기록이 있으면
재시도하지 않고 4번(에스컬레이션)으로 간다.

### 3. 안전 복구 (1회)

화이트리스트의 해당 동작을 1회 수행한다.
- prod 서비스 무응답/다운 → `ops/stack.sh restart prod`
- staging 스택 이상 → `ops/stack.sh down staging` 후 `ops/stack.sh up staging`
- 디스크 압박 → 보존 초과 백업·오래된 `.run/staging-*.log` 삭제

복구 후 재확인:
[FENCE]bash
sleep 20
curl -fs --max-time 10 http://localhost:8000/api/health && echo " 복구 후 prod OK"
[FENCE]
(staging 모의 검증 시에는 `http://localhost:8100/api/health`로 확인한다.)

- 재확인 OK → 5번(기록).
- 재확인 실패 → 4번(에스컬레이션).

### 4. 에스컬레이션

자동 수정하지 않는다. `state/incidents.md`에 항목을 추가하고
`runbooks/telegram-protocol.md`의 알림 형식으로 Telegram 긴급 경보를 보낸다.

### 5. 기록

복구 성공·에스컬레이션 모두 `state/incidents.md`와 `state/log/YYYY-MM-DD.md`에
시각·대상·조치·결과를 기록한다. 루프 가드가 다음 실행에서 이 기록을 읽는다.
```

- [x] **Step 3: 커밋**

```bash
git add docs/ops/autonomy-policy.md docs/ops/runbooks/incident.md
git commit -m "feat(ops): 장애 대응 러닝북 + 안전 복구 화이트리스트"
```

---

### Task 7: 오케스트레이터 + 대시보드 통합

새 러닝북을 오케스트레이터 루프에 연결하고, 대시보드에 백업 상태 행을 추가한다.

**Files:**
- Modify: `docs/ops/orchestrator-prompt.md`
- Modify: `docs/ops/state/dashboard.md`

- [x] **Step 1: `orchestrator-prompt.md`의 러닝북 선별 블록 갱신**

`docs/ops/orchestrator-prompt.md`에서 다음 블록을 찾는다:
```markdown
1. **due한 러닝북 선별**
   - `docs/ops/runbooks/healthcheck.md` — 매 실행마다 수행.
   - (sub-project 1~4에서 백업검증·사용통계 러닝북이 추가되면 여기에 포함된다.)
```
다음으로 교체한다:
```markdown
1. **due한 러닝북 선별**
   - `docs/ops/runbooks/healthcheck.md` — 매 실행마다 수행.
   - `docs/ops/runbooks/backup-verify.md` — 매 실행마다 수행.
   - healthcheck가 prod 실패를 잡으면 `docs/ops/runbooks/incident.md`로 연결한다.
   - (sub-project 2~4에서 사용통계 러닝북이 추가되면 여기에 포함된다.)
```

- [x] **Step 2: `dashboard.md`에 백업 상태 행 추가**

`docs/ops/state/dashboard.md`에서 다음 블록을 찾는다:
```markdown
## 스택 상태

| 스택 | 상태 | 마지막 확인 |
|---|---|---|
| prod | 미확인 | - |
| staging | 미확인 | - |
```
바로 다음에 빈 줄 하나 띄우고 아래를 추가한다:
```markdown
## 백업 상태

| 항목 | 값 |
|---|---|
| 최신 백업 | 미확인 |
| daily / weekly / monthly | - / - / - |
```

- [x] **Step 3: 커밋**

```bash
git add docs/ops/orchestrator-prompt.md docs/ops/state/dashboard.md
git commit -m "feat(ops): 오케스트레이터에 백업검증·장애 러닝북 연결 + 대시보드 백업 행"
```

---

### Task 8: 배포 검증 (검증 기준 #3)

`deploy.md`의 staging 검증과 `restart prod`를 실제로 실행해 배포 경로가 동작함을 실증한다.

**Files:**
- 없음 (실행 검증만. Telegram 더미 제안 단계는 컨트롤러가 처리)

- [x] **Step 1: staging 빌드+테스트 (deploy.md 1단계)**

staging worktree의 현재 코드로 `deploy.md` 1단계 명령을 실행한다(검증이므로 feature 브랜치 체크아웃은 생략, 현재 detached HEAD 그대로).
Run:
```bash
( cd .worktrees/staging/backend && source .venv311/bin/activate \
    && alembic upgrade head && pytest -q )
( cd .worktrees/staging/web && npm run build )
```
Expected: pytest 통과, `npm run build` 성공. 실패하면 출력을 그대로 보고한다.

- [x] **Step 2: `restart prod` 실행 (deploy.md 3단계 일부)**

Run: `ops/stack.sh restart prod`
Expected: `com.baduk.api`·`com.baduk.web` 재시작 요청, 20초 대기 후 `prod_ps` 출력. 짧은 순단 후 prod가 돌아온다.

- [x] **Step 3: 사후 헬스체크 (deploy.md 4단계)**

Run:
```bash
sleep 5
curl -fs --max-time 10 http://localhost:8000/api/health && echo " prod-backend OK"
curl -fs --max-time 10 http://localhost:3000 >/dev/null && echo "prod-web OK"
```
Expected: 둘 다 OK — `restart prod` 후 prod가 정상 복귀했다. 실패하면 launchd가 `KeepAlive`로 복구할 때까지 60초 더 기다렸다 재확인하고, 그래도 실패면 BLOCKED로 보고.

- [x] **Step 4: 커밋 없음**

실행 검증 태스크다. Telegram 더미 승급 제안은 컨트롤러가 별도로 처리한다.

---

### Task 9: 장애 대응 검증 (검증 기준 #4)

staging 백엔드를 일부러 중단해 `incident.md`의 감지→안전 복구→재확인 경로를 실증한다. prod는 건드리지 않는다.

**Files:**
- 없음 (실행 검증만)

- [x] **Step 1: staging 가동 확인**

Run: `ops/stack.sh ps staging`
Expected: staging-backend·web 가동 중. 내려가 있으면 `ops/stack.sh up staging` 후 45초 대기.

- [x] **Step 2: staging 백엔드 강제 중단 (장애 모의)**

Run:
```bash
lsof -ti :8100 | xargs kill -9 2>/dev/null || true
sleep 2
curl -fs --max-time 5 http://localhost:8100/api/health || echo "staging backend 다운 확인"
```
Expected: `staging backend 다운 확인` — 8100 포트가 응답하지 않는다.

- [x] **Step 3: `incident.md` 절차 수행**

`incident.md`의 절차를 입력 "staging backend 다운"으로 수행한다 — ① 분류: staging 스택 이상은 화이트리스트 해당 → ② 루프 가드: `incidents.md`에 직전 동일 복구 기록 없음 → ③ 안전 복구: `ops/stack.sh down staging` 후 `ops/stack.sh up staging` → 재확인.
Run:
```bash
ops/stack.sh down staging
ops/stack.sh up staging
sleep 45
curl -fs --max-time 10 http://localhost:8100/api/health && echo " 복구 후 staging OK"
```
Expected: `복구 후 staging OK` — 안전 복구로 staging 백엔드가 되살아났다.

- [x] **Step 4: incidents.md 기록**

`incident.md` 5단계대로 `docs/ops/state/incidents.md`에 항목을 추가한다(기존 "(없음)"을 대체):
```markdown
## 이력

### 2026-05-23 — staging backend 다운 (검증)
- 감지: :8100 무응답
- 조치: 안전 복구 — staging 스택 재시작
- 결과: 복구 후 :8100 OK
- 비고: sub-project 1 검증 기준 #4 — incident.md 경로 실증.
```

- [x] **Step 5: 커밋**

```bash
git add docs/ops/state/incidents.md
git commit -m "test(ops): 장애 대응 러닝북 검증 — staging 모의 복구"
```

---

### Task 10: 통합 검증 + 대시보드 갱신

검증 기준 4가지를 한 번에 통과시키고 대시보드를 갱신한다. 문서만으로 완료 선언 금지.

**Files:**
- Modify: `docs/ops/state/dashboard.md`
- Modify: `docs/ops/state/log/2026-05-23.md` (없으면 Create)

- [x] **Step 1: 검증 기준 #1 — 백업 + launchd**

Run:
```bash
launchctl list | grep com.inkbaduk.backup
ls -1 ~/baduk-backups/daily/*.db.gz | wc -l
```
Expected: 작업 등록됨, daily 백업 ≥ 1개.

- [x] **Step 2: 검증 기준 #2 — backup-verify 러닝북**

`docs/ops/runbooks/backup-verify.md`의 1~3번 bash 블록을 실행.
Expected: 신선도·티어 개수 출력, 복원 드릴 `integrity_check` → `ok`.

- [x] **Step 3: 검증 기준 #3 — 배포 경로**

Task 8이 통과했는지 확인한다 — `ops/stack.sh ps prod`로 prod 정상, `bash -n ops/stack.sh`로 `restart prod` 분기 문법 OK.
Expected: prod 정상, 문법 OK.

- [x] **Step 4: 검증 기준 #4 — 장애 대응**

`docs/ops/state/incidents.md`에 Task 9의 검증 항목이 기록돼 있는지 확인.
Expected: staging 모의 복구 이력 존재.

- [x] **Step 5: 대시보드 + 로그 갱신**

`docs/ops/state/dashboard.md`의 백업 상태 행을 Step 1~2 실측값(최신 백업 시각, daily/weekly/monthly 개수)으로 채운다. `docs/ops/state/log/2026-05-23.md`에 다음을 추가한다(파일 없으면 생성, 기존 항목 삭제 금지):
```markdown
## (현재시각) — 운영팀 SRE(sub-project 1) 구축 완료
- 검증 기준 4/4 통과: ① 백업+launchd ② 백업검증 러닝북 ③ 배포 경로 ④ 장애 대응
```

- [x] **Step 6: 커밋**

```bash
git add docs/ops/state
git commit -m "feat(ops): 운영팀 SRE 구축 완료 — 검증 기준 4/4 통과"
```

- [x] **Step 7: 최종 보고**

검증 기준 4가지의 실제 출력을 보고하고 sub-project 1 완료를 알린다.

---

## 검증 기준 (spec)

1. `ops/backup.sh`가 `~/baduk-backups/daily/`에 원자적 gzip 스냅샷 생성, 보존 정리 동작, `com.inkbaduk.backup` launchd 등록. → Task 1, 2, 10
2. `backup-verify.md`가 신선도·티어 개수 확인 + 복원 드릴 `integrity_check` 통과. → Task 3, 10
3. `deploy.md` staging 빌드+테스트 green + `ops/stack.sh restart prod` 1회 후 prod 헬스 OK. → Task 8, 10
4. `incident.md` — staging 백엔드 중단 → 감지 → 안전 복구 → 재헬스체크 OK. → Task 9, 10
