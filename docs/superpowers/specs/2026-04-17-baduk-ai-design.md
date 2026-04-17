# AI 바둑 프로그램 설계서

- **작성일**: 2026-04-17
- **프로젝트 경로**: `/Users/daegong/projects/baduk/`
- **상태**: 초안 (사용자 검토 대기)

---

## 1. 개요

브라우저에서 접속해 AI와 바둑을 둘 수 있는 웹 애플리케이션. 사용자는 대국 시작 전에 AI의 급수(18급 ~ 7단)를 선택하거나, 접바둑(2 ~ 9점)을 설정할 수 있다. 실제 강도의 AI를 얻기 위해 **KataGo**(오픈소스 바둑 엔진, Human-SL 모델)를 백엔드에서 실행하고, 표준 GTP(Go Text Protocol)로 통신한다.

### 1.1 목표 사용자 규모

지인 수십명 수준의 소규모(A규모) 운영. 단일 VPS + Docker Compose.

### 1.2 핵심 기능 (MVP)

- 급수·접바둑 선택 후 AI 대국
- 착수·패스·기권, 자동 규칙 검증(착수 금지, 패, 이적)
- 집 계산(한국룰) 및 승부 판정
- SGF 기보 저장·불러오기
- 무르기(Undo)
- AI 힌트(추천수)
- 수순 리플레이 및 분석 모드(승률·히트맵)
- 사용자 계정(이메일 + 비밀번호)
- 대국 전적 기록
- 다국어(한국어/영어) + 라이트/다크 테마

### 1.3 비목표 (V1에서 제외)

- 모바일 네이티브 앱
- 9x9/13x13 바둑판
- 시간 제한(초읽기, 피셔)
- 사용자 간 대국(온라인 대국)
- 소셜 로그인(OAuth)

---

## 2. 아키텍처

### 2.1 최상위 구성

```
[Next.js 브라우저 앱]
   │  HTTPS REST + WebSocket
   ▼
[FastAPI 백엔드]
   ├── Auth / Game / Analysis / WS 라우터
   ├── Go Rules Engine (순수 로직)
   ├── KataGo Adapter (asyncio.subprocess)
   └── SQLAlchemy + SQLite
   │   stdin/stdout (GTP)
   ▼
[KataGo 프로세스 + Human-SL 모델]
```

### 2.2 컨테이너 구성 (docker-compose)

| 서비스 | 이미지 | 포트 | 비고 |
|---|---|---|---|
| `web` | Node 20 (Next.js 빌드) | 3000 | 프론트엔드 |
| `backend` | Python 3.11 + KataGo 바이너리 | 8000 | FastAPI + KataGo 서브프로세스 |

- SQLite 파일은 `backend` 볼륨 `./data/baduk.db` 에 마운트
- KataGo 모델 파일은 빌드 타임에 다운로드(`b18c384nbt-humanv0.bin.gz`), `./katago/models/` 볼륨
- Nginx 리버스 프록시는 V1 생략(단일 노드). 운영 시 Caddy 또는 Cloudflare Tunnel 권장

### 2.3 분리 원칙

- **프론트엔드는 UI만**: 바둑판 렌더링, 상호작용, SGF 파싱. 규칙 판단 없음.
- **Go Rules Engine**: 순수 함수. KataGo와 완전 독립. 100% 테스트 커버리지 목표.
- **KataGo Adapter**: GTP 프로토콜 어댑터. AI 엔진 교체 시 한 곳만 수정.
- **Game Service**: Rules Engine + KataGo Adapter를 조합해 "한 판의 생명주기"를 담당.

---

## 3. 기술 스택

