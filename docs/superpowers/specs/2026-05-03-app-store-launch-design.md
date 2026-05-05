# App Store · Play Store 출시 — 상품화 설계서

- **작성일**: 2026-05-03
- **목표 출시일**: 2026-06-03 ± 며칠 (Play 14일 비공개 테스트가 임계 경로)
- **상태**: 설계 승인 대기 (사용자 검토 후 구현 계획 작성)
- **범위**: 현 Next.js + FastAPI + KataGo 스택을 iOS App Store와 Google Play Store에 동시 등록
- **앱 정식 명칭**: **AI 바둑** (한국어) / **AI Baduk** (영어)

---

## 1. 목표와 배경

**목표**: 자택 운영(Mac mini M4) + 가정용 회선 환경에서 동시 100명 활성 사용자를 목표로, 1개월 내에 양 스토어에 무료 앱으로 동시 출시한다.

**비목표 (V1.1+ 의제)**:
- 광고·인앱 결제·구독 (1.0 무료, PII 없음)
- 시간 제한(byoyomi/Fischer), 사용자 vs 사용자, 푸시 알림, 위젯, Siri Shortcuts, iCloud 동기화
- 7단·6단 강도 (워커 부하 검증 후 V1.1에서 복원)
- 다중 호스트 + Postgres 이행 (동접 1000+ 시 별도 스펙)

**성공 기준**:
- iOS .ipa + Android .aab 양쪽 정식 출시 (또는 1회 리젝 후 재제출 완료)
- 출시 직후 1주 가용성 ≥ 99% (홈 회선 기준)
- p95 착수 응답시간 < 1.5s
- 모든 P0 보안/품질 항목 처리 완료
- Privacy/Terms 페이지가 모바일 앱 메뉴에서 직접 접근 가능

**의도적 스코프 컷** (사용자 합의):
- 강도 상한 **5단**, 모든 등급 `max_visits=256` 캡
- 광고/IAP 없음 → 개인정보 라벨 "Data Not Collected"
- 모니터링은 Cloudflare 대시보드 + 양 스토어 콘솔 자체 리포트로

---

## 2. 배포 토폴로지

```
┌─ App Store ──────────┐    ┌─ Play Store ─────────┐
│  iOS .ipa            │    │  Android .aab         │
│  (Capacitor + WKWeb) │    │  (Capacitor + WebView)│
└──────────┬───────────┘    └────────────┬──────────┘
           │                             │
           │  HTTPS  (api.<도메인>)       │
           └──────────────┬──────────────┘
                          │
                  ┌───────▼────────┐
                  │ Cloudflare      │  무료 + DDoS + WAF
                  └───────┬────────┘
                          │  cloudflared (outbound only, 자택 IP 비노출)
                  ┌───────▼────────┐
                  │  Mac mini M4    │  자택 SKBB 회선
                  │  ┌────────────┐ │
                  │  │ FastAPI     │ │  uvicorn 단일 워커
                  │  └─────┬──────┘ │
                  │  ┌─────▼──────┐ │
                  │  │ KataGo × 4  │ │  Metal 빌드, GPU 가속
                  │  └────────────┘ │
                  │  ┌────────────┐ │
                  │  │ SQLite WAL  │ │
                  │  └────────────┘ │
                  │  ┌────────────┐ │
                  │  │ launchd     │ │  부팅 자동 시작 + 크래시 복구
                  │  └────────────┘ │
                  └─────────────────┘
```

**핵심 변경**:

- **Docker 폐기 (백엔드)** — KataGo Metal 가속을 위해 네이티브 실행. M4 GPU는 Apple Silicon Docker에선 사용 불가.
- **Cloudflare Tunnel (`cloudflared`)** — 자택 IP 비노출, 가정용 회선 80/443 차단 우회, 무료. 100명 트래픽엔 충분.
- **단일 도메인** — `<도메인>` (홈) + `api.<도메인>` (REST/WS).
- **launchd 서비스** — Mac mini 재부팅·KataGo 크래시 자동 복구.
- **백업** — `backup.sh` cron + Cloudflare R2 일일 동기화.

**의도적 배제**:

- ❌ Docker 운영, ❌ k3s/Kubernetes, ❌ Postgres 이전, ❌ Redis/큐 (모두 100명 규모엔 과함).

---

## 3. 백엔드 변경

### 3.1 KataGo Metal 빌드 + 워커 풀

**현재**: `backend/app/core/katago/adapter.py` 1개 + 단일 `asyncio.Lock` → 모든 게임 직렬.

