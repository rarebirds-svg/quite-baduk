# 운영 자동화 정지 방지 (Watchdog & Drift 안정화) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** launchd 잡 6개의 무음 정지·plist drift·알림 단일 실패점을 구조적으로 제거 — Watchdog 잡과 알림 다중화로 "다시 41시간 정지해도 모르는" 상황을 끝낸다.

**Architecture:** `ops/launchd/*.plist`를 단일 진실로 두고 `~/Library/LaunchAgents/`에 동기화하는 idempotent 스크립트, 1시간 간격으로 깨어나 각 잡의 마지막 실행 timestamp를 검사하는 새 launchd 잡 (`com.inkbaduk.ops-watchdog`), Telegram→macOS→파일 3단 fallback 알림 체인.

**Tech Stack:** bash 5+, macOS launchd, curl (Telegram Bot API), osascript (macOS notification), shasum.

**Spec:** [`docs/superpowers/specs/2026-05-25-agentic-ops-watchdog-design.md`](../specs/2026-05-25-agentic-ops-watchdog-design.md)

**자율성 게이트 (사람 승인 필요):** Task 3 (1차 drift sync), Task 8 (watchdog plist 등록). 나머지는 🟢 자율.

---

## Task 1: healthcheck runbook 확장 (plist drift + sleep/wake 진단 절차)

**Files:**
- Modify: `docs/ops/runbooks/healthcheck.md`

- [ ] **Step 1: 기존 runbook 끝(범위 메모 직전)에 두 섹션 추가**

`docs/ops/runbooks/healthcheck.md`의 "## 결과 처리" 다음, "## 범위 메모" 직전에 아래 내용을 삽입.

````markdown
### 4. launchd plist drift

```bash
ops/sync-launchd.sh --check
```
판정: exit 0 + 출력 없음이면 정상. 비0이면 `~/Library/LaunchAgents/`의 plist가
repo `ops/launchd/`와 다름 → drift incident로 기록.

### 5. sleep/wake 진단 (필요 시)

watchdog가 잡 stale을 감지한 경우 또는 launchd trigger 누락이 의심될 때만 실행한다.

```bash
pmset -g | grep -E '^\s+(sleep|standby|hibernatemode|womp)'
pmset -g sched
log show --predicate 'subsystem == "com.apple.xpc.launchd" AND eventMessage CONTAINS "com.inkbaduk"' \
  --last 7d | tail -50
```
판정: `sleep` 값이 0이 아니거나, 7일 log에서 예상되는 trigger 시각의 entry가
빠져 있으면 `state/incidents.md`에 sleep-related로 기록하고 사람에게 보고.

## 결과 처리 (추가)

4·5번에서 비정상이면 watchdog incident와 별도로 기록한다 (id 접두: `DRIFT-` / `SLEEP-`).
````

- [ ] **Step 2: 검증**

Run:
```bash
grep -c "launchd plist drift" docs/ops/runbooks/healthcheck.md
grep -c "sleep/wake 진단" docs/ops/runbooks/healthcheck.md
```
Expected: 각각 `1`.

- [ ] **Step 3: Commit**

```bash
git add docs/ops/runbooks/healthcheck.md
git commit -m "docs(ops): healthcheck에 plist drift·sleep/wake 진단 절차 추가"
```

---

## Task 2: `ops/sync-launchd.sh` 구현 (idempotent + --check)

**Files:**
- Create: `ops/sync-launchd.sh`

- [ ] **Step 1: 스크립트 작성**

`ops/sync-launchd.sh` 생성. 첫 줄에 한국어 헤더 (규칙 6).

