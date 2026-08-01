# 방문 통계 어드민 설계

- 작성일: 2026-07-24
- 상태: 확정 (구현 대기)
- 범위: inkbaduk.com 방문 트래픽 + 검색 유입 통계를 어드민에서 조회

## 배경·목표

공개 SEO 콘텐츠(글로서리·FAQ·프로 기보)로 유입이 늘면서, 운영자가 **어디서·어느 나라에서·어떤 페이지로** 방문하는지, **어떤 검색어로** 들어오는지를 어드민에서 보고 싶다. 기존 `/admin/stats`는 로그인 사용자의 대국·로그인 활동만 다루며, 익명 페이지 방문·유입 경로·검색어는 다루지 않는다. 이 공백을 채운다.

## 핵심 제약 (설계를 규정하는 사실)

1. **검색어는 방문 로그로 얻을 수 없다.** 구글·네이버는 HTTPS referrer에서 검색어(`?q=`)를 제거한다. 검색 결과에서 유입돼도 `Referer`는 `https://www.google.com/`까지만 온다. 검색어별 데이터는 **오직 구글 Search Console·네이버 서치어드바이저에만** 존재한다.
2. **콘텐츠 페이지는 Next.js(:3000)가 서빙**하고 FastAPI(:8000)는 `/api/*`만 받는다. 방문 수집은 클라이언트 비콘이 `/api/*` 엔드포인트로 보내는 방식이어야 두 서버 분리 문제가 풀린다.
3. **Cloudflare Tunnel이 앞단에 있어** `CF-IPCountry`(국가), `CF-Connecting-IP`(신뢰 가능 IP)가 백엔드에 도달한다. 국적은 GeoIP DB 없이 확보된다. 이미 `backend/app/client_ip.py`의 `client_country()`·`client_ip()`가 구현돼 있다.
4. **네이버는 자기 사이트 검색어를 주는 공식 API가 없다.** (네이버 검색광고 API는 광고 키워드 볼륨용으로 다름.) 네이버 검색어는 콘솔 CSV export를 수동 임포트하는 것이 최선이다.

## 아키텍처 개요 — 2모듈

- **모듈 A — 방문 로그(자체 수집)**: 클라이언트 비콘 → 백엔드 → SQLite `visit_hits`. 페이지뷰·순방문자·유입경로(검색사이트 단위)·국가별.
- **모듈 B — 검색어(콘솔 데이터)**: 구글은 Search Console API로 자동 수집, 네이버는 CSV 수동 임포트 → SQLite `search_queries`.

두 모듈은 독립이다. 데이터 모델·API·수집 경로가 분리돼 각각 따로 구현·테스트 가능하다. 어드민 UI에서만 두 탭으로 합쳐 보인다.

---

## 모듈 A — 방문 로그

### A.1 수집 경로

1. 모든 공개 페이지에서 클라이언트 훅이 라우트 진입 시 1회 `navigator.sendBeacon("/api/analytics/hit", body)` 호출.
   - `body`: `{ path: string, referrer: string }` (`referrer` = `document.referrer`).
   - 앱 셸(Capacitor) 빌드에서는 비활성(공개 웹에서만 수집).
2. 요청이 Cloudflare→터널→FastAPI로 도달. 엔드포인트 `POST /api/analytics/hit`(무인증, 공개):
   - `client_country(request)` → 국가코드, `client_ip(request)` → IP(원본은 저장 안 함).
   - `visitor_hash = sha256(ip + daily_salt)` — `daily_salt`는 서버 프로세스가 UTC 날짜별로 보관하는 랜덤값(재시작 시 재생성 허용). 당일 순방문자만 식별, 익일 재식별 불가.
   - `referrer` 파싱 → `referrer_host`(도메인) + `source` 분류.
   - User-Agent 봇 패턴(`bot|crawler|spider|slurp|yeti|bingbot|googlebot` 등) 매칭 시 저장 스킵.
   - `visit_hits` 1행 insert. 응답은 `204 No Content`.

### A.2 `source` 분류 규칙

`referrer_host` 기준:
- `search`: google.*, naver.*(search.naver.com 등), daum.*, bing.*, duckduckgo.*
- `social`: facebook, instagram, x.com/twitter, youtube, threads 등
- `internal`: inkbaduk.com 자기 도메인
- `direct`: referrer 없음(빈 문자열)
- `referral`: 그 외 외부 도메인

검색엔진 세부 구분(구글/네이버/다음/빙)은 `referrer_host` 원본을 함께 저장해 집계 시 도출.

### A.3 데이터 모델 `visit_hits`

| 컬럼 | 타입 | 비고 |
|---|---|---|
| id | int PK | |
| created_at | datetime | UTC, server default |
| path | str | 방문 경로(쿼리스트링 제거) |
| referrer_host | str \| null | 유입 도메인, direct면 null |
| source | str | search/social/referral/direct/internal |
| country | str(2) \| null | CF-IPCountry, 없으면 null |
| visitor_hash | str | 일일솔트 IP 해시 |
| device | str \| null | mobile/desktop (UA 기반, 선택) |

인덱스: `created_at`, `path`, `country`, `source`. **원본 IP 컬럼 없음.**

보존: 180일 초과 행은 ops 정리(주기 삭제). 트래픽 규모가 작아 롤업 테이블 없이 인덱스 직접 집계(YAGNI).

### A.4 집계 API `GET /api/admin/analytics`

