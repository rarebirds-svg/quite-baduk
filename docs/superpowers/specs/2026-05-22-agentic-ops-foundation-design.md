# Agentic Ops — 하위 프로젝트 0: 운영 기반 (Foundation)

- 작성일: 2026-05-22
- 상태: 설계 승인 완료, 구현 계획 대기
- 범위: inkbaduk을 agentic AI로 A-to-Z 운영하기 위한 **기반 계층**

## 배경

inkbaduk(Go/Baduk 웹앱)을 agentic AI로 전 영역 운영하는 체계를 구축한다.
운영 대상 영역은 ① 기능 개발·코드 ② 배포·모니터링·장애 대응 ③ 콘텐츠 운영
④ 사용자 지원·분석 ⑤ SEO 페이지 자동 생성이다.

### 현재 상태 (제약 조건)

- inkbaduk은 **이미 라이브 서비스 중**이다.
- 호스팅은 **맥 미니 한 대** — Claude Code 실행 머신과 라이브 호스트가 동일하다.
- 개발과 운영이 **분리되어 있지 않다**. 에이전트가 실수하면 즉시 라이브 장애가 된다.
- 자산: `.claude/agents/` 5종 에이전트(editorial-implementer, design-token-guardian,
  visual-qa, korean-copy-qa, a11y-auditor), Telegram 플러그인 연동.

### 결정된 설계 축

- **자율성**: 영역별 차등 자율 — 저위험은 자율, 라이브 변경은 승인, 비가역은 금지.
- **환경 분리**: 같은 맥 미니에 prod/staging을 도커 포트로 분리.

## 스코프 분해

요청 전체("A-to-Z 운영")는 단일 스펙으로 담기엔 너무 크다. 서로 독립적인
하위 시스템이므로 각각 별도의 spec → plan → 구현 사이클로 진행한다.

| # | 하위 프로젝트 | 핵심 산출물 |
|---|---|---|
| **0** | **운영 기반 (이 문서)** | prod/staging 분리, `docs/ops/` 구조, 자율성 정책, Telegram 배선, 오케스트레이터 골격 |
| 1 | 운영팀 (SRE) | 배포·헬스체크·백업검증·장애대응 에이전트 + 러닝북 |
| 2 | 개발팀 | staging 대상 기능개발·버그픽스·PR리뷰 파이프라인 |
| 3 | 콘텐츠팀 | 프로기보 수집·데일리공유·SEO 페이지 생성 |
| 4 | 지원·분석팀 | 문의 응대·사용통계 리포트·피드백 분류 |

**0번은 나머지 전부의 토대**다. 1~4번은 0번 완료 후 각자 brainstorm·spec을 거친다.

## 오케스트레이션 접근 — C (하이브리드)

검토한 3가지 접근.

- **A. Claude Code 네이티브** — `/schedule` + `.claude/agents/` + `/loop`. 새 인프라 0.
  약점: 작업 상태가 대화 메모리에 의존.
- **B. GitHub Actions** — CI가 cron·이슈로 에이전트 실행. CI가 집의 맥 미니에
  닿을 수 없어 배포·모니터링이 불가능. **부적합.**
- **C. 하이브리드 (채택)** — A를 쓰되 작업을 **파일로 고정**한다.
  `docs/ops/runbooks/`(선언적 작업 정의)와 `docs/ops/state/`(완료·대기·장애)를 두고,
  launchd가 깨운 오케스트레이터 세션이 러닝북을 읽어 도메인 서브에이전트로 분배.

채택 근거: 맥 미니가 라이브 호스트이자 Claude Code 실행 머신이라 배포·모니터링이
로컬 Bash로 끝난다(B의 네트워크 장벽 소멸). 러닝북·상태 파일이 A의 약점
(세션 간 망각)을 보완한다.

## 설계

### 섹션 1 — 환경 분리 (prod/staging)

맥 미니 한 대에서 두 개의 docker-compose 프로젝트를 띄운다.