```bash
#!/usr/bin/env bash
# repo의 ops/launchd/*.plist를 ~/Library/LaunchAgents/에 동기화하고 launchd에 재등록한다.
set -euo pipefail

ROOT="/Users/daegong/projects/baduk"
SRC_DIR="$ROOT/ops/launchd"
DST_DIR="$HOME/Library/LaunchAgents"
LOG="$ROOT/docs/ops/state/log/launchd-sync.log"
CHECK_ONLY=0

if [[ "${1:-}" == "--check" ]]; then
  CHECK_ONLY=1
fi

mkdir -p "$DST_DIR" "$(dirname "$LOG")"

drift=0
for src in "$SRC_DIR"/com.inkbaduk.*.plist; do
  [ -f "$src" ] || continue
  name=$(basename "$src")
  dst="$DST_DIR/$name"
  label="${name%.plist}"

  if [ ! -f "$dst" ]; then
    echo "MISSING $name (not in $DST_DIR)"
    drift=1
    if [ "$CHECK_ONLY" -eq 0 ]; then
      cp "$src" "$dst"
      launchctl bootstrap "gui/$(id -u)" "$dst"
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] installed $name" >> "$LOG"
    fi
    continue
  fi

  src_hash=$(shasum -a 256 "$src" | awk '{print $1}')
  dst_hash=$(shasum -a 256 "$dst" | awk '{print $1}')
  if [ "$src_hash" != "$dst_hash" ]; then
    echo "DRIFT $name (repo != installed)"
    drift=1
    if [ "$CHECK_ONLY" -eq 0 ]; then
      launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
      cp "$src" "$dst"
      launchctl bootstrap "gui/$(id -u)" "$dst"
      echo "[$(date '+%Y-%m-%d %H:%M:%S')] resynced $name" >> "$LOG"
    fi
  fi
done

if [ "$CHECK_ONLY" -eq 1 ] && [ "$drift" -ne 0 ]; then
  exit 1
fi
exit 0
```

- [ ] **Step 2: 실행 권한 부여 + dry-check 실행**

```bash
chmod +x ops/sync-launchd.sh
ops/sync-launchd.sh --check; echo "exit=$?"
```
Expected: 현재 drift가 1개 이상 있을 가능성이 높으므로 `DRIFT com.inkbaduk.*.plist` 출력 + `exit=1`. 이게 정상 (Task 3에서 사람 승인 후 적용).

- [ ] **Step 3: 멱등성 검증 (수동 dry-run)**

수동으로 동일 hash 가짜 환경 시뮬레이션:
```bash
diff <(shasum -a 256 ops/launchd/*.plist | awk '{print $1, $NF}' | sort) \
     <(shasum -a 256 ~/Library/LaunchAgents/com.inkbaduk.*.plist 2>/dev/null | awk '{print $1, $NF}' | sort) || true
```
이건 그냥 진단 — drift가 어디인지 사람이 확인하기 위함. 결과 기록.

- [ ] **Step 4: Commit**

```bash
git add ops/sync-launchd.sh
git commit -m "feat(ops): launchd plist drift 감지·동기화 스크립트 (sync-launchd.sh)"
```

---

## Task 3: 🟡 1차 drift sync 실행 (사람 승인 게이트)

**Files:** 변경 없음 (실행만)

- [ ] **Step 1: drift 내용을 사람에게 보고**

```bash
ops/sync-launchd.sh --check
```
출력을 사용자에게 제시. "현재 N개 plist가 drift 상태. repo를 단일 진실로 적용하면
`~/Library/LaunchAgents/` 측 N개가 repo 버전으로 덮어쓰여지고 launchd가 재등록됩니다.
진행할까요?" 라고 명시적으로 묻는다.

- [ ] **Step 2: 사용자 승인 대기**

승인 답신 없으면 STOP — Task 4로 넘어가지 말고 대기. (이 plan은 자율로 진행돼도
이 단계에서 멈추는 것이 정상이다.)

- [ ] **Step 3: 승인 받으면 실제 sync 실행**

```bash
ops/sync-launchd.sh
echo "exit=$?"
launchctl list | grep com.inkbaduk
```
Expected: `exit=0`, 6개 잡 모두 `launchctl list`에 보임.

- [ ] **Step 4: sync 후 재확인**

```bash
ops/sync-launchd.sh --check; echo "exit=$?"
```
Expected: `exit=0`, 출력 없음.