- 인증: `AdminSession`. 파라미터: `days`(기본 30, 1~90), `top`(기본 20).
- 반환:
  - `totals`: `{ pageviews, unique_visitors }` (기간 내; unique는 일별 distinct 합).
  - `daily`: `[{ date, pageviews, uniques }]`.
  - `top_pages`: `[{ path, pageviews, uniques }]`.
  - `sources`: `[{ source, referrer_host, pageviews }]` — 검색엔진별 분해 포함.
  - `countries`: `[{ country, pageviews, uniques }]`.

순방문자(UV)는 일일솔트 특성상 **일 단위 순방문자**가 정확하고, 기간 UV는 일별 합산 근사(대시보드에 명시).

---

## 모듈 B — 검색어

### B.1 구글 — Search Console API(자동)

- 인증: **서비스 계정**. GCP 서비스 계정 키(JSON)를 만들고, 계정 이메일을 GSC 속성 `설정 → 사용자 및 권한`에 추가. 대화형 OAuth 불필요.
- `app/core/search_console/gsc.py`: `google-auth`로 서비스 계정 토큰 발급 후 `searchAnalytics/query` REST 호출(httpx). 차원 `["query","page","date"]`, 최근 N일.
- 동기화 잡: ops 크론(일 1회)이 최근 데이터를 `search_queries`에 upsert(`source="google"`). GSC 데이터는 2~3일 지연됨을 감안해 최근 ~5일 재조회.

### B.2 네이버 — CSV 수동 임포트

- 어드민 UI 업로드 → `POST /api/admin/search-queries/import`(multipart CSV, `AdminSession`).
- 네이버 콘솔 `콘텐츠 노출/클릭 → 검색 키워드` export 포맷(검색어·클릭·노출·CTR) 파싱 → `source="naver"`로 적재. 기존 naver 스냅샷은 교체.
- 페이지·순위 컬럼은 네이버 export에 없으면 null.

### B.3 데이터 모델 `search_queries`

| 컬럼 | 타입 | 비고 |
|---|---|---|
| id | int PK | |
| source | str | google / naver |
| query | str | 검색어 |
| page | str \| null | 랜딩 페이지 URL (google) |
| clicks | int | |
| impressions | int | |
| ctr | float | |
| position | float \| null | 평균 순위 (google) |
| date | date | 데이터 기준일(google 일별) 또는 스냅샷 종료일(naver) |
| fetched_at | datetime | 수집 시각 |

유니크: `(source, query, page, date)` upsert 키.

### B.4 조회 API `GET /api/admin/search-queries`

- 인증: `AdminSession`. 파라미터: `source`(google/naver/all), `days`, `top`.
- 반환: `[{ query, page, clicks, impressions, ctr, position, source }]` — 클릭·노출 내림차순 top-N.

---

## 어드민 UI — `/admin/analytics`

기존 `/admin/stats` 패턴·Editorial 디자인 시스템(StatFigure·DataBlock·토큰·lucide) 재사용. 어드민 네비에 "방문 통계" 추가.

- **탭 1 — 방문 현황** (모듈 A): KPI 행(PV·UV·기간 7/30/90) · 유입 경로(검색사이트별·소셜·직접) · 국가별 리스트 · 인기 페이지 top20 · 일별 추이.
- **탭 2 — 검색 유입** (모듈 B): 구글(자동)·네이버(임포트) 검색어 통합 표(검색어·클릭·노출·CTR·순위) · 소스 필터 · 네이버 CSV 업로드 버튼 · 마지막 동기화 시각.

## 설정·의존·마이그레이션

- `~/.baduk.env` 신규: `GSC_SERVICE_ACCOUNT_JSON`(키 파일 경로), `GSC_SITE_URL`(예: `sc-domain:inkbaduk.com`). 미설정 시 구글 동기화 잡은 no-op(네이버·방문로그는 독립 동작).
- 백엔드 dep 추가: `google-auth`(서비스 계정 토큰). REST 호출은 기존 httpx 사용.
- Alembic 마이그레이션 2개: `visit_hits`, `search_queries`.
- `/privacy` 페이지에 "자체 방문 분석(원본 IP 미저장, 국가·해시만)" 한 줄 추가.

## 보안·프라이버시

- 원본 IP 절대 저장 안 함. `visitor_hash`는 일일솔트로 익일 재식별 불가(Plausible 모델).
- `/api/analytics/hit`은 무인증 공개 엔드포인트 → 남용 방지: 요청 본문 크기 제한, 저장 전 봇 필터, 경로/referrer 길이 컷. rate-limit은 기존 미들웨어 정책 따름.
- 어드민 API·CSV 임포트는 `AdminSession` 필수. GSC 서비스 계정 키는 비밀로 취급(레포 커밋 금지, `~/.baduk.env` 경로 참조).

## 테스트 전략

- 모듈 A: `source` 분류 단위 테스트(각 referrer→source), `visitor_hash` 결정성·일일솔트 회전, 봇 필터, 집계 API 스냅샷(픽스처 삽입 후 totals/daily/sources/countries 검증).
- 모듈 B: 네이버 CSV 파서 단위 테스트(정상·헤더변형·빈값), GSC 클라이언트는 HTTP 모킹으로 응답 파싱 검증, `search_queries` upsert 유니크 키 동작.
- 프론트: 비콘 훅이 라우트당 1회 호출·앱셸 비활성, 어드민 페이지 렌더(Vitest).

## 범위 밖 (명시)

- 실시간 라이브 뷰(최근 N분 활성) — 추후.
- 네이버 검색어 자동화 — 공식 API 부재로 CSV 임포트가 최선.
- 크로스데이 개별 방문자 추적 — 프라이버시상 의도적 미지원.