| | prod (라이브) | staging (에이전트 작업장) |
|---|---|---|
| 포트 | web 3000 / backend 8000 | web 3100 / backend 8100 |
| 프로젝트명 | `inkbaduk-prod` | `inkbaduk-staging` |
| DB | `baduk.db` (실데이터) | `baduk-staging.db` (시드 또는 prod 스냅샷) |
| KataGo | 실제 모델 | `KATAGO_MOCK=true` 기본 — 맥 미니 CPU 보호 |
| 코드 출처 | `main` 브랜치 | git worktree (에이전트 작업 브랜치) |

**흐름**: 에이전트는 worktree에서 개발 → staging 배포·검증 → 통과 시 `main` 머지 +
prod 재빌드(승급). prod DB는 에이전트가 직접 건드리지 않고, staging은 주기적으로
prod 스냅샷을 복사해 받는다.

**리소스**: 두 스택 동시 기동 부담을 줄이기 위해 staging backend는 기본
`KATAGO_MOCK=true`. KataGo 자체를 검증할 때만 실모델을 띄운다.

**산출물**: `docker-compose.staging.yml` 오버라이드, `.env.staging`,
`start.sh`/`stop.sh`에 `--env prod|staging` 인자 추가.

### 섹션 2 — `docs/ops/` 디렉터리 구조

작업을 대화 메모리가 아닌 파일로 고정하는 핵심 구조.

```
docs/ops/
  README.md              운영 체계 개요 (사람용 진입점)
  autonomy-policy.md     자율성 정책 (섹션 3)
  runbooks/
    healthcheck.md       헬스체크 절차
    deploy.md            staging→prod 승급 절차
    telegram-protocol.md 알림·승인 메시지 규약 (섹션 4)
    (그 외 러닝북은 하위 1~4에서 추가)
  state/
    dashboard.md         현재 상태 한눈에
    pending-approvals.md 승인 대기 큐
    incidents.md         장애 이력
    log/2026-05-22.md    날짜별 운영 로그 (감사 추적)
```

에이전트 정의는 Claude Code가 읽는 `.claude/agents/`에 두고, `docs/ops/`는
러닝북·상태·로그 전용으로 한다.

### 섹션 3 — 자율성 정책 (거버넌스)

`docs/ops/autonomy-policy.md`에 액션을 3등급으로 고정한다.

| 등급 | 의미 | 해당 액션 (예시) |
|---|---|---|
| 🟢 자율 | 실행 후 사후 로깅 | 헬스체크, 사용통계 리포트, **staging** 배포·검증, 콘텐츠·SEO 페이지 **초안**, 백업 검증 |
| 🟡 승인 | Telegram 제안 → 승인 후 실행 | **prod 승급/배포**, 콘텐츠·페이지 **라이브 게시**, `main` 머지, DB 마이그레이션, 의존성 버전업 |
| 🔴 금지 | 에이전트 절대 불가 (사람 전용) | prod 데이터 삭제, 시크릿/JWT 로테이션, 유료 인프라 결제, 사용자 PII 개별 열람 |

원칙 — 읽기·staging·초안은 자율, 라이브를 바꾸는 모든 것은 승인, 비가역적인 것은
금지. 하위 1~4의 에이전트는 각자 작업을 이 표에 매핑한 채로 만든다.

### 섹션 4 — Telegram 승인·알림 배선

Telegram 플러그인을 승인·알림 채널로 쓴다. Telegram Bot API는 **히스토리 조회가
불가능**하므로(도착하는 메시지만 봄) 제안 시점과 승인 시점을 파일로 분리한다.

**알림 (단방향)** — 오케스트레이터·에이전트가 상태 요약·장애 경보·일일 리포트를
Telegram으로 푸시. 응답 불필요.

**승인 (양방향)** — 🟡 액션을 만나면.

1. 에이전트가 `pending-approvals.md`에 항목 기록 — 고유 ID, 액션 요약, 근거, 영향 범위.
2. 같은 내용을 ID 포함해 Telegram 전송.
3. 사용자가 폰에서 `승인 <ID>` 또는 `반려 <ID>`로 답신.
4. 답신 도착 시 Claude Code 세션이 깨어나 `pending-approvals.md`에서 ID를 찾아
   실행 → `log/`에 기록 → 큐에서 제거.