**변경**: 신규 `backend/app/core/katago/pool.py`.

```python
class KataGoPool:
    def __init__(self, size: int = 4):
        self._adapters: list[KataGoAdapter] = [KataGoAdapter() for _ in range(size)]
        self._game_assignment: dict[int, int] = {}  # game_id → adapter index
        self._lock = asyncio.Lock()

    async def start_all(self) -> None: ...   # asyncio.gather 동시 기동, tune 캐시
    async def stop_all(self) -> None: ...
    def adapter_for(self, game_id: int) -> KataGoAdapter:
        # 신규 game_id는 가장 한가한 워커에 배정 → 이후 끈끈하게 유지
```

`engine_pool.py`는 `_adapter`를 `_pool: KataGoPool`로 교체. 게임 단위 `asyncio.Lock`과 `GameState` 캐시는 유지.

**KataGo 빌드** (`backend/katago/build_macos.sh` 신규):
- KataGo v1.15.3 소스 → `cmake -DUSE_BACKEND=METAL`
- 첫 기동 시 약 30~90초 GPU 튠 → `~/.katago/`에 캐시 → 재기동 즉시
- 폴백: M4가 Metal 빌드 실패 시 OpenCL 빌드 시나리오 1일 버퍼 확보
- 모델 `b18c384nbt-humanv0.bin.gz`은 기존 `download_model.sh` 그대로

**모의(`mock.py`)** — 그대로. `KATAGO_MOCK=true` 시 풀이 4개의 mock 어댑터를 띄워 동시성 테스트도 동일 검증.

### 3.2 강도 조정

`backend/app/core/katago/strength.py`:
- **7단·6단 임시 제거** (UI 셀렉터에서 빼서 선택 불가).
- 1단~5단 모두 `max_visits=256` 일괄 캡 (M4 Metal 기준 한 수 0.2~0.5초 예상).
- 급수 구간(18급~1급) 변경 없음.

### 3.3 FastAPI 운영

- **uvicorn 워커 1개** 유지 (`engine_pool` 싱글톤이 풀을 들고 있어 멀티 워커 시 풀이 N×4개 됨).
- **launchd 서비스** (`backend/deploy/com.baduk.api.plist` 신규) — 부팅 자동 시작 + 크래시 자동 재시작.
- 시스템 환경변수로 secret 분리.

### 3.4 Cloudflare Tunnel

- `cloudflared tunnel create baduk` + Cloudflare DNS에 자동 등록
- `<도메인>` → `localhost:3000` (Next.js, 웹 노출용 — 모바일은 정적 셸이라 직접 진입 안 함)
- `api.<도메인>` → `localhost:8000` (FastAPI)
- WebSocket: `wss://api.<도메인>/ws/...` — Cloudflare 무료 플랜 지원
- WAF 기본 + Rate Limiting Rules로 `/api/session POST 5/분` 같은 추가 보호

### 3.5 모바일 ↔ 백엔드 통신

- `cookie_secure=True` 강제, `samesite=none` 으로 변경 (Capacitor cross-site 처리).
  - 1주차에 `samesite=lax` 그대로 가능한지 실기 검증. 안 통하면 `none; secure` 또는 `Authorization` 헤더 폴백.
- `CORS_ORIGINS` 추가: `https://localhost`, `capacitor://localhost`, `https://<도메인>`.

### 3.6 SQLite (V1 유지)

- WAL 그대로. 100~1000명 동접까지 충분. 10000은 단일 호스트 자체가 한계라 별도 스펙.
- 출시 전 `VACUUM` 1회 + FK 인덱스 추가 (P1-7).
- DB URL을 `DATABASE_URL` 환경변수로 — 미래 Postgres 이행 가능성 보존 (이미 그렇게 되어 있을 가능성 ↑, 1회 점검).
- SQLite 전용 SQL(`JULIANDAY`, `INSERT OR REPLACE` 등) 사용 여부 grep 점검 — 0.5일 미만.

---

## 4. 보안 · 품질 must-fix

`docs/QUALITY_REPORT.md` 미해결 항목 + 스토어 제출 특수 요구사항을 P0/P1/P2로 분류.

### 4.1 P0 — 출시 전 반드시 (12건)

