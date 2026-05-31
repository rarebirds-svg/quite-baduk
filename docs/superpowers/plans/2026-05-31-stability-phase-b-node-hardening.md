# Phase B — 단일 노드 하드닝 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 맥미니 단일 노드의 가용성을, KeepAlive가 못 잡는 3가지 빈틈(머신 다운·hung 프로세스·맥미니 위의 감시자)을 메워 사람 개입 없이 자가 복구되도록 만든다.

**Architecture:** 코드/콘텐츠 이전 없음. (1) macOS 전원·로그인 설정으로 머신 레벨 복구, (2) watchdog에 HTTP 헬스 기반 자동 kickstart 추가, (3) 맥미니 밖 Cloudflare Worker Cron이 공개 엔드포인트를 외부에서 폴링해 Telegram 알림.

**Tech Stack:** bash, launchd, `pmset`, `launchctl`, Cloudflare Workers (wrangler), Telegram Bot API.

> **참고 — 테스트 정책:** 본 리포의 `ops/*.sh`는 단위 테스트 프레임워크가 없다(기존 관례). 셸 스크립트는 **드라이런 실행 + 명령 출력 관찰**로 검증한다. Worker는 `wrangler dev --test-scheduled`로 검증한다. Next.js 코드 변경이 없으므로 pytest/vitest 영향 없음.

> **사전 사실 (조사 완료):**
> - `~/Library/LaunchAgents/com.baduk.api.plist`·`com.baduk.web.plist` 둘 다 `KeepAlive=true`·`RunAtLoad=true` (프로세스 종료 시 자동 재시작은 이미 됨).
> - `/api/health`는 `{"status","db","katago_alive"}` 반환 (`backend/app/api/health.py`).
> - 알림 다중화 진입점은 `ops/notify.sh` (Telegram → macOS). Telegram 토큰 진실 공급원은 `~/.claude/channels/telegram/.env`, chat_id는 `ops/ops.env`(`TELEGRAM_CHAT_ID=1241277614`).
> - watchdog 코어는 `ops/check-staleness.sh`, launchd 진입은 `ops/run-watchdog.sh` (StartInterval 3600s, `com.inkbaduk.ops-watchdog`).

---

## File Structure

- Create: `backend/deploy/harden_macos.sh` — 머신 레벨 전원·복구 설정을 적용하는 1회성 스크립트.
- Modify: `backend/deploy/README.md` — 하드닝 절차 문서화.
- Create: `ops/check-health.sh` — HTTP 헬스 폴링 + 연속 실패 시 자동 kickstart 자가 교정.
- Modify: `ops/run-watchdog.sh` — staleness 검사 후 health 검사도 호출.
- Create: `ops/cloudflare/health-monitor/wrangler.toml` — 외부 모니터 Worker 설정.
- Create: `ops/cloudflare/health-monitor/src/index.js` — Cron 트리거 헬스 폴링 + Telegram 알림.
- Create: `ops/cloudflare/health-monitor/README.md` — 배포·시크릿 등록 절차.

---

## Task 1: 머신 레벨 자동 복구 설정

KeepAlive는 프로세스 종료만 잡는다. 정전·재부팅 후 머신이 사람 로그인 없이 서비스로 복귀하도록 전원·로그인을 설정한다.

**Files:**
- Create: `backend/deploy/harden_macos.sh`
- Modify: `backend/deploy/README.md`

- [ ] **Step 1: 하드닝 스크립트 작성**

`backend/deploy/harden_macos.sh`:

```bash
#!/usr/bin/env bash
# 맥미니 머신 레벨 자동 복구 설정 — 정전 자동부팅·슬립 금지·자동로그인 안내를 적용한다.
set -euo pipefail

if [ "$(uname)" != "Darwin" ]; then
  echo "이 스크립트는 macOS 전용입니다." >&2
  exit 1
fi

echo "== pmset 전원 정책 적용 (sudo 필요) =="
# 정전 복구 시 자동 부팅
sudo pmset -a autorestart 1
# 슬립·디스크 슬립 금지 (24/7 서비스)
sudo pmset -a sleep 0 disksleep 0
# Wake on network access 허용
sudo pmset -a womp 1 || true

echo
echo "== 현재 pmset 설정 =="
pmset -g | grep -E 'autorestart|(^| )sleep|disksleep|womp' || true

echo
echo "== 수동 1회 설정 (스크립트로 자동화 불가) =="
echo "  자동 로그인을 켜야 재부팅 후 GUI LaunchAgent(com.baduk.*)가 사람 개입 없이 기동됩니다."
echo "  시스템 설정 → 사용자 및 그룹 → 자동 로그인 → 이 계정 선택."
echo "  (cloudflared는 LaunchDaemon이라 로그인과 무관하게 부팅 시 기동됩니다.)"
```

- [ ] **Step 2: 실행 권한 부여 + 드라이 검증**

Run:
```bash
chmod +x backend/deploy/harden_macos.sh
bash -n backend/deploy/harden_macos.sh && echo "syntax OK"
```
Expected: `syntax OK` (구문 오류 없음). 실제 적용은 Step 3.

- [ ] **Step 3: 적용 + 설정 확인**

Run:
```bash
backend/deploy/harden_macos.sh
pmset -g | grep autorestart
```
Expected: `autorestart` 값이 `1`. 자동 로그인 안내가 출력됨 → 시스템 설정에서 1회 수동 활성화.

- [ ] **Step 4: README에 절차 추가**

`backend/deploy/README.md`의 "One-time setup" 섹션 끝에 추가:

```markdown
## 머신 레벨 자동 복구 (필수)

launchd KeepAlive는 프로세스 종료만 복구한다. 정전·재부팅 후 머신이 사람 개입
없이 서비스로 복귀하려면 전원·로그인 설정이 필요하다.

```bash
backend/deploy/harden_macos.sh
```

- `pmset autorestart 1` — 정전 복구 시 자동 부팅
- `pmset sleep 0` — 슬립 금지
- **자동 로그인 수동 활성화** — 시스템 설정 → 사용자 및 그룹 → 자동 로그인.
  `com.baduk.*`는 GUI 도메인 LaunchAgent라 로그인이 있어야 기동된다.

검증: 맥미니를 강제 재부팅 → 사람 개입 0으로 `curl -s https://<domain>/api/health`가
200을 반환하는지 확인.
```

- [ ] **Step 5: 커밋**

```bash
git add backend/deploy/harden_macos.sh backend/deploy/README.md
git commit -m "ops(deploy): 맥미니 머신 레벨 자동 복구 스크립트·문서 추가"
```

---

## Task 2: watchdog HTTP 헬스 자동 교정

KeepAlive·staleness watchdog 모두 "살아있으나 응답 불능(hung)"을 못 잡는다. HTTP 헬스를 폴링해 연속 N회 실패 시 자동으로 `launchctl kickstart`하고 incident·알림을 남긴다.

**Files:**
- Create: `ops/check-health.sh`
- Modify: `ops/run-watchdog.sh`

- [ ] **Step 1: 헬스 자가 교정 스크립트 작성**

`ops/check-health.sh`:

```bash
#!/usr/bin/env bash
# api·web HTTP 헬스를 폴링하고 연속 실패가 임계 넘으면 자동 kickstart·incident·알림을 수행한다.
set -euo pipefail

ROOT="/Users/daegong/projects/baduk"
STATE_DIR="$ROOT/docs/ops/state"
INCIDENTS="$STATE_DIR/incidents.md"