- [ ] **Step 5: 결과 기록 (코드 변경 없음, log만)**

```bash
tail -20 docs/ops/state/log/launchd-sync.log
```
출력에 "installed"/"resynced" 항목 확인. 커밋 대상 코드 변경은 없으므로 commit 단계 생략.

---

## Task 4: `ops/notify-telegram.sh`

**Files:**
- Create: `ops/notify-telegram.sh`

- [ ] **Step 1: 스크립트 작성**

```bash
#!/usr/bin/env bash
# Telegram Bot API로 메시지를 보낸다. 토큰/채팅ID 없거나 non-2xx면 비0 종료(상위 fallback 트리거).
set -euo pipefail

MSG="${1:-}"
if [ -z "$MSG" ]; then
  echo "usage: notify-telegram.sh <message>" >&2
  exit 2
fi

ROOT="/Users/daegong/projects/baduk"
[ -f "$ROOT/ops/ops.env" ] && { set -a; . "$ROOT/ops/ops.env"; set +a; }

: "${TELEGRAM_BOT_TOKEN:=}"
: "${TELEGRAM_CHAT_ID:=}"

if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
  echo "notify-telegram: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing" >&2
  exit 1
fi

http_code=$(curl -s -o /tmp/notify-telegram.out -w "%{http_code}" \
  --max-time 10 \
  -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_CHAT_ID}" \
  --data-urlencode "text=${MSG}")

if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
  exit 0
fi
echo "notify-telegram: HTTP $http_code" >&2
cat /tmp/notify-telegram.out >&2 2>/dev/null || true
exit 1
```

- [ ] **Step 2: 권한 + dry-run (토큰 없이 즉시 fallback 확인)**

```bash
chmod +x ops/notify-telegram.sh
ops/notify-telegram.sh "test"; echo "exit=$?"
```
Expected: `notify-telegram: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing` 에러 + `exit=1`.

- [ ] **Step 3: Commit**

```bash
git add ops/notify-telegram.sh
git commit -m "feat(ops): Telegram Bot API 알림 스크립트 (notify-telegram.sh)"
```

---

## Task 5: `ops/notify-macos.sh`

**Files:**
- Create: `ops/notify-macos.sh`

- [ ] **Step 1: 스크립트 작성**

```bash
#!/usr/bin/env bash
# macOS 로컬 알림(osascript)을 띄운다. Telegram 실패 시 last-resort 채널.
set -euo pipefail

MSG="${1:-}"
if [ -z "$MSG" ]; then
  echo "usage: notify-macos.sh <message>" >&2
  exit 2
fi

# osascript 인자 escape — 작은따옴표/큰따옴표 모두 안전하게.
escaped=$(printf '%s' "$MSG" | sed 's/"/\\"/g')
osascript -e "display notification \"$escaped\" with title \"inkbaduk watchdog\""
```

- [ ] **Step 2: 권한 + 실제 알림 띄우기**

```bash
chmod +x ops/notify-macos.sh
ops/notify-macos.sh "watchdog 자가 테스트 알림"; echo "exit=$?"
```
Expected: 맥 우상단에 알림 1회 + `exit=0`. (macOS 알림 권한이 osascript에 거부된 환경에서는 비0 가능 — 그때는 시스템 설정에서 권한 부여 필요.)

- [ ] **Step 3: Commit**

```bash
git add ops/notify-macos.sh
git commit -m "feat(ops): macOS 로컬 알림 fallback 스크립트 (notify-macos.sh)"
```

---

## Task 6: `ops/notify.sh` (오케스트레이터 — Telegram → macOS → file)

**Files:**
- Create: `ops/notify.sh`

- [ ] **Step 1: 스크립트 작성**