| # | 항목 | 위치 |
|---|---|---|
| P0-1 | Next.js 14.2.5 → 14.2.32+ (CVE-2024-51479, CVE-2025-29927) | `web/package.json` |
| P0-2 | `cookie_secure=True` 강제 + `samesite` 정책 결정 | `backend/app/config.py`, `app/api/session.py` |
| P0-3 | 보안 응답 헤더 (HSTS, CSP, X-Frame-Options, Referrer-Policy, X-Content-Type-Options, Permissions-Policy) | 신규 `app/middleware/security_headers.py` + Cloudflare Transform Rules |
| P0-4 | `/api/games/{id}/move`·`/api/analyze`·`/api/session` 레이트 리밋 | `app/rate_limit.py` 확장 |
| P0-5 | Cloudflare 신뢰 헤더 (`CF-Connecting-IP`) — Cloudflare IP 범위 외 요청은 헤더 무시 | `app/api/session.py:_client_key`, 공통 helper |
| P0-6 | Privacy/Terms 콘텐츠를 익명 세션 모델로 갱신 + 모바일 메뉴 진입점 추가 | `web/app/privacy/page.tsx`, `terms/page.tsx`, 모바일 메뉴 |
| P0-7 | 한국 GRAC 자체등급분류 표시 (Apple/Google 사업자 정보) | `web/app/terms/page.tsx` 끝에 게임물 정보 블록 |
| P0-8 | Apple App Privacy 라벨 "Data Not Collected" 선언 + 로그 IP 익명화 결정 | App Store Connect + 백엔드 로그 정책 |
| P0-9 | Google Data Safety 양식 "No data collected, no data shared" | Play Console |
| P0-10 | WebSocket 단일 세션 race 처리 — 모바일 백그라운드 ↔ 포그라운드 재연결 안정화 | `app/api/ws.py:_connections` |
| P0-11 | WS 재접속 in-flight 메시지 보존 (송신 큐) | `web/lib/ws.ts` |
| P0-12 | 세션 만료 후 WS 절단 (heartbeat) | `app/api/ws.py` |

### 4.2 P1 — 강한 권장 (9건, 시간 허락 시)

| # | 항목 | 위치 |
|---|---|---|
| P1-1 | `GameError.detail` 응답 누락 (공통 예외 핸들러) | `app/main.py` |
| P1-2 | `/analyze?moveNum=N`이 moveNum 무시 — 정확 분석 위해 보드 재생 후 분석 | `app/services/analysis_service.py` |
| P1-3 | `resign` 후 UI에서 result/winner 노출 | `web/store/gameStore.ts` |
| P1-4 | `ScorePanel` 한국어 하드코딩 → i18n | `web/components/ScorePanel.tsx` |
| P1-5 | KataGo replay 실패 처리 강화 | `app/core/katago/adapter.py`, 신규 `pool.py` |
| P1-6 | `load_sgf_text` 미구현 | `app/core/katago/adapter.py` |
| P1-7 | DB FK 인덱스 누락 — Alembic 마이그레이션 | `backend/migrations/` |
| P1-8 | `cors_origins.split` 공백 처리 | `app/config.py` |
| P1-9 | `page`/`moveNum` 범위 검증 (Pydantic constraints) | `app/schemas/` |

### 4.3 P2 — V1 이후 (이번 출시 외)

- Rules I-1~3 (resign 플래그, handicap 캡슐화, frozen dataclass)
- KataGo I-2~6 (64KiB readline, stderr 로깅, 부분 응답 처리)
- Security M3 (bcrypt timing) — 비밀번호 모델 폐기로 N/A
- Security M4 (multi-worker rate limiter) — 단일 워커 유지로 N/A
- seki / snapback / 무르기 후 ko 해제 추가 테스트

### 4.4 스토어 특이 항목

| 항목 | 처리 |
|---|---|
| Apple ATT (추적 동의) | 추적 안 함 → 다이얼로그 불필요 |
| Apple ATS (HTTPS only) | Cloudflare로 자동 충족 |
| Apple Guideline 4.2 (단순 래퍼) | §6의 네이티브 보강(Tier 1 + 가급적 Tier 2)으로 회피 |
| Apple 5.1.1.iv (데이터 최소화) | 익명 세션 모델로 자연스럽게 충족 |
| Google Play Target API 35 (Android 15) | Capacitor 7.x로 달성 |
| Sensitive Permissions | 인터넷·진동(VIBRATE)만. 카메라/위치/연락처/저장소 일체 없음 |
| 연령 등급 | 4+ / Everyone / 전체이용가 |
| 한국 청소년 보호 책임자 | 약관에 개발자 본인 표기 |

---

## 5. Capacitor 래핑 + 프론트엔드 변경

### 5.1 패키징 전략: 정적 셸 + 원격 API (하이브리드)