| 영역 | 기술 |
|---|---|
| 프론트엔드 | Next.js 14 (App Router, TypeScript), Zustand(상태), SWR(캐시), Tailwind CSS |
| 바둑판 렌더링 | SVG (React 컴포넌트, 19x19 성능 충분) |
| 백엔드 | FastAPI (Python 3.11), Uvicorn, Pydantic v2, SQLAlchemy 2.x |
| DB | SQLite (WAL 모드), Alembic 마이그레이션 |
| 인증 | JWT (HS256) + HttpOnly 쿠키, bcrypt |
| AI 엔진 | KataGo + `b18c384nbt-humanv0` Human-SL 모델 |
| 실시간 통신 | FastAPI WebSocket |
| 배포 | Docker Compose |
| 테스트 | pytest, httpx, Vitest, Playwright |
| 린트·포맷 | ruff, mypy, eslint, prettier |

---

## 4. 프로젝트 구조

```
baduk/
├── docker-compose.yml
├── README.md
├── docs/superpowers/
│   ├── specs/
│   │   └── 2026-04-17-baduk-ai-design.md   ← 이 문서
│   └── plans/                              ← writing-plans로 생성
├── web/                                    ← Next.js
│   ├── app/
│   │   ├── (auth)/{login,signup}
│   │   ├── (game)/{new,play/[id],review/[id]}
│   │   ├── history/
│   │   └── settings/
│   ├── components/{Board,StonePalette,GameControls,ScorePanel,AnalysisOverlay}
│   ├── lib/{api,ws,sgf,i18n}
│   ├── store/
│   ├── tests/
│   └── package.json
└── backend/                                ← FastAPI + KataGo
    ├── app/
    │   ├── main.py
    │   ├── api/{auth,games,analysis,ws}.py
    │   ├── core/
    │   │   ├── rules/{board,captures,ko,scoring,handicap}.py
    │   │   ├── katago/{adapter,strength,analysis}.py
    │   │   └── sgf/writer.py
    │   ├── services/{game_service,user_service}.py
    │   ├── models/{user,game,move}.py
    │   ├── db.py
    │   └── config.py
    ├── migrations/                         ← Alembic
    ├── tests/
    ├── katago/                             ← 바이너리·모델
    ├── data/                               ← SQLite 파일 (볼륨)
    └── Dockerfile
```

---

## 5. 데이터 흐름

### 5.1 새 대국 생성 + 첫 수

1. 사용자가 `/game/new` 에서 급수·접바둑 선택 → `POST /api/games {ai_rank, handicap, user_color}`
2. 백엔드: DB에 `games` 레코드 생성, 접바둑이면 치석 좌표 생성(§7.2), KataGo에 `clear_board` + `komi` + `humanSLProfile` 설정, 치석 순차 `play B`
3. 응답으로 `{gameId, state}` 반환, 프론트는 `/game/play/{gameId}` 로 이동하며 WebSocket 연결
4. 사용자 클릭 → WS 메시지 `{type:"move", coord:"Q16"}` → Rules Engine 검증 → DB 기록 → KataGo `play` → `genmove` 호출 → AI 수 반환 → DB 기록 → WS로 푸시

### 5.2 무르기

1. 프론트 `{type:"undo", steps:2}` → 최근 2수를 `is_undone=true` 처리, KataGo에 `undo undo` 전송
2. 보드 상태 재계산 후 WS로 푸시

### 5.3 힌트

1. `POST /api/games/{id}/hint` → KataGo `kata-analyze 1 50` → 상위 3수 + 승률 반환(JSON)

### 5.4 종국 + 집 계산

1. 양쪽 연속 패스 감지 → Rules Engine의 한국룰 집 계산 실행
2. KataGo `final_score`로 교차 검증
3. 불일치 시 사용자에게 "사석(죽은 돌) 지정" UI 제공 → 재계산
4. `games.status="finished"`, `result`, `sgf_cache` 저장

### 5.5 분석 모드

1. 리뷰 화면에서 수 선택 → `POST /api/games/{id}/analyze?moveNum=N`
2. 캐시(`analyses` 테이블) 히트 시 즉시 반환
3. 미스 시 KataGo에 SGF 로드 + `kata-analyze 100` → 승률·ownership·상위수 파싱 → 캐시 저장

### 5.6 통신 프로토콜 매트릭스