```bash
#!/usr/bin/env bash
# 알림 채널 다중화 진입점 — Telegram → macOS notification 순으로 시도, 첫 성공에서 멈춤.
set -euo pipefail

MSG="${1:-}"
if [ -z "$MSG" ]; then
  echo "usage: notify.sh <message>" >&2
  exit 2
fi

ROOT="/Users/daegong/projects/baduk"

if "$ROOT/ops/notify-telegram.sh" "$MSG" 2>/dev/null; then
  exit 0
fi

if "$ROOT/ops/notify-macos.sh" "$MSG" 2>/dev/null; then
  exit 0
fi

echo "notify: all channels failed for: $MSG" >&2
exit 1
```

- [ ] **Step 2: 권한 + 실제 시도 (토큰 없으면 macOS로 fallback)**

```bash
chmod +x ops/notify.sh
ops/notify.sh "통합 fallback 테스트"; echo "exit=$?"
```
Expected: 토큰이 없으면 Telegram 실패 → macOS 알림 + `exit=0`. 둘 다 실패면 `exit=1`.

- [ ] **Step 3: Commit**

```bash
git add ops/notify.sh
git commit -m "feat(ops): 알림 채널 다중화 오케스트레이터 (notify.sh)"
```

---

## Task 7: `ops/check-staleness.sh` (잡별 로그 신선도 검사 + rate-limit)

**Files:**
- Create: `ops/check-staleness.sh`

- [ ] **Step 1: 스크립트 작성**

```bash
#!/usr/bin/env bash
# launchd 잡들의 마지막 실행 timestamp가 임계 초과로 stale인지 검사하고 incident·알림을 발생시킨다.
set -euo pipefail

ROOT="/Users/daegong/projects/baduk"
LOG_DIR="$ROOT/docs/ops/state/log"
INCIDENTS="$ROOT/docs/ops/state/incidents.md"
COOLDOWN_DIR="$ROOT/docs/ops/state"
COOLDOWN_SECS=3600   # 같은 잡 1시간 1회 알림

# 잡 정의: "표시명|로그파일|임계(초)"
JOBS=(
  "orchestrator|orchestrator-runs.log|28800"      # 8h
  "dev-cycle|dev-cycle-runs.log|108000"           # 30h
  "content-draft|content-draft-runs.log|108000"   # 30h
  "content-ingest|content-ingest-runs.log|108000" # 30h
  "analytics-weekly|analytics-weekly-runs.log|691200"  # 8d
  "backup|backup.out.log|108000"                  # 30h
)

now=$(date +%s)
incidents_added=0

extract_last_ts() {
  # 마지막 "[YYYY-MM-DD HH:MM:SS]" 패턴 찾아 epoch 초로 변환. 없으면 빈 문자열.
  local file="$1"
  [ -f "$file" ] || return 0
  local ts_str
  ts_str=$(grep -oE '^\[[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\]' "$file" | tail -1 | tr -d '[]')
  [ -z "$ts_str" ] && return 0
  date -j -f "%Y-%m-%d %H:%M:%S" "$ts_str" +%s 2>/dev/null || true
}

check_cooldown() {
  local job="$1"
  local file="$COOLDOWN_DIR/.watchdog-cooldown-$job"
  [ -f "$file" ] || return 1   # cooldown 없음 → 알림 가능
  local last
  last=$(cat "$file" 2>/dev/null || echo 0)
  local diff=$(( now - last ))
  [ "$diff" -lt "$COOLDOWN_SECS" ]   # true면 아직 cooldown 중
}

write_cooldown() {
  local job="$1"
  echo "$now" > "$COOLDOWN_DIR/.watchdog-cooldown-$job"
}

append_incident() {
  local job="$1"
  local age_h="$2"
  local last_str="$3"
  local today
  today=$(date '+%Y%m%d')
  local id
  id="WD-$today-$(date +%H%M%S)"
  {
    echo ""
    echo "### $id — $job stale ${age_h}h"
    echo ""
    echo "- 감지: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "- 마지막 실행: ${last_str:-N/A}"
    echo "- 임계 초과 — watchdog가 자동 감지."
  } >> "$INCIDENTS"
}

for entry in "${JOBS[@]}"; do
  IFS='|' read -r job logname threshold <<<"$entry"
  logfile="$LOG_DIR/$logname"
  last_ts=$(extract_last_ts "$logfile")
  if [ -z "$last_ts" ]; then
    last_str="(로그 비어있음)"
    age=$threshold   # 비어있으면 무조건 stale
  else
    last_str=$(date -r "$last_ts" '+%Y-%m-%d %H:%M:%S')
    age=$(( now - last_ts ))
  fi

  if [ "$age" -ge "$threshold" ]; then
    if check_cooldown "$job"; then
      echo "[$job] stale but in cooldown — skip notify" >&2
      continue
    fi
    age_h=$(( age / 3600 ))
    append_incident "$job" "$age_h" "$last_str"
    msg="[inkbaduk] $job 잡 ${age_h}h 정지 — 마지막 실행 ${last_str:-N/A}"
    "$ROOT/ops/notify.sh" "$msg" || echo "[$job] notify 채널 전부 실패 (incident는 기록됨)" >&2
    write_cooldown "$job"
    incidents_added=$(( incidents_added + 1 ))
  fi
done

echo "watchdog 검사 완료 — 신규 incident $incidents_added 건"
exit 0
```