- 화면(보드, 리뷰, 설정)은 앱 번들에 포함 → 첫 페인트 < 100ms
- 게임 상태와 분석은 `https://api.<도메인>` 호출
- Apple 4.2 회피에 결정적 (즉시 렌더링되는 UI는 "단순 래퍼" 인상에서 멀어짐)

### 5.2 디렉터리 추가

```
mobile/
  capacitor.config.ts
  package.json            # Capacitor 7.x + 플러그인
  ios/                    # npx cap add ios
  android/                # npx cap add android
  www/                    # web/out/ 동기화 대상 (gitignore)
  resources/
    icon.png              # 1024×1024 마스터 (흑돌+백돌 모노그램)
    icon-foreground.png   # Android 적응형 (전경)
    icon-background.png   # Android 적응형 (배경)
    splash.png            # 2732×2732 (paper 배경 + BrandMark)
    splash-dark.png
```

빌드 흐름:
```
npm run build:mobile        # NEXT_PUBLIC_PLATFORM=mobile + output:export → web/out/
npm run cap:sync            # web/out → mobile/www, npx cap sync
npx cap open ios            # Xcode (Archive + 업로드)
npx cap open android        # Android Studio (.aab 빌드)
```

### 5.3 next.config.js 분기

```js
const isMobile = process.env.NEXT_PUBLIC_PLATFORM === 'mobile';
module.exports = {
  output: isMobile ? 'export' : 'standalone',
  images: { unoptimized: isMobile },
  trailingSlash: isMobile,
  ...(isMobile ? {} : { rewrites: ... }),
};
```

### 5.4 API/WS 호출 통합

- 신규 `web/lib/config.ts` — 빌드 시점에 `API_URL`, `WS_URL` 결정. 모바일은 `https://api.<도메인>` 하드코딩.
- 모든 `fetch`/`WebSocket` 호출이 이 모듈 경유 — 점검 1회 필요.

### 5.5 Capacitor 플러그인 (V1 스코프)

| 플러그인 | 용도 |
|---|---|
| `@capacitor/haptics` | 착수·캡쳐·종료 햅틱 (4.2 보강 핵심) |
| `@capacitor/share` | 시스템 공유 시트로 SGF 공유 |
| `@capacitor/app` | 백그라운드/포그라운드 감지 → WS 재연결, 뒤로가기 인터셉트 |
| `@capacitor/network` | 오프라인 배너 |
| `@capacitor/status-bar` | 다크/라이트 시 시스템 바 색상 동기화 |
| `@capacitor/splash-screen` | 종이 무드 스플래시 |
| `@capacitor/preferences` | 닉네임·테마·언어 저장 (localStorage 폴백 가능) |

### 5.6 모바일 UI 조정

- Safe-area 패딩 (`env(safe-area-inset-*)`) — 노치/펀치홀 회피
- Pull-to-refresh 비활성화 (게임 중 실수 리로드 방지)
- 뒤로가기 인터셉트 (Android, 게임 중 confirm 다이얼로그)
- i18n 자동 감지 (`Capacitor Device.getLanguageCode()`)

### 5.7 Editorial 디자인 시스템 호환성

- 토큰(paper/ink/oxblood/gold/moss) + Newsreader/Pretendard 폰트 그대로
- 모바일 빌드는 폰트를 앱 번들에 포함 (오프라인 + 첫 페인트 일관성)
- 다크 모드 `next-themes` `attribute="class"` 그대로
- Lucide 아이콘 트리쉐이킹 그대로

### 5.8 빌드 부산물 크기 목표

| 플랫폼 | 목표 |
|---|---|
| iOS .ipa | < 25 MB |
| Android .aab | < 15 MB (사용자 다운로드 ~8 MB) |

KataGo 모델/바이너리는 **모바일 빌드에 포함 안 됨** (서버 전용).

---

## 6. 네이티브 보강 (Apple Guideline 4.2 회피)

여러 작은 네이티브 신호를 누적시키는 게 4.2 회피의 가장 안전한 전략.

### 6.1 Tier 1 — 필수 (2.5일)

**햅틱**: 내·상대 착지(Light), 캡쳐(Medium), 합법수 아님(Warning), 게임 종료(Success). `web/lib/haptics.ts` (플랫폼 가드 + 웹 noop). 설정 화면 토글.

**시스템 공유 시트**: 게임 종료/리뷰에 "공유" 버튼 → SGF 임시 파일 → `Share.share({ files })`. 웹은 download 어트리뷰트 폴백.

