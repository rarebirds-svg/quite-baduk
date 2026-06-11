# Capacitor 앱 셸 설계 — App Store / Play Store 배포 (2026-06-11)

## 목적

inkbaduk(Next.js 14 웹앱)을 Google Play Store와 Apple App Store에 배포하기 위해 Capacitor
네이티브 래퍼를 도입한다. 출시 순서는 **Android 먼저, iOS 후속**. 앱 셸 전략은 **정적
export 번들**(원격 URL 모드 아님) — 오프라인 화면, 빠른 초기 로딩, Apple 4.2(최소 기능성)
방어에 유리하고 iOS까지 가는 유일하게 안전한 길이다.

## 결정 사항 요약

| 결정 | 선택 | 근거 |
|------|------|------|
| 출시 순서 | Android → iOS | Play 비공개 테스트로 셸 검증 후 Apple 심사 대응 |
| 셸 전략 | 정적 export 번들 | 오프라인·4.2 방어·iOS 호환. 원격 URL 모드는 서버 다운 = 앱 먹통 |
| 인증 | 쿠키 유지 + Bearer 토큰 이중화 | SameSite=None 쿠키는 iOS WKWebView에서 깨짐. 지금 토큰을 깔아 재작업 방지 |
| 동적 라우트 | 앱 포함 라우트만 쿼리 파라미터 전환 | `output:"export"`는 런타임 동적 세그먼트 미지원 |
| 라우트 제외 | 빌드 스크립트 임시 이동 방식 | 단일 코드베이스 유지, 최소 침습. 취약 시 `pageExtensions` 분리로 승격 |

## 현재 상태 (조사 결과)

- 핵심 화면(대국·관전·기록·설정)은 전부 `"use client"` + useEffect fetch — export 전환 용이.
- export 차단 요소는 세 가지.
  1. 동적 세그먼트 `[id]`/`[slug]` 전반에 `generateStaticParams` 없음 → export 빌드 실패.
  2. `faq`/`glossary`가 `force-dynamic` + 로컬 FS 읽기(`getContent()`) → export 불가.
  3. 인증이 쿠키 전용(`baduk_session` HttpOnly, WS 포함) → 교차 출처 WebView에서 불안정.
- `next.config.js`는 `output:"standalone"` + `/api/*` rewrite 프록시. export에서는 rewrite가
  동작하지 않으므로 앱은 절대 URL 직접 호출 + CORS 필요.
- `web/lib/ws.ts:78-85`에 이미 `NEXT_PUBLIC_WS_URL` 분기 존재 (Capacitor 대비 주석).
- `backend/app/config.py:36`에 `cookie_samesite:"none"` 옵션 존재 (사용하지 않기로 결정).

## 설계

### 1. 리포 구조와 빌드 모드

- Capacitor 프로젝트는 **`web/` 내부**에 둔다 (`web/capacitor.config.ts`, `web/android/`,
  후속으로 `web/ios/`). `webDir`는 `out`. Capacitor는 자기 루트의 `package.json`에서
  플러그인을 감지하므로 별도 `mobile/` 디렉토리로 분리하면 플러그인 등록이 깨진다.
  (2026-06-11 구현 조사 후 보정 — 원안은 `mobile/` 형제 디렉토리였음.)
- `web/next.config.js`를 `BUILD_TARGET=app` 환경변수로 분기.
  - 앱 빌드: `output:"export"`, rewrite 없음.
  - 웹 prod: 기존 `standalone` + rewrite 그대로 — **웹 배포 경로 불변**.
- `NEXT_PUBLIC_APP_SHELL=1` — 앱 빌드 전용 플래그. 코드 내 분기(후원 숨김, API 베이스,
  토큰 저장)에 사용.

### 2. 앱 포함 화면 (v1 범위)

**포함** — 홈(닉네임 게이트), `game/new`, `game/play`, `game/review`, 관전 목록·상세,
프로 기보 목록·상세, `daily`, `history`, `settings`, `privacy`, `terms`.

**제외** — `admin/*`, `dev/*`, `support`·`supporters`(스토어 외부 결제 정책 방어),
`faq/*`·`glossary/*`(force-dynamic + 로컬 FS, 웹 전용 SEO 표면),
`spectate/picks/*`·`spectate/themes/*`(서버 fetch SEO 표면), `sitemap.ts`/`robots.ts`.

