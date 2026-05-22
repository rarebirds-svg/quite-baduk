# Agentic Ops — 하위 프로젝트 1: 운영팀 SRE

- 작성일: 2026-05-23
- 상태: 설계 승인 완료, 구현 계획 대기
- 의존: 하위 프로젝트 0 (운영 기반) — `2026-05-22-agentic-ops-foundation-design.md`
- 범위: inkbaduk 운영의 **배포·백업·장애 대응** 계층

## 배경

하위 프로젝트 0이 운영 기반(prod/staging 분리, `docs/ops/` 구조, 자율성 정책,
Telegram 배선, launchd 오케스트레이터 + healthcheck 러닝북)을 구축했다. 이 1번은
그 위에 SRE 도메인 — 배포·백업·장애 대응 — 을 올린다.

### 현재 상태 (조사 확정)

- prod는 macOS launchd(`com.baduk.api` :8000, `com.baduk.web` :3000)로 리포 작업
  트리에서 직접 실행된다. prod web은 `npm start`가 `web/.next` 빌드 산출물을 서빙한다.
- **prod DB 백업이 0개다.** `backend/deploy/r2_backup.sh`(R2 업로드 스크립트)는
  존재하나 cron 미등록·rclone 미설치·R2 remote 미설정 — 한 번도 연결된 적이 없다.
  라이브 서비스인데 백업이 없는 것이 현재 최대 운영 리스크다.
- 배포 재시작 절차는 `launchctl kickstart -k gui/<uid>/com.baduk.api`.

### 결정된 설계 축

- **백업**: 로컬 다중 세대 백업 (외부 의존 0). 디스크 장애 취약성은 수용.
- **장애 대응**: 안전 복구는 자율, 나머지는 에스컬레이션.
- **배포**: 🟡 승인 게이트 (하위 0의 자율성 정책 그대로).

## 접근 — C (작업 성격별 분리)

검토한 3가지.

- **A. 전부 러닝북** — 백업처럼 결정적인 작업까지 LLM이 실행 — 비용·실패점 낭비.
- **B. 전용 에이전트** — `.claude/agents/`에 SRE 에이전트 추가 — 백업엔 과함.
- **C. 작업 성격별 분리 (채택)** — 백업 생성은 순수 셸 스크립트 + launchd(결정적,
  LLM 불필요). 판단이 필요한 배포·장애만 러닝북으로 두고 오케스트레이터/범용
  서브에이전트가 실행. 검증(백업 신선도·복원 드릴)만 러닝북.

## 설계

### 섹션 1 — 백업 (로컬 다중 세대)

순수 셸 스크립트 + launchd. LLM 불개입.

- **`ops/backup.sh`** — `sqlite3 backend/data/baduk.db ".backup '<tmp>'"`(원자적·WAL
  안전) → gzip → 세대 저장소로 이동 → 보존 정책대로 정리.
- **저장 위치** — `~/baduk-backups/` (리포 트리 밖). prod가 리포 트리에서 직접
  실행되므로 백업을 트리 안에 두지 않는다.
- **세대 구조** — `daily/`(최근 14개) · `weekly/`(일요일분, 8개) ·
  `monthly/`(매월 1일분, 12개). 스크립트가 요일·날짜를 보고 해당 티어에 복사하고
  개수 초과분을 오래된 순으로 삭제. 보존 개수는 스크립트 상단 변수로 조정 가능.
- **`com.inkbaduk.backup` launchd 작업** — 매일 04:00 실행. plist는 `ops/launchd/`.
- **`docs/ops/runbooks/backup-verify.md`** — 오케스트레이터가 12·18시에 수행하는
  🟢 검증 러닝북. 최신 백업 신선도(<30시간), 티어별 개수 확인, 주기적 복원 드릴 —
  백업 사본을 풀어 `sqlite3 ... "PRAGMA integrity_check"` + 핵심 테이블 행 수 확인.
  이상 시 Telegram 경보 + `incidents.md` 기록.

### 섹션 2 — 배포 (staging → prod 승급)

**`docs/ops/runbooks/deploy.md`** — 🟡 승인 게이트.

1. **staging 검증** — feature 브랜치를 `.worktrees/staging`에서 빌드+테스트
   (`pytest`, `npm run build`, `npm test`). 통과해야 다음 단계로.
2. **제안** — Telegram으로 승급 제안 (브랜치·커밋·변경 요약을 `pending-approvals.md`
   AP 항목으로). 승인 전 prod 변경 없음.
3. **승급** (승인 후) — 승급 직전 `main` SHA 기록 → feature 브랜치를 `main`에 머지 →
   `backend` 의존성 변경 시 `pip install` + `alembic upgrade head` → `web`
   재빌드(`npm run build`) → `ops/stack.sh restart prod`로 launchd 두 서비스 재시작.
4. **사후 확인** — `/api/health`·web 헬스체크. 실패 시 **롤백** — 기록한 이전 SHA로
   `main`을 되돌리고 재빌드·재시작·재확인.