**사운드**: `web/public/sounds/` 활용. Web Audio API. 새 트랙 4종(stone-soft, stone-firm, pass, end) 라이선스 깨끗한 freesound.org에서 정리. 사용자 토글 + 시스템 무음 모드 존중.

**시스템 다크 모드 자동 추종**: `next-themes` 기본을 `system`으로 + `@capacitor/status-bar`로 시스템 바 색 동기화.

**네이티브 스플래시**: 1024×1024 BrandMark + paper 배경 → `@capacitor/assets` 자동 생성. 페이드아웃 300ms.

### 6.2 Tier 2 — 권장 (시간 허락 시 +2일)

**Files 앱 .sgf 핸들러**: iOS `Info.plist` `CFBundleDocumentTypes` + Android `<intent-filter>`. `appUrlOpen` 이벤트로 SGF import → 리뷰 화면 자동 이동. **4.2 회피에 큰 신호.**

**Quick Actions**: 홈 화면 길게 누르기 → "이어하기 / 새 게임 / 기보 보기". `@capacitor-community/app-shortcuts`.

### 6.3 Tier 3 — V1.1 이후

위젯, Siri Shortcuts, iPad Apple Pencil + 키보드, iCloud, 푸시 알림.

### 6.4 Android 동등 보강 (자동)

- 햅틱 → Vibrator API (`VIBRATE` 권한)
- 공유 → `ACTION_SEND` 인텐트
- 다크 모드 → DayNight 테마
- 스플래시 → SplashScreen API (Android 12+)
- .sgf intent-filter
- 뒤로가기 인터셉트 (Capacitor `App` 플러그인)
- Edge-to-edge (Android 15 필수, Capacitor 7 기본)

---

## 7. 스토어 자산 & 메타데이터

### 7.1 앱 식별

| 항목 | 값 |
|---|---|
| 앱 이름 (한글) | **AI 바둑** |
| 앱 이름 (영문) | **AI Baduk** |
| Subtitle (iOS) | "KataGo와 한 판" / "Play against KataGo" |
| Bundle ID / Application ID | `<도메인역순>.baduk` (도메인 결정 후 확정) |
| Primary Category | Games > Board |
| Secondary Category (iOS) | Strategy |
| 연령 등급 | 4+ / Everyone / 전체이용가 |

### 7.2 아이콘 — 흑돌+백돌 모노그램

- 1024×1024 마스터 1장 → `@capacitor/assets`로 모든 사이즈 자동 생성
- 컨셉: paper 톤 또는 oxblood 단색 배경 + 흑돌·백돌이 살짝 겹친 미니멀 모노그램
- 텍스트 없음 (스토어 정책)
- iOS 둥근 모서리 자동 적용 → 사각형 + 여백 최소
- Android 적응형 아이콘: 전경(돌)/배경(paper) 분리

### 7.3 추가 그래픽

- Play Feature graphic 1024×500
- 스플래시 마스터 2732×2732 + 다크 변형

### 7.4 스크린샷 (한·영 각 6장)

| # | 화면 | 캡션 한 / 영 |
|---|---|---|
| 1 | 홈 + 새 게임 | 18급에서 5단까지, 12개의 강도 / From 18-kyu to 5-dan |
| 2 | 19×19 게임 중 | KataGo Human-SL이 사람처럼 둡니다 / KataGo plays like a human |
| 3 | 분석/힌트 패널 | 수마다 승률과 추천수 / Winrate and top moves, every move |
| 4 | 리뷰 모드 | 끝낸 게임, 한 수씩 복기 / Replay any game, move by move |
| 5 | 다크 모드 보드 | 야간 모드 + 종이 결 / Editorial dark mode |
| 6 | 통계 화면 | 급수별 전적과 흐름 / Stats by rank and handicap |

iOS는 6.9" iPhone (1290×2796) 만 제출하면 자동 스케일. Android는 폰 1080×1920+ 최소 2장.

### 7.5 텍스트 (한·영)

**Short description (≤80자)**:
- 한: "KataGo의 Human-SL 모델로 18급부터 5단까지 12단계 강도. 승률·복기·핸디캡 지원."
- 영: "Play Go against KataGo Human-SL — 12 strength tiers from 18-kyu to 5-dan."

**Full description**: 후크 + 8줄 불릿 + KataGo 설명 + 프라이버시 + 지원. 양 스토어 동일 본문.

**Keywords (iOS, 100자)**:
- 한: `바둑,Go,KataGo,기원,복기,SGF,AI,두뇌,보드`
- 영: `Go,Baduk,Weiqi,KataGo,AI,SGF,review,board game,strategy`

### 7.6 개인정보 라벨

