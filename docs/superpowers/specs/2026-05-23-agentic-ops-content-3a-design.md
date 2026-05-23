# Agentic Ops — 하위 프로젝트 3a: 콘텐츠 수집 + SEO 인덱스 정비

- 작성일: 2026-05-23
- 상태: 설계 승인 완료, 구현 계획 대기
- 의존: 하위 프로젝트 0 (운영 기반), 1 (SRE), 2 (개발팀)
- 범위: inkbaduk 콘텐츠 운영의 **수집·검색 노출** 계층

## 배경

하위 프로젝트 3(콘텐츠팀)을 단일 spec으로 담기엔 큐레이션·LLM 콘텐츠가 섞여 너무
크다. 결정적·기계적 영역(자동 수집, 인덱스 정비)만 먼저 3a로 떼어내 자율 운영
패턴(sub-project 0~2)에 맞춘다. 큐레이션(테마·주·월간 페이지)은 3b, FAQ·용어
LLM 콘텐츠는 3c로 분리한다.

### 현재 상태 (조사 확정)

- prod DB의 `pro_games` 테이블에 **911개 게임**이 적재됨.
- `backend/scripts/seed_pro_games.py`는 `data/pro_games/masterpieces/*.sgf`를 멱등 적재 —
  **수동·로컬 디렉터리 기반**. 외부 소스 자동 fetch 없음.
- `web/app/sitemap.ts`는 **정적 5 URL**만 포함 (`/`, `/support`, `/supporters`,
  `/privacy`, `/terms`) — **911개 프로 기보 페이지가 sitemap에서 누락**. 검색 노출 0.
- `web/app/spectate/pro/[id]/page.tsx`에 `generateMetadata` 없음 — 모든 프로 기보
  페이지가 동일한 사이트 기본 메타로 크롤러에 보임.

### 결정된 설계 축

- **수집 소스**: CWI 퍼블릭 도메인 컬렉션(`homepages.cwi.nl/~aeb/go/games/`)만 허용
  ([[pro-game-sgf-source]] 메모리 — 상용 사이트 스크래핑 금지).
- **수집 주기**: 주 1회 (CWI 아카이브가 자주 갱신되지 않음).
- **SEO 정비**: 동적 sitemap + 동적 메타 — Next.js 런타임 생성. ingest 후 다음
  요청에 즉시 반영(최대 1시간 캐시).

## 접근

cron 자동화 + Next.js 동적 라우트로 두 영역을 일관되게 자동화.

- A. 전부 cron 자동화 (**채택**) — weekly CWI ingest + 런타임 동적 sitemap·meta.
  신규 ingest가 다음 요청에 즉시 반영.
- B. CWI는 cron, sitemap·meta는 빌드타임 정적 — 다음 prod 빌드 전까진 신규 게임이
  sitemap에 안 들어옴. Stale.
- C. CWI 온디맨드 — 자율성 줄지만 cron 항목 줄임. "주 1회 자동"이 사용자 결정이라 부적합.

## 설계

### 섹션 1 — CWI 자동 수집 스크립트

**`backend/scripts/ingest_cwi_weekly.py`** — 결정적 Python, LLM 불개입.

- HTTP로 CWI 인덱스 페이지 가져옴 → ETag/Last-Modified 캐시(`~/.baduk/ingest-cwi.cache`)와
  비교 → 변경 없으면 0건으로 종료.
- 변경 시 SGF 후보 파일 목록 추출 → 각 SGF 다운로드.
- 각 SGF를 `app.core.sgf.import_sgf.parse_pro_sgf`로 파싱(기존 `seed_pro_games.py`와
  동일 경로) → `content_hash` 계산.
- 기존 `pro_games`에 같은 `content_hash`가 있으면 스킵 → 신규만
  `collection='cwi'` 라벨로 insert.
- 결과 카운트(검사·신규·중복·실패)를 `docs/ops/state/log/YYYY-MM-DD.md`에 추가.
- **라이선스 가드** — 스크립트 상단의 도메인 화이트리스트로 `homepages.cwi.nl` 외
  fetch를 거부([[pro-game-sgf-source]] 강제).

### 섹션 2 — `com.inkbaduk.content-ingest` launchd

`ops/launchd/com.inkbaduk.content-ingest.plist` — `StartCalendarInterval`을 일요일 03:00로
설정(백업 04:00 / dev-cycle 02:00과 안 겹침). `ops/run-content-ingest.sh`가 prod
venv를 활성화해 `python -m scripts.ingest_cwi_weekly`를 실행한다. 로그는
`docs/ops/state/log/content-ingest.{out,err}.log`.

