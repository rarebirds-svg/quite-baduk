# Agentic Ops — 운영 자동화 정지 방지 (Watchdog & Drift 안정화)

- 작성일: 2026-05-25
- 상태: 설계 승인 완료, 구현 계획 대기
- 범위: launchd 잡 무음 정지·plist drift·알림 채널 단일 실패점을 구조적으로 제거
- 선행 spec: [`2026-05-22-agentic-ops-foundation-design.md`](2026-05-22-agentic-ops-foundation-design.md), [`2026-05-23-agentic-ops-sre-design.md`](2026-05-23-agentic-ops-sre-design.md)

## 배경

agentic ops 기반 (Phase 0~3)이 구축돼 launchd 잡 6개(orchestrator 4회/일,
dev-cycle, content-draft, content-ingest, analytics-weekly, backup)가 운영 자동화를
돌리고 있다. 그러나 2026-05-25 진단에서 **약 41시간 동안 어떤 잡도 실행되지
않은 무음 정지**를 발견했다.

### 진단 결과 (2026-05-25 기준)

- prod 자체는 정상 (`/api/health` 200 OK, `web` 200 OK, db OK).
- launchd 잡 6개 모두 `launchctl list`에 load 상태로 존재.
- 그러나 `launchctl print gui/501/com.inkbaduk.ops-orchestrator` →
  `runs = 1`, `state = not running`, `last exit code = 0`.
  즉 load 이후 **정확히 1회만** 실행되고 이후 calendar trigger가 트리거되지 않았다.
- `orchestrator-runs.log` 마지막 entry: `2026-05-24 02:01:11 종료`. 그 이후 4회 ×
  약 41시간 = **최소 6회의 scheduled trigger 누락**.
- 모든 `*.err.log` 0바이트 — 실행 후 죽은 게 아니라 trigger 자체가 안 됨.
- Telegram 알림은 `TELEGRAM_BOT_TOKEN` 부재 + `--channels` 미부여(과거 기록)로
  만성적으로 미발송 → 41시간 정지를 아무도 감지하지 못함.

### Root cause 가설 (3중 결합)

1. **plist drift** — repo의 `ops/launchd/com.inkbaduk.ops-orchestrator.plist`는
   옛 스케줄(12:00 / 18:00, 2회/일). 실제 `~/Library/LaunchAgents/`에 load된
   plist는 commit cb43377 이후 새 스케줄(06:30·12:30·18:30·23:30, 4회/일).
   **단일 진실 공급원이 없어** 어느 plist가 실제로 도는지 검증 불가.
2. **launchd calendar trigger 누락** — macOS launchd는 sleep/wake 상태나 시스템
   부하 상황에서 `StartCalendarInterval`을 놓칠 수 있다. 한 번 놓치면
   다음 정시까지 idle 상태로 남는다.
3. **감지 백업 부재** — Telegram이 primary 알림이지만 끊겨 있고, fallback이 없어
   "운영이 멈췄다"는 사실이 외부로 새지 못한다.

세 가지 중 하나만 있어도 위험하고, 세 개가 결합돼 41시간 무음 정지가 났다.

## 비목표 (YAGNI)

- 사용자 행동 지표·KPI 대시보드 — 별도 spec.
- 에이전트 출력 품질 평가(eval) — 별도 spec.
- 새 launchd 잡 도메인 추가 (마케팅·지원 등) — 별도 spec.
- launchd를 다른 스케줄러(systemd-timers, cron, supervisord)로 교체 — 현 인프라 유지.
- 잡 자체의 비즈니스 로직 변경(orchestrator-prompt, runbook 내용 등) — 손대지 않는다.

## 설계

### 섹션 1 — plist 단일 진실화 (drift 제거)

**원칙**: `ops/launchd/*.plist`가 단일 진실 공급원.
`~/Library/LaunchAgents/com.inkbaduk.*.plist`는 그 복사본이며, drift가 발생하면
즉시 감지된다.

**신규 스크립트**: `ops/sync-launchd.sh`
- 동작:
  1. `ops/launchd/com.inkbaduk.*.plist` 각각에 대해 `~/Library/LaunchAgents/`
     대상 파일과 sha256 비교.
  2. 다르면 복사 + `launchctl bootout gui/$(id -u)/<Label>` 후
     `launchctl bootstrap gui/$(id -u) <path>` 재등록.
  3. 결과를 `docs/ops/state/log/launchd-sync.log`에 append.