# 설정 (테스트 시 env로 덮어쓰기 가능)
API_URL="${HEALTH_API_URL:-http://127.0.0.1:8000/api/health}"
WEB_URL="${HEALTH_WEB_URL:-http://127.0.0.1:3000/}"
FAIL_THRESHOLD="${HEALTH_FAIL_THRESHOLD:-2}"   # watchdog가 1h 주기 → 2회면 ~2h 무응답
COOLDOWN_SECS="${HEALTH_COOLDOWN_SECS:-3600}"
DRY_RUN="${WATCHDOG_DRY_RUN:-0}"               # 1이면 kickstart 대신 명령만 출력

now=$(date +%s)

probe() {  # url → 0(2xx/3xx) | 1(실패)
  local url="$1" code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 "$url" 2>/dev/null || echo 000)
  [ "$code" -ge 200 ] && [ "$code" -lt 400 ]
}

remediate() {  # label → kickstart 대상 launchd label
  local label="$1"
  if [ "$DRY_RUN" = "1" ]; then
    echo "[dry-run] launchctl kickstart -k gui/$(id -u)/$label"
    return 0
  fi
  launchctl kickstart -k "gui/$(id -u)/$label"
}

check_one() {  # name url label
  local name="$1" url="$2" label="$3"
  local cfile="$STATE_DIR/.health-fail-$name"
  if probe "$url"; then
    rm -f "$cfile"
    echo "[$name] OK"
    return 0
  fi
  local fails
  fails=$(( $(cat "$cfile" 2>/dev/null || echo 0) + 1 ))
  echo "$fails" > "$cfile"
  echo "[$name] FAIL ($fails/$FAIL_THRESHOLD)"
  if [ "$fails" -lt "$FAIL_THRESHOLD" ]; then
    return 0
  fi

  # 쿨다운 — 무한 재시작 루프 방지
  local kfile="$STATE_DIR/.health-kick-$name"
  local lastk
  lastk=$(cat "$kfile" 2>/dev/null || echo 0)
  if [ $(( now - lastk )) -lt "$COOLDOWN_SECS" ]; then
    echo "[$name] 임계 초과나 쿨다운 중 — kickstart skip"
    return 0
  fi

  echo "[$name] 임계 초과 — 자동 kickstart 실행"
  remediate "$label"
  echo "$now" > "$kfile"
  rm -f "$cfile"
  {
    echo ""
    echo "### WD-$(date '+%Y%m%d-%H%M%S') — $name 헬스 ${fails}회 연속 실패 자동 kickstart"
    echo ""
    echo "- 감지: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "- 대상: $label / URL $url"
    echo "- watchdog가 자동 재시작 수행."
  } >> "$INCIDENTS"
  "$ROOT/ops/notify.sh" "[inkbaduk] $name ${fails}회 무응답 — 자동 kickstart 실행 ($label)" \
    || echo "[$name] notify 실패 (incident는 기록됨)" >&2
}

check_one "api" "$API_URL" "com.baduk.api"
check_one "web" "$WEB_URL" "com.baduk.web"
echo "health 검사 완료"
exit 0
```

- [ ] **Step 2: 구문 검증 + 정상 경로 드라이런**

Run (api/web가 떠 있는 prod에서):
```bash
chmod +x ops/check-health.sh
bash -n ops/check-health.sh && echo "syntax OK"
ops/check-health.sh
```
Expected: `syntax OK`, 이어서 `[api] OK` / `[web] OK` / `health 검사 완료`.

- [ ] **Step 3: 실패→자동교정 경로 드라이런 (실서비스 무영향)**

존재하지 않는 포트를 헬스 URL로 주입하고 임계 1, 드라이런으로 검증:
```bash
WATCHDOG_DRY_RUN=1 HEALTH_FAIL_THRESHOLD=1 \
  HEALTH_API_URL=http://127.0.0.1:59999/x \
  HEALTH_WEB_URL=http://127.0.0.1:59999/x \
  ops/check-health.sh