### 섹션 3 — 동적 sitemap.xml

`web/app/sitemap.ts`를 정적 5개에서 동적 생성으로 변경.

- 공개 페이지 5개 그대로 유지.
- backend `/api/spectate/pro` 목록을 fetch → 각 `pro_games.id`마다
  `/spectate/pro/{id}` URL 추가. `lastModified`는 게임 추가 시각, `priority` 0.6,
  `changeFrequency: monthly`.
- 빌드 시점이 아닌 **요청 시점** 렌더링 — `export const revalidate = 3600` (1시간 캐시).
  ingest 후 최대 1시간 내 검색엔진에 노출 가능.
- 빌드·런타임 오류 시 fallback: 정적 5개만(빈 pro list). 깨진 sitemap보다 낫다.

### 섹션 4 — 프로 기보 페이지 `generateMetadata`

`web/app/spectate/pro/[id]/page.tsx`에 `generateMetadata async` 함수 추가.

- pro game을 fetch → title: `{black} vs {white} ({event}, {date}) — inkbaduk`,
  description: 이벤트·날짜·결과 한 줄, `alternates.canonical`:
  `https://inkbaduk.com/spectate/pro/{id}`.
- OG: 일단 사이트 기본 이미지 + 페이지 title 텍스트. 커스텀 OG 이미지(보드 정적
  SVG)는 3b로 미룸.
- 404 처리 — pro game이 없으면 `notFound()`. 메타에 `robots: { index: false }`.

### 섹션 5 — 오케스트레이터 통합

`orchestrator-prompt.md`의 일일 요약(보고 단계)에 한 줄 추가 — "최근 CWI ingest 결과"를
`docs/ops/state/log/`에서 읽어 포함(0건이어도 보고). 새 러닝북은 만들지 않음 —
ingest는 결정적 스크립트라 별도 러닝북 불필요.

### 섹션 6 — 범위 경계

**포함** — CWI ingest 스크립트 + launchd + 래퍼, 동적 sitemap, 프로 기보 페이지
`generateMetadata`, 오케스트레이터 한 줄 통합.

**제외** — 커스텀 OG 이미지(3b), 테마·주·월간 페이지(3b), FAQ·용어 해설(3c),
daily-share 사용자 기능(별도 plan으로 이미 존재).

## 검증 기준

이 4가지가 실제 명령 실행으로 통과하면 하위 프로젝트 3a 완료. 문서만으로 완료 선언 금지.

1. `ingest_cwi_weekly.py`가 CWI에 접근하고 정상 종료한다(신규 0건이어도 OK).
   `com.inkbaduk.content-ingest` launchd 작업이 등록되고 수동 트리거 로그가 남는다.
2. `curl http://localhost:3000/sitemap.xml` 응답에 911개 이상의
   `/spectate/pro/<id>` URL이 포함된다.
3. `curl http://localhost:3000/spectate/pro/<유효 id>`의 응답 HTML에 고유 `<title>`,
   `<meta name="description">`, `<link rel="canonical">`이 들어 있다.
4. 오케스트레이터 일일 요약에 "최근 CWI ingest 결과" 한 줄이 포함된다.

## 리스크와 완화

| 리스크 | 완화 |
|---|---|
| 비허용 소스 fetch | 스크립트 상단 도메인 화이트리스트로 CWI 외 거부. 코드 리뷰가 가드 |
| ingest 실패가 sitemap을 깨뜨림 | sitemap.ts fallback — 동적 실패 시 정적 5개로 응답 |
| pro_games 수가 커져 sitemap 응답 느려짐 | `revalidate=3600` 캐시. 1만 건까지 일반적으로 무난 |
| Next.js dev 환경에서 dynamic route SSR 비용 | sitemap·메타는 prod 빌드 후 효력 — 배포 후에만 측정 |
| 메타 fetch 실패로 페이지 렌더 자체가 깨짐 | `generateMetadata`는 별도 함수 — 실패 시 catch 후 기본 메타로 폴백 |

## 다음 단계

이 spec 승인 후 `writing-plans` 스킬로 하위 프로젝트 3a의 구현 계획을 작성한다.
3b(테마·주·월간 페이지), 3c(FAQ·용어 해설), sub-project 4(지원·분석팀)는 각자
별도 brainstorm → spec → plan 사이클을 거친다.