| 스토어 | 신고 |
|---|---|
| Apple App Privacy | "Data Not Collected" — 단, IP 로깅 익명화 결정 후 확정 |
| Google Data Safety | "No data collected, no data shared" + "Encrypted in transit" |

### 7.7 한국 게임물관리위원회

- Apple/Google이 자체등급분류사업자 → 별도 신청 불필요
- 약관에 "자체등급분류 사업자 (Apple App Store / Google Play)" + 등급 표시 권장
- 누적 매출/다운로드 발생 시 GRAC 직접 등록 검토 (V1.1+)

### 7.8 심사용 데모 메모

```
본 앱은 익명 닉네임 세션을 사용합니다. 첫 화면의 "시작" 버튼을 누르면
닉네임 입력 후 즉시 게임이 가능합니다. 가입·로그인·결제 흐름이 없습니다.

This app uses anonymous nickname sessions. Tap "Start" on the home screen,
enter any nickname, and play immediately. No signup, login, or payment.
```

### 7.9 필수 URL

- Privacy: `https://<도메인>/privacy`
- Terms: `https://<도메인>/terms`
- Support: `mailto:support@<도메인>` 또는 `/support` 페이지
- Marketing: `https://<도메인>/`

---

## 8. 테스트 전략

### 8.1 레이어

| 레이어 | 도구 | 목표 |
|---|---|---|
| 백엔드 | pytest | 170 → 180+ (풀 + P0 패치) |
| 프론트 단위 | Vitest | 8 → 15+ (Capacitor 어댑터 noop) |
| E2E | Playwright | 5 → 10+ (모바일 시나리오) |
| iOS 실기기 | TestFlight | 본인 + 5명 |
| Android 실기기 | Play Closed Testing | **12명+ (정책 강제)** |
| 시각 회귀 | `visual-qa` | 라이트·다크 12장 베이스라인 |
| 한국어 카피 | `korean-copy-qa` | 새 i18n 키 100% |
| 접근성 | `a11y-auditor` | axe critical/serious 0 |
| 디자인 토큰 | `design-token-guardian` | 모바일 신규 코드 클린 |

### 8.2 모바일 E2E 시나리오

```
e2e/tests/mobile/
  onboarding.spec.ts       # 첫 실행 → 닉네임 → 새 게임 → 첫 착수
  background-resume.spec.ts # WS 끊김 → 재연결 → 상태 복원
  offline-banner.spec.ts    # 네트워크 차단 → 배너 → 복구
  share-sgf.spec.ts         # 게임 종료 → 공유 (Capacitor mock)
  dark-mode-auto.spec.ts    # 시스템 다크 토글 → 즉시 반영
```

`web/lib/native-mocks.ts`로 Capacitor 플러그인 모킹.

### 8.3 부하 테스트 (선택, 0.5일)

- k6 100명 시뮬, 1분당 1수, 30분 지속
- 측정: p95 < 1.5s, p99 < 3s, 워커 큐 ≤ 4, SQLite 잠금 평균 < 50ms

### 8.4 출시 전 최종 체크리스트

```
[ ] 백엔드 30분 안정 동작 (launchd 재시작 0회)
[ ] KataGo 워커 4개 모두 정상
[ ] SGF export → import 라운드트립
[ ] P0 12건 완료
[ ] visual-qa 12장 무회귀
[ ] korean-copy-qa 통과
[ ] a11y-auditor 위반 0
[ ] design-token-guardian 클린
[ ] Privacy/Terms 모바일 메뉴 접근 가능
[ ] 데이터 라벨 사실 일치
[ ] 공유 시트 실기기 동작 (iOS + Android)
[ ] 햅틱 실기기 + 토글
[ ] 다크 모드 시스템 자동 추종
[ ] 백그라운드 → 포그라운드 WS 재연결 5/5
[ ] Cloudflare Tunnel 24h 무재시작
[ ] 백업 → R2 업로드 성공
[ ] launchd 재부팅 자동 시작 검증
```

---

## 9. 1개월 일정

오늘 2026-05-03 (일) 기준. 목표 공개 출시 **2026-06-03 ± 며칠**.

### 9.1 임계 경로

```
Day 1  (5/3 일) — 도메인 구매 + Apple/Play 계정 등록
Day 7  (5/9 토) — Cloudflare Tunnel + 백엔드 공개 운영
Day 10 (5/13 수) — Play 첫 .aab Closed Testing 업로드 → 14일 카운트 시작 ⏰
Day 14 (5/17 일) — iOS 첫 TestFlight 빌드 업로드
Day 24 (5/27 수) — Play 14일 종료 → Production 신청
Day 24 (5/27 수) — App Store 정식 심사 제출
Day 28~32       — 양 스토어 공개 출시
```