rm -f docs/ops/state/.health-fail-* docs/ops/state/.health-kick-*
```
Expected: `[api] FAIL (1/1)` → `[api] 임계 초과 — 자동 kickstart 실행` → `[dry-run] launchctl kickstart -k gui/<uid>/com.baduk.api` (web도 동일). 실제 kickstart는 일어나지 않음.

- [ ] **Step 4: watchdog 진입점에 연결**

`ops/run-watchdog.sh`를 수정 — `exec`를 일반 호출로 바꾸고 health 검사를 이어서 실행:

```bash
#!/usr/bin/env bash
# launchd가 1시간마다 호출 — staleness + health 검사를 한 번씩 실행한다.
set -euo pipefail
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT"
[ -f ops/ops.env ] && { set -a; . ops/ops.env; set +a; }
ops/check-staleness.sh || echo "check-staleness 비정상 종료" >&2
ops/check-health.sh    || echo "check-health 비정상 종료" >&2
```

- [ ] **Step 5: 통합 1회 실행 확인**

Run:
```bash
bash -n ops/run-watchdog.sh && echo "syntax OK"
ops/run-watchdog.sh
```
Expected: staleness 요약(`watchdog 검사 완료 …`)에 이어 `[api] OK`/`[web] OK`/`health 검사 완료` 출력.

- [ ] **Step 6: 커밋**

```bash
git add ops/check-health.sh ops/run-watchdog.sh
git commit -m "ops(watchdog): HTTP 헬스 연속 실패 시 자동 kickstart 자가 교정 추가"
```

- [ ] **Step 7: (수동) hung 주입 복구 검증**

prod에서 1회: uvicorn 마스터 PID에 `kill -STOP` → 두 watchdog 주기 후 자동 `kickstart`로 `/api/health` 복구 확인 → 확인 후 상태파일 정리. (자동화 불가한 머신 검증이므로 plan 외 수동 절차로 기록.)

---

## Task 3: 외부 독립 모니터 (Cloudflare Worker Cron)

현 watchdog은 맥미니 위에서 돈다 — 맥미니가 통째로 죽으면 알림도 못 온다. 맥미니 밖 Worker가 공개 헬스 URL을 외부에서 폴링해 실패 시 Telegram으로 알린다.

**Files:**
- Create: `ops/cloudflare/health-monitor/wrangler.toml`
- Create: `ops/cloudflare/health-monitor/src/index.js`
- Create: `ops/cloudflare/health-monitor/README.md`

- [ ] **Step 1: Worker 설정 작성**

`ops/cloudflare/health-monitor/wrangler.toml`:

```toml
# inkbaduk 외부 헬스 모니터 Worker — Cron으로 공개 /api/health를 폴링한다.
name = "inkbaduk-health-monitor"
main = "src/index.js"
compatibility_date = "2024-11-01"

[triggers]
crons = ["*/5 * * * *"]   # 5분마다

[vars]
HEALTH_URL = "https://inkbaduk.com/api/health"
# TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 은 `wrangler secret put` 으로 등록 (README 참조)
```

- [ ] **Step 2: Worker 로직 작성**

`ops/cloudflare/health-monitor/src/index.js`:

```javascript
// Cron 트리거로 공개 /api/health를 폴링하고 실패 시 Telegram으로 알린다.
async function notify(env, text) {
  const url = `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`;
  await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ chat_id: env.TELEGRAM_CHAT_ID, text }),
  });
}

async function probe(env) {
  try {
    const res = await fetch(env.HEALTH_URL, {
      signal: AbortSignal.timeout(10000),
      cf: { cacheTtl: 0 },
    });
    if (!res.ok) return `HTTP ${res.status}`;
    const body = await res.json();
    if (body.status !== "ok") return `status=${body.status} db=${body.db} katago=${body.katago_alive}`;
    return null; // 정상
  } catch (e) {
    return `unreachable: ${e.name}`;
  }
}