핵심 — prod web은 `npm start`가 `.next`를 서빙하므로 머지만으로는 반영되지 않는다.
deploy 러닝북은 `npm run build`를 반드시 포함한다. `ops/stack.sh`에 `restart prod`
(두 서비스 `launchctl kickstart -k`)를 추가한다.

### 섹션 3 — 장애 대응 (안전 복구 자율 + 에스컬레이션)

**`docs/ops/runbooks/incident.md`** — healthcheck가 prod 실패를 잡으면 오케스트레이터가
이 러닝북으로 연결한다.

**안전 복구 화이트리스트** — 장애가 감지된 경우에 한해 자율 실행 가능한 한정된 복구.

- prod launchd 서비스 재시작 — 프로세스는 떠 있으나 `/api/health` 무응답이거나
  다운일 때 `launchctl kickstart -k`. (순수 크래시는 `KeepAlive`가 이미 처리.)
- 디스크 압박 해소 — 보존 정책 초과 백업·오래된 `.run/staging-*.log` 삭제.
  **prod 데이터는 불가.**
- staging 스택 재시작.

전부 한정적·가역적·복구 전용이다. **그 외 전부 에스컬레이션** — DB 손상, 재시작
루프, prod 데이터로 인한 디스크 풀, KataGo·코드 레벨 오류는 자동 수정 금지,
Telegram 경보 + `incidents.md` 기록.

**루프 가드** — 직전 실행에서 같은 서비스를 안전 재시작했는데 또 실패면
(`incidents.md` 확인) 재시작하지 않고 에스컬레이션. 복구 후엔 healthcheck를
재실행해 확인하고, 여전히 실패면 에스컬레이션한다.

### 섹션 4 — 자율성 정책 보강 + 오케스트레이터 통합

- **`autonomy-policy.md`에 "장애 안전 복구 화이트리스트" 절 추가** — 섹션 3의 동작들은
  *감지된 장애 대응 중*, *장애당 1회*에 한해 🟢. 장애 맥락 밖에서 prod 재시작은
  여전히 🟡. "라이브 변경은 전부 승인" 원칙의 명시적 예외임을 문서에 박는다.
- **`orchestrator-prompt.md` 갱신** — 러닝북 세트에 `backup-verify.md` 추가,
  healthcheck 실패 시 `incident.md`로 연결. 일일 백업 생성 자체는 별도 launchd
  작업이라 오케스트레이터 밖이다.
- **`dashboard.md`** — 백업 상태 행(최신 백업 시각·티어별 개수) 추가.

### 섹션 5 — 범위 경계

**포함** — `ops/backup.sh` + `com.inkbaduk.backup` launchd + `backup-verify.md`,
`deploy.md` + `ops/stack.sh restart prod`, `incident.md` + 자율성 정책 보강,
오케스트레이터 통합.

**제외** — 하위 프로젝트 2~4(개발·콘텐츠·지원). 전용 `.claude/agents/` SRE
에이전트는 만들지 않는다(접근 C — 러닝북을 범용 서브에이전트가 실행).
공개 도메인(cloudflared) 외형 점검은 범위 밖 — 별도 후속.

## 검증 기준

이 4가지가 실제 명령 실행으로 통과하면 하위 프로젝트 1 완료. 문서만으로 완료 선언 금지.

1. `ops/backup.sh`가 `~/baduk-backups/daily/`에 원자적 gzip 스냅샷을 생성하고,
   보존 정리가 동작하며, `com.inkbaduk.backup` launchd 작업이 등록된다.
2. `backup-verify.md`가 신선도·티어 개수를 확인하고, 복원 드릴에서 백업 사본의
   `PRAGMA integrity_check`가 통과한다.
3. `deploy.md`의 staging 빌드+테스트가 green이고, 더미 승급 제안이 Telegram에
   도달하며, `ops/stack.sh restart prod` 1회 실행 후 prod 헬스가 OK다
   (`KeepAlive`가 복구를 보장하며 짧은 순단이 발생 — 수용하기로 결정됨).
4. `incident.md` — staging 백엔드를 일부러 중단하면 러닝북이 감지하고, 안전 복구로
   재기동한 뒤 재헬스체크가 OK다 (prod 아닌 staging으로 모의해 라이브 무영향).

## 리스크와 완화

| 리스크 | 완화 |
|---|---|
| 라이브 백업 0개 | 섹션 1을 최우선 — 로컬 다중 세대 백업 즉시 구축 |
| 로컬 백업의 디스크 장애 취약성 | 수용된 트레이드오프. 후속에서 오프사이트 복제 검토 가능 |
| 자율 prod 재시작이 루프에 빠짐 | 장애당 1회 제한 + `incidents.md` 루프 가드 |
| 배포가 prod web `.next`를 갱신 못 함 | deploy 러닝북에 `npm run build` 필수 포함 |
| 배포 실패 후 복구 불가 | 승급 직전 `main` SHA 기록 → 롤백 경로 명시 |

## 다음 단계

이 spec 승인 후 `writing-plans` 스킬로 하위 프로젝트 1의 구현 계획을 작성한다.
하위 2~4는 각자 brainstorm → spec → plan 사이클을 거친다.