- [ ] **Step 2: 권한 + 정상 케이스 dry-run**

```bash
chmod +x ops/check-staleness.sh
ops/check-staleness.sh
```
Expected (현 시점 — 41시간 정지 상황): 여러 잡(orchestrator·dev-cycle·content-* 등)이 stale로 감지되어 incidents.md에 entry 추가 + notify.sh 호출. `신규 incident N 건` 출력. 사용자에게 알림 도달.

- [ ] **Step 3: cooldown 검증**

```bash
ops/check-staleness.sh
```
Expected: 동일 잡이 다시 stale이지만 cooldown 발동 → `stale but in cooldown — skip notify` stderr 출력, `신규 incident 0 건`.

- [ ] **Step 4: incidents.md에 entry 정상 기록 확인**

```bash
tail -30 docs/ops/state/incidents.md
```
Expected: `### WD-YYYYMMDD-HHMMSS — <job> stale Nh` 형식 entry들.

- [ ] **Step 5: Commit (cooldown 파일은 .gitignore 추가)**

먼저 `.gitignore`에 cooldown 파일 패턴이 있는지 확인:

```bash
grep -E "watchdog-cooldown" .gitignore || echo "추가 필요"
```

없으면 `.gitignore`에 한 줄 추가:

```
docs/ops/state/.watchdog-cooldown-*
```

그 다음 commit:

```bash
git add ops/check-staleness.sh docs/ops/state/incidents.md .gitignore
git commit -m "feat(ops): 잡 stale 감지·incident 기록·rate-limited 알림 (check-staleness.sh)"
```

---

## Task 8: `ops/run-watchdog.sh` (launchd wrapper) + plist

**Files:**
- Create: `ops/run-watchdog.sh`
- Create: `ops/launchd/com.inkbaduk.ops-watchdog.plist`

- [ ] **Step 1: wrapper 스크립트 작성**

`ops/run-watchdog.sh`:

```bash
#!/usr/bin/env bash
# launchd가 1시간마다 호출 — check-staleness.sh를 한 번 실행한다.
set -euo pipefail
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT"
[ -f ops/ops.env ] && { set -a; . ops/ops.env; set +a; }
exec ops/check-staleness.sh
```

- [ ] **Step 2: launchd plist 작성**

`ops/launchd/com.inkbaduk.ops-watchdog.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- 1시간마다 각 launchd 잡의 마지막 실행 timestamp를 검사하고 stale 시 알림을 보내는 watchdog. -->
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.inkbaduk.ops-watchdog</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/daegong/projects/baduk/ops/run-watchdog.sh</string>
  </array>
  <key>StartInterval</key>
  <integer>3600</integer>
  <key>StandardOutPath</key>
  <string>/Users/daegong/projects/baduk/docs/ops/state/log/watchdog.out.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/daegong/projects/baduk/docs/ops/state/log/watchdog.err.log</string>
</dict>
</plist>
```