export default {
  async scheduled(_event, env, _ctx) {
    const problem = await probe(env);
    if (problem) {
      await notify(env, `[inkbaduk] 외부 모니터 — ${env.HEALTH_URL} 이상: ${problem}`);
    }
  },
  // 수동 점검용 HTTP 진입점 (`curl <worker-url>`)
  async fetch(_req, env) {
    const problem = await probe(env);
    return new Response(problem ? `FAIL: ${problem}` : "OK", { status: problem ? 503 : 200 });
  },
};
```

- [ ] **Step 3: 배포 절차 문서 작성**

`ops/cloudflare/health-monitor/README.md`:

```markdown
# inkbaduk 외부 헬스 모니터

맥미니 *밖*(Cloudflare 엣지)에서 5분마다 `/api/health`를 폴링해 실패 시 Telegram으로
알린다. 맥미니가 통째로 죽어도(머신·네트워크·Tunnel 다운) 이 감시자는 살아 있다.

## 배포

```bash
cd ops/cloudflare/health-monitor
npm i -g wrangler            # 최초 1회
wrangler login              # 브라우저 인증

# 시크릿 등록 (값은 ~/.claude/channels/telegram/.env, ops/ops.env 참조)
wrangler secret put TELEGRAM_BOT_TOKEN
wrangler secret put TELEGRAM_CHAT_ID

wrangler deploy
```

## 로컬 검증

```bash
# scheduled 핸들러 테스트 (정상이면 알림 없음, 이상이면 Telegram 발송)
wrangler dev --test-scheduled
curl "http://localhost:8787/__scheduled?cron=*/5+*+*+*+*"

# HTTP 진입점으로 즉시 상태 확인
curl http://localhost:8787    # OK 또는 FAIL: <이유>
```

## 검증 기준

cloudflared를 내려 origin을 죽인 뒤 5분 내 Telegram 알림 수신.
```

- [ ] **Step 4: 로컬 scheduled 검증**

Run:
```bash
cd ops/cloudflare/health-monitor
npx wrangler dev --test-scheduled &
sleep 3
curl -s "http://localhost:8787/__scheduled?cron=*/5+*+*+*+*"
curl -s http://localhost:8787
kill %1
```
Expected: HEALTH_URL이 정상이면 `OK`. (시크릿 미설정 상태에선 notify가 실패해도 probe 결과는 출력됨 — 배포 시 secret put으로 해결.)

- [ ] **Step 5: 배포 + 실패 알림 검증 (수동)**

README 절차로 `wrangler deploy` 후, prod에서 cloudflared를 잠시 내려 origin-down을 만들고 5분 내 Telegram 알림 수신을 1회 확인. 확인 후 cloudflared 복구.

- [ ] **Step 6: 커밋**

```bash
git add ops/cloudflare/health-monitor
git commit -m "ops(monitor): 맥미니 외부 Cloudflare Worker Cron 헬스 모니터 추가"
```

---

## 검증 기준 (Phase B 성공 정의)

- Task 1: 강제 재부팅 후 사람 개입 0으로 `/api/health` 200 복귀.
- Task 2: 헬스 실패→자동교정 드라이런이 kickstart 명령을 출력(Step 3), 통합 실행 정상(Step 5), 수동 hung 주입 복구(Step 7).
- Task 3: origin 강제 다운 시 5분 내 외부 모니터 Telegram 알림 수신(Step 5).

---

## Self-Review 메모

- **스펙 커버리지:** 스펙 Phase B의 B1(머신 복구)=Task1, B2(hung 자동교정)=Task2, B3(외부 모니터)=Task3. B4(폴백 페이지)는 스펙대로 Phase C로 흡수 — 본 plan 비포함.
- **플레이스홀더:** 모든 스크립트 전문 수록, "적절한 에러 처리" 류 없음. 외부 머신·재부팅·배포 검증은 자동화 불가하여 명시적 수동 절차로 분리.
- **타입/이름 일관성:** launchd label `com.baduk.api`/`com.baduk.web`, 상태파일 prefix `.health-fail-*`/`.health-kick-*`, env 키 `HEALTH_*`/`WATCHDOG_DRY_RUN` 전 태스크 일치.