**제외 메커니즘** — `scripts/build-app.sh`가 빌드 직전 제외 라우트 디렉토리를 임시 이동,
`trap`으로 원위치 복원 보장. 빌드 산출물은 `web/out/`.

### 3. 동적 세그먼트 → 쿼리 파라미터

앱 포함 라우트의 `[id]`를 쿼리 방식 페이지로 전환한다.

| 기존 (웹 유지) | 신규 (앱+웹 공용) |
|----------------|-------------------|
| `game/play/[id]` | `game/play?id=` |
| `game/review/[id]` | `game/review?id=` |
| `spectate/[id]` | `spectate/watch?id=` |
| `spectate/pro/[id]` | `spectate/pro/view?id=` |

- 페이지 본체를 공유 클라이언트 컴포넌트로 추출. 웹의 기존 `[id]` 경로는 유지(공유 링크·
  SEO 메타 보존)하되 같은 컴포넌트를 감싸는 얇은 셸로 남긴다.
- 앱 내 내비게이션과 신규 링크는 쿼리 방식으로 통일.

### 4. 인증 — 토큰 이중화

- `POST /api/session` 응답 body에 세션 토큰 포함.
- `backend/app/deps.py` `get_current_session` — 쿠키 우선, `Authorization: Bearer` 폴백.
  웹 동작 불변.
- `backend/app/api/ws.py` — `?token=` 쿼리 파라미터 인증 추가, 쿠키 폴백 유지.
- 앱 셸 — 토큰을 Capacitor Preferences에 저장. `web/lib/api.ts` 래퍼가
  `NEXT_PUBLIC_APP_SHELL`일 때 Bearer 헤더 첨부 + `API_BASE`를 `NEXT_PUBLIC_API_URL`
  절대 URL로 전환. `web/lib/ws.ts`는 토큰 쿼리 파라미터 추가.
- `CORS_ORIGINS`에 `https://localhost`(Android Capacitor 오리진) 추가. iOS 시점에
  `capacitor://localhost` 추가.

### 5. 네이티브 통합 (Android v1 최소셋)

- `@capacitor/app` — 하드웨어 뒤로가기 처리(Android 필수), 백그라운드 복귀 시 WS 재동기화.
- `@capacitor/haptics` — 착수 진동 (향후 iOS 4.2 방어 자산).
- `@capacitor/splash-screen` / `@capacitor/status-bar` — Editorial 토큰 색상 적용.
- 오프라인 안내 — 앱 셸은 `@capacitor/network` 플러그인, 웹은 브라우저 `online`/`offline`
  이벤트. (1차 보정에서 플러그인을 제거했으나 Android WebView에서 브라우저 이벤트가
  발화하지 않음이 에뮬레이터 스모크에서 확인되어 재보정. 2026-06-11)
- `@capacitor/preferences` — 세션 토큰 저장.
- 푸시·딥링크·공유는 v1 제외.

### 6. 단계 구성

1. **Phase 0** — 백엔드 토큰 인증 + CORS. 웹에 무해, 독립 배포·테스트 가능.
2. **Phase 1** — 프론트 앱 셸 모드. 빌드 분기, 쿼리 라우트 전환, api/ws 클라이언트,
   라우트 제외 스크립트, 후원 숨김, 오프라인 화면.
3. **Phase 2** — `mobile/` Capacitor Android 프로젝트 + 플러그인 통합.
4. **Phase 3** — 에뮬레이터·실기기 스모크, 웹 e2e 회귀 확인, Play 내부 테스트 트랙 준비.

## 테스트 전략

- Phase 0: pytest — 헤더 인증·WS 토큰 파라미터 단위/통합 테스트 추가. 기존 쿠키 테스트
  전부 통과 유지.
- Phase 1: `BUILD_TARGET=app` export 빌드 성공이 게이트. 기존 vitest + 웹 `npm run build`
  회귀 확인.
- Phase 2~3: Android 에뮬레이터 스모크(닉네임 입장 → 대국 → 백그라운드 복귀 → 재동기화),
  기존 웹 e2e 회귀.

## 범위 밖 (별도 트랙)

- 스토어 에셋(아이콘 1024px, 스플래시, 스크린샷), Play Console 계정·등급 설문.
- iOS 빌드 (`ios/`, Sign in with Apple 불필요 — 닉네임 전용).
- 푸시 알림, 딥링크, 세션 TTL 연장 정책.