- idempotent — 변경 없으면 아무 액션 안 함, 종료 코드 0.
- `--check` 플래그 — 변경 사항을 출력만 하고 적용 안 함. healthcheck가 호출.

**healthcheck runbook 확장**:
- `docs/ops/runbooks/healthcheck.md`에 한 섹션 추가 — "launchd plist drift".
- `ops/sync-launchd.sh --check`를 실행, 차이 있으면 dashboard에 경고 + Telegram 보고.

**자율성 등급**:
- `--check`는 read-only → 🟢 자율.
- 실제 sync (bootout/bootstrap)는 prod 운영에 영향 → 🟡 승인.
  (예외: 신규 잡 등록만 있는 경우는 🟢 — 기존 잡 영향 없음. 이건 단순화 위해 일단 🟡로.)

### 섹션 2 — Watchdog launchd 잡

**신규 plist**: `ops/launchd/com.inkbaduk.ops-watchdog.plist`
- `Label`: `com.inkbaduk.ops-watchdog`
- `StartInterval`: 3600 (1시간마다) — `StartCalendarInterval`이 아니라 interval로
  설정해 sleep/wake 후에도 깨어나면 즉시 한 번 돈다.
- `ProgramArguments`: `/Users/daegong/projects/baduk/ops/run-watchdog.sh`
- 로그: `docs/ops/state/log/watchdog.{out,err}.log`

**신규 스크립트**: `ops/run-watchdog.sh`
- launchd wrapper. `ops/ops.env` source 후 `ops/check-staleness.sh` 호출.

**신규 스크립트**: `ops/check-staleness.sh`
- 각 잡별 임계값을 정의:
  | 잡 | 로그 파일 | 임계 (stale 판정) |
  |---|---|---|
  | orchestrator | `orchestrator-runs.log` | 8h |
  | dev-cycle | `dev-cycle-runs.log` | 30h (1일 1회) |
  | content-draft | `content-draft-runs.log` | 30h |
  | content-ingest | `content-ingest-runs.log` | 30h |
  | analytics-weekly | `analytics-weekly-runs.log` | 8일 |
  | backup | `backup.out.log` | 30h |
- 각 로그의 마지막 `^\[YYYY-MM-DD HH:MM:SS\]` timestamp 추출 → 현재와 비교.
- 임계 초과 시 incident 생성:
  - `docs/ops/state/incidents.md`에 entry append (incident id: `WD-YYYYMMDD-N`).
  - `ops/notify.sh "<message>"` 호출 (섹션 3).
- 동일 incident에 대해 **1시간 1회**만 알림 (단순 rate-limit: `state/.watchdog-cooldown`
  파일에 마지막 알림 시각 기록).
- 자가 보호: watchdog 자신의 로그(`watchdog.out.log`)는 검사 대상에서 제외.

**자율성**: watchdog 잡 등록 = 🟡 (신규 launchd 잡 추가). 등록 이후
watchdog의 알림·incident 기록 = 🟢 자율 (감지만 함, prod 변경 없음).

### 섹션 3 — 알림 채널 다중화

**신규 스크립트**: `ops/notify.sh "<message>"`
- 채널 순차 시도, 첫 성공에서 멈춤. 모두 실패하면 stderr에 출력 + exit 1.
- 채널 순서:
  1. **Telegram** — `ops/notify-telegram.sh`
     - `TELEGRAM_BOT_TOKEN`과 `TELEGRAM_CHAT_ID`가 `ops/ops.env`에 있으면 curl로
       `sendMessage` 호출. 둘 중 하나라도 없거나 HTTP non-2xx면 실패로 간주.
  2. **macOS notification** — `ops/notify-macos.sh`
     - `osascript -e 'display notification "<msg>" with title "inkbaduk watchdog"'`.
     - 토큰 불필요, 항상 동작. 사용자가 맥 미니 화면에 접근 가능할 때만 유효하지만
       Telegram 끊긴 상황의 last-resort.
  3. **파일 보고** — `docs/ops/state/incidents.md`에 entry는 항상 기록 (위 두
     채널과 무관, watchdog가 직접 수행).