### 9.2 주차별 작업

#### Week 1 — 5/3~5/9 (기초 인프라 + 계정)

| 트랙 | 작업 |
|---|---|
| 인프라 | (1) 도메인 구매 (5/3). (2) Apple Developer 가입. (3) Play Console 가입. (4) Cloudflare 위임 |
| 백엔드 | (5) KataGo Metal 빌드. (6) `KataGoPool` 구현 + 테스트. (7) `engine_pool.py` 풀 전환. (8) 강도 상한 5단/256. (9) launchd plist + 부팅 검증 |
| 프론트 | (10) `next.config.js` 분기. (11) `lib/config.ts`. (12) `output:'export'` 빌드 통과 |
| 스토어 | (13) Bundle ID 확정. (14) 카테고리/연령 결정 |

**끝 상태**: 도메인 활성, Cloudflare Tunnel로 공개 HTTPS, KataGo 4 워커 풀 안정, 모바일 빌드 성공.

#### Week 2 — 5/10~5/16 (Capacitor + 네이티브 + Play 14일 시작)

| 트랙 | 작업 |
|---|---|
| 백엔드 | P0-1, P0-2, P0-3, P0-4, P0-5, P0-10, P0-11, P0-12 |
| 모바일 셸 | `mobile/` + Capacitor 7 init + add ios/android. 플러그인 7종 설치. 햅틱·공유·다크·스플래시 통합 |
| 모바일 UI | Safe-area, 뒤로가기 인터셉트, pull-to-refresh 비활성화, i18n 자동 감지 |
| 자산 | 1024 아이콘 마스터 디자인 + 자동 생성. 스플래시 마스터 |
| 베타 모집 | 12명+ 옵트인 시작 (Google Form, 한·영) |
| Play | **5/13 수: 첫 .aab Closed Testing 업로드** → 14일 카운트 시작 |

**끝 상태**: 양 플랫폼 실기기 동작, Play 14일 진행 중, 12명 옵트인 완료.

#### Week 3 — 5/17~5/23 (P1 + 자산 + iOS 베타)

| 트랙 | 작업 |
|---|---|
| 백엔드 | P1-1, P1-2, P1-7. 선택: P1-6 |
| 프론트 | P1-3, P1-4. WS 재접속 큐 마무리. Files 앱 .sgf 핸들러 (Tier 2). 오프라인 배너 |
| 자산 | 스크린샷 12장 (한·영 × 6). Feature graphic. 설명 텍스트. Privacy/Terms 갱신 (P0-6). 지원 페이지 |
| iOS | **5/17 일: 첫 TestFlight 업로드**. Beta App Review 24~48h. Internal Testing 본인+5명 |
| QA | visual-qa, korean-copy-qa, a11y-auditor, design-token-guardian |

**끝 상태**: 양 스토어 메타데이터 90%, iOS TestFlight 동작, QA 통과, P0 완료.

#### Week 4 — 5/24~5/30 (제출 + 심사)

| 트랙 | 작업 |
|---|---|
| 부하 테스트 | k6 100명 시뮬 (선택, 0.5일) |
| iOS | **5/27 수: App Store 정식 심사 제출** |
| Android | **5/27 수: Play Production 트랙 신청** |
| 백업·모니터링 | backup.sh + R2 동기화. Cloudflare 다운 알림. launchd 재시작 카운터 |
| 리젝 대응 버퍼 | 4.2 보강 추가, Data Safety 조정 |
| 테스터 피드백 | 작은 패치 1~2회 |

**끝 상태**: 양 스토어 심사 통과 또는 1회 리젝 후 재제출.

#### Week 5 — 5/31~6/6 (출시 + 안정화)

- 양 스토어 공개 출시 (수동 릴리스, 안정성 확인 후)
- 출시 후 24h 모니터링
- 첫 핫픽스 윈도우
- `CHANGELOG.md` 1.0.0
- README 갱신 (스토어 배지, 다운로드 링크)

### 9.3 일정 압축 옵션 (필요 시)

- Tier 2 (Files 핸들러, Quick Actions) 보류 → 2일 단축. 4.2 위험 ↑.
- 부하 테스트 생략 → 0.5일 단축.
- P1-2/P1-6/P1-7 V1.1로 이연 → 1일 단축.

---

## 10. 리스크 + 미해결 의사결정

### 10.1 기술 리스크