| 용도 | 프로토콜 | 이유 |
|---|---|---|
| 인증, 대국 생성, 기보·전적 조회, 힌트, 분석 | REST(JSON) | 요청·응답 단순 |
| 대국 중 착수·AI 응수·무르기 | WebSocket | 저지연 양방향 |

---

## 6. 급수 시스템 (KataGo 강도 조절)

### 6.1 전략

일반 KataGo 모델은 초인급이라 "일부러 약하게" 두기가 부자연스럽다. 따라서 **Human-SL 모델**(`b18c384nbt-humanv0`)을 사용해 실제 인간 급수를 모사한다.

### 6.2 급수-프로필 매핑

| UI 표시 | `humanSLProfile` | `maxVisits` |
|---|---|---|
| 18급 | `rank_18k` | 1 |
| 15급 | `rank_15k` | 1 |
| 12급 | `rank_12k` | 1 |
| 10급 | `rank_10k` | 2 |
| 7급 | `rank_7k` | 4 |
| 5급 | `rank_5k` | 8 |
| 3급 | `rank_3k` | 16 |
| 1급 | `rank_1k` | 32 |
| 1단 | `rank_1d` | 64 |
| 3단 | `rank_3d` | 128 |
| 5단 | `rank_5d` | 256 |
| 7단 | `rank_7d` | 512 |

- UI는 위 12개 프리셋만 노출(선택 친화적)
- 매핑 테이블은 `backend/app/core/katago/strength.py` 에 상수로 정의, 튜닝 용이
- 베타 테스트 중 체감 강도 보정 필요 시 이 테이블만 수정

### 6.3 급수 체감 보정

사용자 승률이 10판 기준 70% 이상 또는 30% 이하일 때 "AI 급수를 재설정해보세요" UI 힌트 노출. 내부 ELO 추적은 V2.

---

## 7. 규칙·접바둑

### 7.1 일반 대국

- 룰셋: **한국룰** (영토 집계 / territory scoring, 덤 6.5)
- 연속 패스 또는 기권으로 종국
- 자살수는 이적이 동반되지 않으면 금지
- 단패만 자동 금지(장생·삼패는 계가 UI에서 사용자에게 처리 맡김)

### 7.2 접바둑 치석 좌표 (19x19 기준)

| 치석 수 | 좌표 |
|---|---|
| 2점 | D16, Q4 |
| 3점 | D16, Q4, Q16 |
| 4점 | D4, D16, Q4, Q16 |
| 5점 | D4, D16, Q4, Q16, K10 |
| 6점 | D4, D16, Q4, Q16, D10, Q10 |
| 7점 | D4, D16, Q4, Q16, D10, Q10, K10 |
| 8점 | D4, D16, Q4, Q16, D10, Q10, K4, K16 |
| 9점 | D4, D16, Q4, Q16, D10, Q10, K4, K10, K16 |

- 접바둑 시 덤 **0.5** (한국식 표준)
- 첫 수는 **백(AI)** 부터
- AI 강도는 약한 쪽(흑, 사용자) 급수로 설정

---

## 8. 데이터 모델

### 8.1 테이블

```sql
users(
  id INTEGER PK,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL,
  preferred_rank TEXT,
  locale TEXT DEFAULT 'ko',
  theme TEXT DEFAULT 'light',
  created_at TIMESTAMP,
  last_login_at TIMESTAMP
)

games(
  id INTEGER PK,
  user_id INTEGER FK→users,
  ai_rank TEXT NOT NULL,
  handicap INTEGER NOT NULL,
  komi REAL NOT NULL,
  user_color TEXT NOT NULL,                 -- 'black'|'white'
  status TEXT NOT NULL,                     -- 'active'|'finished'|'resigned'|'abandoned'|'suspended'
  result TEXT,                              -- SGF 결과 (예: 'B+R', 'W+12.5')
  winner TEXT,                              -- 'user'|'ai'|null
  move_count INTEGER DEFAULT 0,
  started_at TIMESTAMP,
  finished_at TIMESTAMP,
  sgf_cache TEXT
)

moves(
  id INTEGER PK,
  game_id INTEGER FK→games,
  move_number INTEGER NOT NULL,
  color TEXT NOT NULL,                      -- 'B'|'W'
  coord TEXT,                               -- 'Q16'|'pass'|null(기권)
  captures INTEGER DEFAULT 0,
  is_undone BOOLEAN DEFAULT FALSE,
  played_at TIMESTAMP,
  UNIQUE(game_id, move_number)
)

analyses(
  id INTEGER PK,
  game_id INTEGER FK→games,
  move_number INTEGER NOT NULL,
  payload TEXT NOT NULL,                    -- JSON: winrate, ownership[], topMoves[]
  created_at TIMESTAMP,
  UNIQUE(game_id, move_number)
)
```