**Telegram 토큰 부재 시 거동**: `notify-telegram.sh`가 즉시 비0 종료 → macOS
notification으로 fallback. watchdog는 정상 동작한다.

**자율성**: `ops/ops.env`에 토큰 추가 = 🔴 (사람 전용). 그 외 스크립트
구현·통합 = 🟢 자율.

### 섹션 4 — sleep/wake 안전

**진단 절차** (구현이 아니라 문서화):
- `docs/ops/runbooks/healthcheck.md`에 "sleep/wake 검증" 섹션 추가.
- 절차:
  1. `pmset -g` 출력 캡처 — `sleep`·`standby`·`hibernatemode`·`womp` 확인.
  2. `pmset -g sched` — 예약된 wake/restart 스케줄 확인.
  3. `log show --predicate 'subsystem == "com.apple.xpc.launchd" AND eventMessage CONTAINS "com.inkbaduk"' --last 7d` —
     실제 launchd가 잡을 trigger한 이력 검사.
- 이 정보로 sleep이 trigger 누락의 원인인지 사람이 판단.

**옵션 권장 (사람 결정)**:
- 옵션 A: `pmset -a sleep 0`로 sleep 완전 비활성 (라이브 서버이므로 합리적).
- 옵션 B: `pmset repeat wakeorpoweron MTWRFSU 06:25:00` 등으로 매일 06:25에 강제 wake.
- 옵션 C: watchdog의 `StartInterval=3600`이 사실상 1시간마다 깨워서 다른 잡들도
  연쇄 trigger되도록 OS에 신호 (불확실 — 검증 필요).

**자율성**: `pmset` 변경 = 🔴 (시스템 전역 설정). 문서화·진단은 🟢.

## 아키텍처 다이어그램

```
ops/launchd/*.plist          ← 단일 진실 (git)
        │
        │ ops/sync-launchd.sh
        │   (--check: read-only / 적용: 🟡)
        ▼
~/Library/LaunchAgents/*.plist   ← OS 로드 대상
        │
        ├── com.inkbaduk.ops-orchestrator  → run-orchestrator.sh  → orchestrator-runs.log
        ├── com.inkbaduk.dev-cycle         → run-dev-cycle.sh     → dev-cycle-runs.log
        ├── com.inkbaduk.content-*         → run-content-*.sh     → content-*-runs.log
        ├── com.inkbaduk.analytics-weekly  → run-analytics-weekly.sh → analytics-weekly-runs.log
        ├── com.inkbaduk.backup            → backup.sh            → backup.out.log
        └── com.inkbaduk.ops-watchdog (NEW, 1h interval)
                    │
                    ▼
              ops/check-staleness.sh
                    │  임계 초과 감지 시
                    ▼
              ops/notify.sh "<msg>"
                    ├─→ notify-telegram.sh (primary)
                    ├─→ notify-macos.sh    (fallback)
                    └─→ incidents.md append (항상)
```

## 인터페이스 요약

| 산출물 | 종류 | 진입점 | 호출자 |
|---|---|---|---|
| `ops/sync-launchd.sh` | bash | `sync-launchd.sh [--check]` | 사람·healthcheck |
| `ops/launchd/com.inkbaduk.ops-watchdog.plist` | plist | (launchd 등록) | sync-launchd.sh |
| `ops/run-watchdog.sh` | bash | (launchd wrapper) | launchd |
| `ops/check-staleness.sh` | bash | `check-staleness.sh` | run-watchdog.sh |
| `ops/notify.sh` | bash | `notify.sh "<msg>"` | check-staleness.sh, healthcheck |
| `ops/notify-telegram.sh` | bash | `notify-telegram.sh "<msg>"` | notify.sh |
| `ops/notify-macos.sh` | bash | `notify-macos.sh "<msg>"` | notify.sh |
| `docs/ops/runbooks/healthcheck.md` | md | (orchestrator가 읽음) | orchestrator |
| `docs/ops/autonomy-policy.md` | md | (참조 문서) | 에이전트 |

모든 신규 스크립트는 첫 줄에 한국어 한 줄 헤더 주석 (`# ...`) 포함 — 규칙 6.

## 테스트 / 검증

