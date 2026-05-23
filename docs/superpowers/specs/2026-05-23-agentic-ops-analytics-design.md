# Agentic Ops — 하위 프로젝트 4: 분석·리포트 (지원·분석팀 축소판)

- 작성일: 2026-05-23
- 상태: 설계 승인 완료, 구현 계획 대기
- 의존: 하위 프로젝트 0~3c
- 범위: inkbaduk **주간 사용 통계 리포트 자동 생성·Telegram 푸시**. 지원·피드백 채널 구축은 별도 후속.

## 배경

원래 sub-project 4 ("지원·분석팀")의 의도는 문의 응대·사용 통계·피드백 분류 세
영역이다. 그러나 inkbaduk이 **익명 닉네임 세션**(PII 비수집)이라 실 사용자와의
1:1 응대 채널은 외부 인프라(이메일·SNS·공개 Telegram 채널) 결정이 선행돼야
가능하다. 반면 분석·리포트는 기존 `/api/stats`·`/api/admin/summary` + DB로
즉시 가치 창출이 가능하다.

이 4번은 **분석·리포트만**으로 좁힌다. 피드백·문의 채널은 채널 인프라 결정 후 별도 사이클.

### 현재 상태

- `backend/app/api/stats.py` — 공개 `/api/stats` endpoint.
- `backend/app/api/admin.py` — 인증 필요 `/api/admin/summary` 등 다수.
- prod DB(`backend/data/baduk.db`) 222 게임, sessions 테이블 다수.
- 자율성 정책의 "사용통계 리포트"는 이미 🟢 자율.

### 결정된 설계 축

- 데이터 소스: 공개 `/api/stats` + DB 직접 read(SQLite 읽기 전용).
- 주기: 주 1회 (일요일 09:00).
- 형식: 한국어 요약 마크다운, `docs/ops/state/reports/YYYY-WW.md` 누적.
- 전달: Telegram 푸시 + 오케스트레이터 일일 요약에 한 줄.

## 접근 — A (헤드리스 LLM 요약 + Telegram 푸시)

- A. **자율 사이클 — 헤드리스 LLM 요약 + Telegram (채택)** — 기존 sub-project 0/1/2/3c
  launchd 패턴 재사용. 새 endpoint·schema 없음.
- B. 백엔드 분석 endpoint 정형 JSON — 더 견고하나 schema 설계 비용 큼, 분석 안정화 전엔 과함.
- C. admin UI 대시보드 — 별도 작업, 본 범위 밖.

## 설계

### 섹션 1 — 데이터 소스 + 리포트 항목

데이터.
- `GET /api/stats`(공개) — 랭크 분포, 게임 결과 등.
- `backend/data/baduk.db` 읽기 전용 — `games`, `sessions`, `session_history` 테이블.
- 보조: `docs/ops/state/log/`(자체 운영 로그) — 보류 승인·incidents 카운트.

리포트 본문 (~500자, 한 페이지).
- 주간 게임 수·일별 추이.
- 평균 수순·평균 대국 시간.
- 랭크 분포·인기 핸디캡.
- 세션 추정(신규 vs 재방문 — 가능한 범위).
- sub-project 3a/3c 효과: 신규 글로서리·FAQ 게시, 픽 트래픽(가능 시).
- 보류 승인 N건, incidents N건.

### 섹션 2 — `analytics-weekly` launchd

`com.inkbaduk.analytics-weekly` — 매주 일요일 09:00 (헬스체크 12:00 전, 운영 한가한 시간).
`ops/run-analytics-weekly.sh` → 헤드리스 Claude (`--channels` Telegram +
`--dangerously-skip-permissions`) → `docs/ops/analytics-prompt.md` 지시문 실행.

### 섹션 3 — 리포트 보관 + Telegram 푸시

- `docs/ops/state/reports/YYYY-WW.md` — 주차별 별도 파일. 미래 추세 비교 자산.
- Telegram 푸시 — 본문 요약(짧게) + 보관 경로.
- 오케스트레이터 일일 요약(12·18시)에 "최근 분석 리포트 YYYY-WW" 한 줄 추가.

### 섹션 4 — 범위 경계

**포함** — analytics-weekly launchd + 래퍼 + 프롬프트, `docs/ops/state/reports/` 디렉터리,
오케스트레이터 한 줄 통합.

**제외** — admin endpoint 인증 자동화(헤드리스 세션이 cookie 없이 호출 불가),
피드백·문의 채널(별도 인프라 결정 후), admin UI 대시보드 시각화, 시계열 트렌드 그래프.

## 검증 기준

이 3가지가 실제 명령 실행으로 통과하면 하위 프로젝트 4 완료.

1. `com.inkbaduk.analytics-weekly` launchd 등록 + 수동 트리거 → 
   `docs/ops/state/reports/YYYY-WW.md` 신규 파일 생성. Telegram 메시지 발송(또는
   curl 폴백).
2. 생성된 리포트가 실제 DB 통계(게임 수·세션 수 등)를 정확히 반영. LLM이 환각 없이
   숫자를 보고. 사람이 한 번 스폿체크.
3. 오케스트레이터 일일 요약(`orchestrator-prompt.md`)에 "최근 분석" 한 줄 포함.

## 리스크와 완화

| 리스크 | 완화 |
|---|---|
| LLM이 통계 수치 환각 | 프롬프트가 명령 실행 결과를 그대로 인용하도록 강제. 자체 추정 금지 명시. 사람 스폿체크. |
| 매주 동일 형식의 노이즈 | 변화량 중심 보고 — 전주 대비 ±%만 표기. 변동 없는 항목은 생략. |
| 가짜·테스트 세션 통계 오염 | 명시적 필터 없음 — 현재 트래픽이 적어 노이즈 자체 적음. 후속에서 필터 추가 가능. |

## 다음 단계

이 spec 승인 후 `writing-plans`로 sub-project 4 구현 계획 작성. 피드백·문의 채널은
인프라(이메일·SNS·공개 채널) 결정 후 별도 spec.
