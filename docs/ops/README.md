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