- [ ] **Step 3: 권한 + wrapper 단독 실행 검증**

```bash
chmod +x ops/run-watchdog.sh
ops/run-watchdog.sh; echo "exit=$?"
```
Expected: cooldown 발동 상태일 가능성이 높아 `신규 incident 0 건` + `exit=0`. 만약 새로운 stale이 생긴 사이라면 incident 추가도 가능.

- [ ] **Step 4: plist 등록 전 drift 확인**

```bash
ops/sync-launchd.sh --check; echo "exit=$?"
```
Expected: 새 `com.inkbaduk.ops-watchdog.plist`가 `~/Library/LaunchAgents/`에 없으므로 `MISSING com.inkbaduk.ops-watchdog.plist` + `exit=1`.

- [ ] **Step 5: Commit**

```bash
git add ops/run-watchdog.sh ops/launchd/com.inkbaduk.ops-watchdog.plist
git commit -m "feat(ops): watchdog launchd 잡 정의 + 1시간 interval wrapper"
```

---

## Task 9: 🟡 watchdog 잡 등록 (사람 승인 게이트)

**Files:** 변경 없음 (launchd에만 영향)

- [ ] **Step 1: 등록 계획을 사람에게 보고**

"새 watchdog 잡 (`com.inkbaduk.ops-watchdog`)을 launchd에 등록합니다. 1시간 간격으로
`check-staleness.sh`를 실행하고 stale 감지 시 Telegram(없으면 macOS notification)으로
알림. prod 영향 없음 (감지만). 진행할까요?"

- [ ] **Step 2: 사용자 승인 대기**

승인 없으면 STOP — Task 10으로 가지 말고 대기.

- [ ] **Step 3: 승인 받으면 sync 실행**

```bash
ops/sync-launchd.sh; echo "exit=$?"
launchctl list | grep com.inkbaduk.ops-watchdog
launchctl print "gui/$(id -u)/com.inkbaduk.ops-watchdog" | head -20
```
Expected: `exit=0`, watchdog 잡이 list에 보임, `print` 출력에서 `state` 확인.

- [ ] **Step 4: 첫 트리거 강제 + 결과 확인**

```bash
launchctl kickstart -k "gui/$(id -u)/com.inkbaduk.ops-watchdog"
sleep 5
tail -5 docs/ops/state/log/watchdog.out.log
tail -5 docs/ops/state/log/watchdog.err.log
```
Expected: out.log에 `watchdog 검사 완료 — 신규 incident N 건` 또는 cooldown 메시지. err.log는 비어있거나 cooldown 안내만.

---

## Task 10: autonomy-policy.md 업데이트 (watchdog kickstart 화이트리스트)

**Files:**
- Modify: `docs/ops/autonomy-policy.md`

- [ ] **Step 1: "장애 안전 복구 화이트리스트" 섹션 끝에 항목 추가**

`docs/ops/autonomy-policy.md`의 기존 "## 장애 안전 복구 화이트리스트" 섹션, 마지막 bullet
("staging 스택 재시작") 다음에 새 bullet 추가:

```md
- watchdog 감지 잡 1회 재트리거 — `check-staleness.sh`가 stale로 감지한 잡에 대해
  `launchctl kickstart -k gui/$(id -u)/com.inkbaduk.<label>`로 강제 트리거.
  같은 incident에 재시도 후에도 stale이면 🟡로 격상해 사람 승인 요청.
```

- [ ] **Step 2: 검증**

```bash
grep -c "watchdog 감지 잡 1회 재트리거" docs/ops/autonomy-policy.md
```
Expected: `1`.

- [ ] **Step 3: Commit**

```bash
git add docs/ops/autonomy-policy.md
git commit -m "docs(ops): autonomy-policy에 watchdog kickstart 화이트리스트 추가"
```

---

## Task 11: 통합 end-to-end 검증 (stale 시뮬레이션)

**Files:** 변경 없음 (검증만, 부수효과로 incidents.md만 append)