| # | 리스크 | 확률 | 영향 | 완화 |
|---|---|---|---|---|
| T1 | KataGo Metal 빌드 시행착오 | 중 | 1~3일 | OpenCL 폴백. 최악의 경우 Eigen CPU + 4d 캡 |
| T2 | Capacitor 쿠키 차단 | 중 | 1일 | 1주차 실기 검증. `samesite=none; secure` 또는 헤더 폴백 |
| T3 | WS 재연결 race | 중 | UX 저하 | 베타 피드백 조기 발견 |
| T4 | Mac mini 정전·재부팅 | 저 | 다운타임 | UPS 권장. launchd 자동 복구 |
| T5 | KataGo 메모리 누수 | 저 | 며칠 후 OOM | RAM 임계 모니터 → 자동 재시작 |
| T6 | Cloudflare 무료 한계 | 저 | 차단 | 100명 규모 한참 미만 |

### 10.2 스토어 리스크

| # | 리스크 | 확률 | 영향 | 완화 |
|---|---|---|---|---|
| S1 | Apple 4.2 (단순 래퍼) 리젝 | **중상** | 1~2주 | Tier 1 + Tier 2 보강. 리젝 시 즉시 재제출 |
| S2 | Apple 5.1.1 라벨 부정확 | 저 | 1~3일 | IP 로깅 익명화 + 자체 검토 |
| S3 | Play 14일 활동 부족 | 중 | +14일 | 12명+ + 일일 사용 독려 |
| S4 | Bundle ID 충돌 | 저 | 명칭 재선택 | 1주차 즉시 등록 |
| S5 | GRAC 사후 신고 | 저 (V1) | 6~12개월 | V1.1+ 의제 |

### 10.3 운영 리스크

| # | 리스크 | 완화 |
|---|---|---|
| O1 | SKBB 약관 위반 → 회선 정지 | 100명 규모 발각 거의 없음. 발각 시 콜로/VPS 24~48h 이전 가능 상태 유지 |
| O2 | DDoS | Cloudflare 무료 + WAF + Rate Limiting Rules |
| O3 | 단일 운영자 | 출시 후 1주 매일 헬스체크. 알림 자동화 (Cloudflare 다운 → 이메일) |
| O4 | 백업 복구 미검증 | 출시 전 1회 복구 드릴 (0.5일) |
| O5 | 악성 닉네임 | `core/nickname.py` 필터 + 신고 메일 |

### 10.4 미해결 의사결정 (1주차 안에 결정)

| # | 결정 | 후보 | 시점 |
|---|---|---|---|
| D1 | 도메인 이름 | 사용자 결정 (예: `aibaduk.app`, `baduk.kr`) | 5/3 즉시 |
| D2 | Bundle ID | `<도메인역순>.baduk` | 도메인 직후 |
| D3 | Apple Developer 유형 | Individual 권장 | 5/3 |
| D4 | 사운드 V1 포함 | 포함 (0.3일) / 보류 | 1주차 |
| D5 | Tier 2 포함 여부 | 시간 허락 시 포함 | 3주차 초 |
| D6 | 베타 테스터 12명 명단 | 가족·친구 + 커뮤니티 | 1주차 |
| D7 | 고객 지원 이메일 | `support@<도메인>` | 1주차 |
| D8 | 청소년 보호 책임자 | 개발자 본인 | 약관 갱신 시 |
| D9 | 마케팅 채널 | 한국 바둑 커뮤니티, Reddit, Twitter, SNS | 출시 직전 |

### 10.5 V1 의도적 비포함

- 푸시, 시간 제한, PvP, 7d/6d, 위젯, Siri Shortcuts, iCloud, Apple Pencil
- 한국 GRAC 직접 등록
- 다중 호스트 + Postgres
- E2E 모바일 자동 테스트 CI 통합
- 광고/IAP

### 10.6 출시 직후 1주 KPI

| 지표 | 목표 |
|---|---|
| 백엔드 가용성 | ≥ 99% |
| p95 착수 응답시간 | < 1.5s |
| KataGo 워커 큐 평균 | < 2 |
| 크래시율 (스토어 콘솔) | < 1% 세션 |
| 사용자 피드백 응답시간 | 24h |

---

## 11. 다음 단계

본 설계 문서가 승인되면 `superpowers:writing-plans` 스킬로 **구현 계획서**를 작성한다. 계획서는 본 설계의 모든 작업 항목을 PR 단위 또는 단계 단위로 분해하고, 각 단계의 검증 방법과 롤백 절차를 명시한다.