### 8.2 설계 포인트

- 무르기된 수도 **삭제하지 않고** 논리 플래그로 표시 (기보 감사성 유지)
- 현재 보드 상태는 저장하지 않고, `moves`를 재생(replay)해서 복원. 메모리 캐시가 FastAPI에 존재
- `sgf_cache`는 종국 시점에만 생성·저장
- 인덱스: `games(user_id, status)`, `moves(game_id, move_number)`, `analyses(game_id, move_number)`

---

## 9. API 정의 (주요 엔드포인트)

### 인증
- `POST /api/auth/signup {email, password, display_name}` → 201
- `POST /api/auth/login {email, password}` → 200 (쿠키 설정)
- `POST /api/auth/logout` → 204
- `GET  /api/auth/me` → 현재 사용자

### 대국
- `POST /api/games {ai_rank, handicap, user_color}` → 201 `{gameId}`
- `GET  /api/games?status=&page=` → 목록
- `GET  /api/games/{id}` → 상세
- `DELETE /api/games/{id}` → 본인 대국만
- `POST /api/games/{id}/resign` → 기권
- `POST /api/games/{id}/hint` → 추천수 3개
- `POST /api/games/{id}/analyze?moveNum=N` → 분석 결과
- `GET  /api/games/{id}/sgf` → SGF 다운로드
- `POST /api/games/import-sgf` (multipart) → 기보 업로드 후 리뷰

### 실시간
- `WS /api/ws/games/{id}` — 메시지 타입: `move`, `pass`, `undo`, `state`, `ai_move`, `game_over`, `error`

### 전적·기타
- `GET  /api/stats` → 승·패 집계 (ai_rank, handicap별)
- `GET  /api/health` → DB·KataGo 상태

### 에러 응답 형식

```json
{
  "error": {
    "code": "ILLEGAL_KO",
    "message_key": "errors.illegal_ko",
    "detail": {"coord":"Q16"}
  }
}
```

프론트는 `message_key`를 i18n 번역.

---

## 10. 에러 처리 & 안정성

### 10.1 KataGo 장애

- 감지: stdin/stdout 단절, exit code ≠ 0, 응답 타임아웃 60초, 10분 간격 `version` 헬스체크
- 복구: 프로세스 재기동 → 활성 대국마다 `clear_board` → `komi` → 저장된 moves 순서 재생 → UI에 "AI 재접속 중" 토스트
- 누적 정책: 1시간 내 3회 크래시 → 활성 대국 `suspended`, 로그 알림

### 10.2 규칙 위반

- 에러 코드: `ILLEGAL_KO`, `ILLEGAL_SUICIDE`, `OCCUPIED`, `OUT_OF_BOUNDS`, `NOT_YOUR_TURN`
- Rules Engine이 1차 검증, 프론트는 에러 코드를 i18n 번역하여 표시

### 10.3 동시성

- 대국당 단일 WS 세션 정책 (새 연결 시 기존 연결 종료, 이전 탭에 알림)
- `game_id` 단위 asyncio lock으로 수 직렬화
- KataGo 호출은 전역 큐로 직렬화

### 10.4 네트워크 단절

- WS 끊기면 대국은 `active` 유지(24시간), 재접속 시 `moves` 재생으로 복원
- 24시간 미복귀 → `abandoned`, 전적 미반영

### 10.5 인증·보안