- [ ] **Step 1: cooldown 초기화 (테스트를 위해)**

```bash
rm -f docs/ops/state/.watchdog-cooldown-*
```

- [ ] **Step 2: orchestrator 로그를 가상으로 9시간 전으로 만들기 (백업 후 임시 변조)**

```bash
cp docs/ops/state/log/orchestrator-runs.log /tmp/orch-backup.log
# 마지막 entry timestamp만 가상으로 9시간 전으로 추가
nine_h_ago=$(date -v-9H '+%Y-%m-%d %H:%M:%S')
echo "[$nine_h_ago] orchestrator 종료 (테스트 변조)" >> docs/ops/state/log/orchestrator-runs.log
```

- [ ] **Step 3: check-staleness.sh 실행**

```bash
ops/check-staleness.sh
```
Expected: orchestrator는 stale이 아닐 수 있으므로 (마지막 entry가 추가된 9h 전), 이 검증은 "**다른** 잡들 (실제로 40h+ stale인 dev-cycle 등)"에 대한 알림이 발생. `신규 incident N 건` 출력.

(만약 Task 3에서 plist sync 후 정시 trigger들이 도는 사이라면 각 잡 로그가 갱신돼 있을 수 있다. 그 경우는 실제 stale이 없으니 `신규 incident 0 건`. 둘 다 정상.)

- [ ] **Step 4: 알림 도달 확인**

알림이 어떤 채널로 갔는지 확인:
```bash
# Telegram이 살아있으면 텔레그램 메시지 확인 (사용자가 직접)
# 아니면 macOS 알림이 떴는지 확인 (사용자가 화면에서 확인)
tail -10 docs/ops/state/incidents.md
```
Expected: 시뮬레이션으로 trigger된 incident WD-* entry. 사용자가 "알림 받음" 또는 "받지 못함" 보고.

- [ ] **Step 5: 로그 원복**

```bash
mv /tmp/orch-backup.log docs/ops/state/log/orchestrator-runs.log
```

- [ ] **Step 6: 종합 dashboard 항목 추가**

`docs/ops/state/dashboard.md`의 적절한 위치에 watchdog 상태 한 줄 추가 (수동 편집):

```md
## Watchdog

| 항목 | 값 |
|---|---|
| 잡 등록 | `com.inkbaduk.ops-watchdog` 가동 중 (1h interval) |
| 마지막 실행 | (watchdog.out.log 최신 시각) |
| 최근 incident | (incidents.md WD-* 최신) |
```

실제 값을 채워 commit.

- [ ] **Step 7: 최종 commit**

```bash
git add docs/ops/state/dashboard.md
git commit -m "docs(ops): dashboard에 watchdog 상태 섹션 추가 + e2e 검증 통과"
```

---

## 자율성 게이트 요약

| Task | 등급 | 사람 개입 |
|---|---|---|
| 1, 2, 4, 5, 6, 7, 8, 10, 11 | 🟢 자율 | 불필요 (커밋·실행 모두 자율) |
| 3 (1차 drift sync) | 🟡 승인 | drift 보고 → 승인 → sync 실행 |
| 9 (watchdog 잡 등록) | 🟡 승인 | 등록 계획 보고 → 승인 → sync 실행 |

자율 실행 모드에서는 Task 3·9 직전에 멈추고 사용자에게 보고 후 답신을 기다린다.

## 검증 통과 기준

전체 plan이 끝났을 때:
- `launchctl list | grep com.inkbaduk` → 7개 잡 (기존 6 + watchdog) 모두 표시
- `ops/sync-launchd.sh --check` → exit 0, 출력 없음
- `docs/ops/state/log/watchdog.out.log` → 최근 entry가 1시간 이내
- `ops/notify.sh "test"` → exit 0 (Telegram 또는 macOS notification 도달)
- `docs/ops/state/incidents.md` → WD-* incident 최소 1개 (검증 단계에서 생성됨)
- `docs/ops/autonomy-policy.md` → watchdog kickstart 화이트리스트 포함