| 케이스 | 절차 | 기대 |
|---|---|---|
| sync `--check` 정상 | 변경 없는 상태에서 실행 | exit 0, 출력 없음 |
| sync `--check` drift 감지 | `~/Library/LaunchAgents/`의 plist 1개를 수동 변조 후 실행 | drift 항목 stdout, exit 1 |
| watchdog stale 감지 | orchestrator-runs.log 마지막 entry timestamp를 9시간 전으로 변조 | incident entry 생성 + notify 호출 |
| Telegram 토큰 없을 때 fallback | `TELEGRAM_BOT_TOKEN` 비우고 notify 호출 | macOS notification 노출, exit 0 |
| Telegram·macOS 둘 다 실패 | macOS notification API 차단 환경 | incidents.md에는 기록, notify exit 1, watchdog는 계속 |
| rate-limit | 같은 incident에 1시간 내 2회 호출 | 두 번째 호출에서 notify 스킵, incidents.md 중복 없음 |
| 신규 watchdog 잡 등록 | `sync-launchd.sh` 실행 후 `launchctl list` | `com.inkbaduk.ops-watchdog` 표시 |
| watchdog 자기 보호 | watchdog 자체 로그 stale 검사 제외 | watchdog가 watchdog를 incident로 기록하지 않음 |

## 자율성 정책 업데이트

`docs/ops/autonomy-policy.md`에 추가:

```md
### Watchdog 감지 액션 화이트리스트

watchdog가 8시간 이상 stale인 잡을 감지한 경우, **장애당 1회**에 한해 🟢 자율:

- `launchctl kickstart -k gui/$(id -u)/com.inkbaduk.<label>` — 정지된 잡 강제 트리거.
- 같은 잡이 재시도 후에도 stale이면 🟡로 격상, 사람 승인 요청.
```

## 위험 / 미해결 질문

1. **watchdog 자체가 멈추면?** — `StartInterval=3600`은 OS 부하·sleep에 비교적
   강하지만 100% 보장 아님. 외부(예: GitHub Actions cron으로 prod에 ping)는 이 spec
   범위 밖. **잔여 위험 수용**.
2. **Telegram fallback이 macOS notification이면 원격에서 안 보임** — 사용자가 외출
   중일 때 무용지물. 토큰 복구가 진짜 해법. 토큰 복구 절차는 spec 범위 밖
   (사용자 수동).
3. **plist drift sync를 🟡로 하면 자율 복구 안 됨** — 첫 sync는 사람 승인.
   이후 drift는 healthcheck가 감지·보고만 하고 사람이 결정. 자율도가 너무 낮다고
   판단되면 다음 iteration에서 "신규 추가만 🟢, 기존 변경 🟡"로 세분화.
4. **incident id 충돌** — `WD-YYYYMMDD-N`의 N은 그 날 watchdog 알림 순번. 동시
   실행은 없다고 가정 (StartInterval=3600 + lock 파일).
5. **sleep/wake가 실제 원인인지 확정 안 됨** — root cause는 plist drift + trigger
   누락 + 알림 부재의 **결합**으로 봐도 충분. 정확한 OS-level 원인 추적은 위 4번
   섹션의 진단 절차로 가능하지만 필수 아님.

## 단계 분해 (writing-plans에서 상세화)

1. healthcheck runbook에 plist drift 진단 + sleep/wake 절차 추가 (문서만)
2. `ops/sync-launchd.sh` 구현 + `--check` 모드
3. drift 1차 sync 실행 (🟡 — 사람 승인 후 적용, repo plist를 진실로)
4. `ops/notify-{telegram,macos}.sh` + `ops/notify.sh` 구현
5. `ops/check-staleness.sh` 구현 + rate-limit
6. `ops/run-watchdog.sh` + `ops/launchd/com.inkbaduk.ops-watchdog.plist` 작성
7. watchdog 잡 등록 (🟡 승인 후 `sync-launchd.sh` 실행)
8. autonomy-policy.md 업데이트 (watchdog kickstart 화이트리스트)
9. 통합 검증 — orchestrator-runs.log stale 시뮬레이션으로 end-to-end 알림 확인

각 단계가 끝나면 commit (규칙 9 — semantic commits). 7번 단계 전까지는 모두
non-destructive — 사람 승인은 7번에 집중된다.