- JWT: 액세스 24h + 리프레시 30d, HttpOnly SameSite=Lax 쿠키
- bcrypt cost=12
- Rate limit: 로그인 5회/분/IP, 착수 30회/분/사용자
- 운영 도메인만 CORS 허용
- 환경변수: `JWT_SECRET`, `DB_PATH`, `KATAGO_BIN_PATH`, `KATAGO_MODEL_PATH`, `KATAGO_CONFIG_PATH`
- SQLAlchemy ORM 전용, raw SQL 금지

### 10.6 데이터 무결성

- 착수 저장: `moves` insert + `games.move_count` 증가 단일 트랜잭션
- 종국 처리: 상태·결과·SGF 단일 트랜잭션
- SQLite WAL 모드 활성화

### 10.7 관찰 가능성

- `structlog` JSON 로그 (요청·응답 요약, KataGo 명령·응답 요약)
- `/api/health`: DB 연결, KataGo 프로세스 상태, 최근 genmove 지연

### 10.8 백업

- 매일 자정 `baduk.db` → `backups/baduk-YYYY-MM-DD.db` (30일 보관)
- Docker Compose의 크론 전용 컨테이너

---

## 11. 테스트 & 품질 검증

### 11.1 테스트 계층

```
                  [수동 대국 QA]
              [E2E (Playwright)]
        [API 통합 (pytest + httpx)]
  [단위 테스트 (pytest / vitest)]
```

### 11.2 Rules Engine 단위 테스트 (100% 커버리지 목표)

- 합법수 판정: 빈 점, 착수 금지점, 자살수(이적 동반 시 합법 예외), 패 반복
- 이적 계산: 1점/다수/연쇄/자살수-이적 충돌
- 패(Ko): 단패·장생·삼패·순환
- 집 계산(한국룰): 완국, 중립점, 사석 수동 표시, 세키
- 접바둑 배치: 2~9점 각각
- **골든 테스트**: 저명 기보 20판 → 종국 결과 공식 결과와 일치

### 11.3 KataGo Adapter 통합 테스트

- GTP 파싱: 정상·에러·다행 응답·interrupt
- 프로세스: 시작·강제종료 후 재기동·상태 복원
- 요청 큐: 동시 5개 → 순차 처리, 타임아웃 처리
- 급수 매핑: 12개 프리셋 모두 설정 정확성

### 11.4 API 통합 테스트

- pytest + httpx + in-memory SQLite + KataGo Mock(결정적 응답)
- 인증, JWT 만료, 대국 CRUD, 착수·무르기·힌트·분석·종국, 권한, Rate limit, WebSocket

### 11.5 프론트엔드 테스트

- 컴포넌트(Vitest + React Testing Library): Board, 착수 상호작용, ScorePanel, SGF 파서
- 스토어(Zustand) 전이
- i18n 키 완전성 CI 체크

### 11.6 E2E (Playwright) — 핵심 5개 시나리오

1. 회원가입 → 5급 호선 → 3수 → 힌트 → 무르기 → 기권 → 전적
2. 4점 접바둑 1급 AI → 100수 → 패스 종국 → 집 계산 → SGF 다운로드
3. 리뷰·분석 모드: 기보 열기 → 분석 → 히트맵
4. 다크모드 + ko↔en 언어 전환
5. 두 탭 동시 접속 → 단일 세션 정책 동작

### 11.7 성능·부하

- KataGo 지연: 급수별 p95 목표 1급 기준 < 3초
- 동시 3판 시 큐 지연 측정
- SQLite 쓰기: 착수 엔드포인트 p95 < 50ms

### 11.8 보안 검증

- `bandit` (Python), `eslint-plugin-security` (JS)
- `pip-audit`, `npm audit` — CI 통합
- `security-review` 스킬로 배포 전 수동 검증
- 체크리스트: JWT 검증, CORS, SQLi, XSS, CSRF(SameSite), Rate limit

### 11.9 병렬 에이전트 교차 리뷰

구현 완료 후, 다음 5개 리뷰 에이전트를 **병렬로** 실행:

| 에이전트 | 역할 |
|---|---|
| Rules-Reviewer | Rules Engine 골든 테스트 재검증, 엣지 케이스 탐색 |
| KataGo-Reviewer | GTP 어댑터·급수 매핑·프로세스 관리 |
| API-Reviewer | FastAPI 엔드포인트 정합성, 권한, 에러 응답 |
| Frontend-Reviewer | 접근성, 반응형, i18n 완전성, 상태 관리 |
| Security-Reviewer | 인증·세션·입력 검증·의존성 취약점 |

각 에이전트 결과를 합쳐 최종 **품질 보고서**를 `docs/QUALITY_REPORT.md` 에 기록하고 산출물에 포함.

### 11.10 CI 품질 게이트 (merge 전 필수 통과)

- 린터 통과: ruff, eslint, prettier
- 타입 체크: mypy, tsc
- 백엔드 단위 + 통합 테스트 100% 통과
- 프론트 단위 테스트 100% 통과
- 커버리지: Rules Engine 100%, 그 외 ≥ 80%
- E2E 핵심 5개 통과
- 보안 스캔 심각도 high 이상 0건

### 11.11 릴리스 전 수동 QA 체크리스트

1. 18급 / 5급 / 1단 / 7단 각 1판씩 대국 — 급수 체감 검증
2. 4점 접바둑 상·하수 양쪽
3. 기권 및 연속 패스 종국 양쪽
4. 크롬·사파리·파이어폭스 + 모바일 뷰포트
5. 로그인 30일 유지

---

## 12. 구현 단계 및 역할 분담 (에이전트별)

사용자 요구사항("각 에이전트별로 역할 분담")에 따라 구현은 아래와 같이 병렬·순차 조합한다. 세부 구현 계획은 writing-plans 스킬이 별도 문서(`docs/superpowers/plans/`)로 산출한다.

### 12.1 기초 단계 (순차)

1. **Infra-Agent**: Docker Compose, 저장소 구조, CI 스캐폴딩
2. **DB-Agent**: SQLAlchemy 모델 + Alembic 마이그레이션 + 테스트
3. **Rules-Agent**: Rules Engine + 100% 단위 테스트 + 골든 테스트

### 12.2 병렬 구현 단계

- **KataGo-Agent**: KataGo Adapter, 급수 매핑, 프로세스 관리, mock
- **Backend-Agent**: FastAPI 라우터, 인증, Game Service, WebSocket
- **Frontend-Agent**: Next.js, Board 컴포넌트, 대국 UI, i18n, 테마
- **SGF-Agent**: SGF 파서·작성기(프론트·백엔드 양쪽)

### 12.3 통합·검증 단계

- **Integration-Agent**: E2E 시나리오(Playwright), 성능 테스트
- **5개 Review-Agent 병렬 실행** (§11.9) → `docs/QUALITY_REPORT.md` 생성
- **Release-Agent**: README, 배포 스크립트, 백업 크론

---

## 13. 산출물 (최종 납품물)

1. 실행 가능한 `docker-compose up` 한 번으로 기동되는 전체 스택
2. 소스 코드 (web/, backend/)
3. KataGo 모델 다운로드 스크립트
4. 마이그레이션 및 시드 데이터
5. 테스트 스위트 (단위·통합·E2E) + CI 파이프라인
6. 사용자 매뉴얼(`README.md`) — 설치·실행·백업·트러블슈팅
7. 품질 보고서(`docs/QUALITY_REPORT.md`) — 5개 리뷰 에이전트 결과 병합
8. 설계서(본 문서) 및 구현 계획서(writing-plans 산출)

---

## 14. 열린 이슈 / V2 후보

- 모바일 앱(React Native 또는 PWA 강화)
- 9x9/13x13 바둑판 지원
- 시간 제한(초읽기, 피셔)
- 사용자 간 온라인 대국
- 소셜 로그인(OAuth)
- 관리자 콘솔 UI
- 자동 ELO 기반 급수 재설정
- Prometheus/Grafana 관측 스택