`pending-approvals.md`가 단일 진실 공급원이라 제안 세션과 승인 처리 세션이 달라도
안전하게 이어진다. 승인 없이 시간이 지난 항목은 다음 오케스트레이터 실행 때
"보류 N건"으로 다시 알린다.

**산출물**: `runbooks/telegram-protocol.md` — 알림·승인 헬퍼와 메시지 포맷 규약.

### 섹션 5 — 운영 오케스트레이터 골격

스케줄러가 깨우는 Claude Code "운영 오케스트레이터" 세션이 러닝북을 읽고 도메인
서브에이전트로 분배한다.

**스케줄러** — macOS `launchd` plist. 맥 미니 상주, 재부팅에도 생존. 맥에서
cron보다 신뢰성이 높다.

**기동 케이던스**

| 시점 | 하는 일 |
|---|---|
| 매시 정각 | `healthcheck.md` 실행 → 이상 시에만 Telegram 경보 |
| 매일 09:00 | 일일 점검 — 백업검증 + 사용통계 + 보류 승인 리마인드 + 일일 요약 푸시 |
| Telegram 답신 도착 | `pending-approvals.md` 처리 (섹션 4) |

**오케스트레이터 1회 실행 루프** — ① `runbooks/`에서 due한 러닝북 선별 →
② `Agent` 도구로 도메인 서브에이전트 호출 → ③ 결과 수집 → ④ `state/` 갱신
(dashboard·log) → ⑤ Telegram 요약 푸시.

**0번이 만드는 범위** — 오케스트레이터 프롬프트 + launchd plist + `healthcheck.md`
러닝북 **1개**. "스케줄에 깨어나 → 러닝북 실행 → 상태 기록 → Telegram 보고"의
한 바퀴가 실제로 도는 것을 증명한다. 도메인 에이전트와 나머지 러닝북은 하위 1~4에서.

### 섹션 6 — 범위 경계

**0번 포함** — 환경 분리(1), `docs/ops/` 뼈대(2), 자율성 정책 문서(3),
Telegram 배선(4), 오케스트레이터 골격 + healthcheck 러닝북(5).

**0번 제외** — 실제 도메인 에이전트(개발·SRE·콘텐츠·지원), SEO 페이지 생성 로직,
콘텐츠 파이프라인. 모두 하위 1~4의 각자 spec.

## 검증 기준

이 4가지가 실제 명령 실행으로 통과하면 0번 완료. 문서만으로 "완료" 선언 금지.

1. staging 스택이 prod와 독립 포트로 **동시 기동**되고 서로 간섭이 없다.
2. `healthcheck.md` 러닝북이 prod·staging 양쪽 상태를 정확히 보고한다.
3. Telegram 알림이 도착하고, 승인 큐 왕복(제안→답신→실행→로그)이 더미 항목으로
   동작한다.
4. launchd가 스케줄에 오케스트레이터를 깨우고 `log/`에 실행 기록이 남는다.

## 리스크와 완화

| 리스크 | 완화 |
|---|---|
| 에이전트 실수가 라이브 장애로 직결 | prod/staging 분리, 라이브 변경은 전부 🟡 승인 |
| 맥 미니 리소스 부족(두 스택 + KataGo) | staging은 `KATAGO_MOCK=true` 기본 |
| 세션 간 작업 상태 망각 | `docs/ops/state/`·`runbooks/` 파일이 단일 진실 공급원 |
| Telegram 히스토리 부재로 승인 유실 | `pending-approvals.md`로 제안/승인 시점 분리, 미처리분 재알림 |
| 맥 미니 재부팅 시 스케줄 중단 | launchd plist(부팅 시 자동 로드) |

## 다음 단계

이 spec 승인 후 `writing-plans` 스킬로 0번의 구현 계획을 작성한다. 하위 1~4는
0번 완료 후 각자 brainstorm → spec → plan 사이클을 거친다.
