# 출시 전 QA 베이스라인 보고서

- **작성일**: 2026-05-03
- **대상 릴리스**: 1.0.0 (App Store · Play Store 동시 출시, 목표 2026-06-03)
- **연관 설계서**: [`docs/superpowers/specs/2026-05-03-app-store-launch-design.md`](../superpowers/specs/2026-05-03-app-store-launch-design.md)
- **목적**: 스토어 출시 작업 시작 전 현재 코드베이스의 단위/통합 테스트, 보안 스캔, 정적 분석, 디자인·카피 일관성을 종합 검증해 작업 우선순위를 확정한다.

---

## 1. 종합 결과

| 영역 | 결과 | Critical | High | Medium | Low |
|---|---|---|---|---|---|
| 백엔드 단위/통합 테스트 (pytest) | ✅ 334/334 | 0 | 0 | 0 | 0 |
| 프론트엔드 단위 테스트 (Vitest) | ✅ 51/51 | 0 | 0 | 0 | 0 |
| 백엔드 정적 분석 (mypy strict) | ✅ Clean | 0 | 0 | 0 | 0 |
| 프론트엔드 정적 분석 (TypeScript strict + ESLint) | ✅ Clean | 0 | 0 | 0 | 0 |
| 백엔드 린트 (ruff) | ⚠️ 1 error | 0 | 0 | 0 | 1 |
| 백엔드 코드 커버리지 (`--cov-fail-under=80`) | ⚠️ 79.50% | 0 | 1 | 0 | 0 |
| 백엔드 보안 린트 (bandit) | ✅ 0 med/high | 0 | 0 | 0 | 8 |
| 백엔드 의존성 취약점 (pip-audit) | ⚠️ 1 (pip 자체) | 0 | 0 | 0 | 1 |
| 프론트엔드 의존성 취약점 (npm audit) | 🔴 13건 | **1** | **6** | **6** | 0 |
| 디자인 토큰 준수 | ⚠️ 5건 | 0 | 0 | 4 | 1 |
| i18n 키 파리티 (ko ↔ en) | ✅ 348/348 일치 | 0 | 0 | 0 | 0 |
| 한국어 카피 자연스러움/용어 일관성 | ⚠️ 12건 | 0 | 0 | 7 | 5 |
| **합계** | — | **1** | **7** | **17** | **15** |

**결론**: 코드 자체의 동작 품질은 매우 양호하지만 **출시를 막는 항목 1건(npm 의존성 critical) + 즉시 처리해야 할 high 7건**이 있습니다. 모두 설계서의 P0/P1 항목과 매핑되어 있고, 1주차 안에 해소 가능합니다.

---

## 2. 단위/통합 테스트 결과

### 2.1 백엔드 (pytest, KATAGO_MOCK=true)

```
334 passed, 9 warnings in 4.49s
TOTAL coverage: 79.50%
```

- **테스트 수**: 334 (CHANGELOG 0.1.0 기준 170 → 현재 334로 증가, 거의 두 배)
- **분포**: `tests/rules/`, `tests/katago/`, `tests/api/`, `tests/test_*.py` (30 파일)
- **실패**: 0
- **경고 9건**: 모두 `aiosqlite` 백그라운드 워커 스레드의 `RuntimeError: Event loop is closed` — 테스트 종료 시 이벤트 루프 정리 race. **코드 결함 아님**, 향후 conftest의 fixture teardown 순서 보강으로 정리.

#### 모듈별 커버리지 핵심

| 모듈 | 커버리지 | 비고 |
|---|---|---|
| `app/core/rules/*` | **94~100%** | 룰 엔진 — 출시 품질 |
| `app/core/katago/adapter.py` | (mock만 검증) | 풀 컨버전 시 통합 테스트 보강 필요 |
| `app/api/*` | 평균 90%+ | 양호 |
| `app/services/game_service.py` | **70%** | **유일한 약점** — 113줄 미커버. 분기(에러 경로, 핸디캡, 리뷰)가 주 미커버 |
| 모델/스키마 | 100% | 완벽 |

#### 액션 아이템

- **A1 [High]** `--cov-fail-under=80` CI 게이트가 **현재 79.50%로 실패**. `game_service.py`에 미커버 분기 테스트 5~10개 추가 → 0.5일.
- **A2 [Low]** aiosqlite teardown race 경고 — `tests/conftest.py` fixture에 `await db.close()` + `await engine.dispose()` 명시 → 0.3일.

### 2.2 프론트엔드 (Vitest)

```
Test Files  10 passed (10)
Tests       51 passed (51)
Duration    1.41s
```

- **테스트 수**: 51 (CHANGELOG 0.1.0 기준 8 → 현재 51로 6배 증가)
- **분포**: `board.test.tsx` (25), `editorial/*`, `ui/*`, `lib/*`, `i18n.test.ts`, `sgf.test.ts`
- **실패**: 0

#### 액션 아이템

- **A3 [Medium]** Capacitor 어댑터 모킹 테스트 미존재. 모바일 작업 시작과 동시에 `lib/haptics.test.ts`, `lib/share.test.ts` 추가. (설계서 §5.5)

### 2.3 통합 / E2E

- **상태**: 본 베이스라인 실행 시점에 Docker 스택을 띄우지 않아 **Playwright E2E 미실행**. 5개 시나리오는 CHANGELOG 기준 모두 작동.
- **출시 전 필수**: 풀 컨버전 + Capacitor 모바일 모킹 후 재실행. 모바일 시나리오 5종 추가는 설계서 §8.2.

---

## 3. 정적 분석

### 3.1 백엔드

| 도구 | 결과 |
|---|---|
| mypy --strict | ✅ Success: no issues found in 48 source files |
| ruff (E,F,I,B,UP,S,W) | ⚠️ 1 error |
| bandit (security lint) | ✅ 0 medium/high (low 8건, 모두 의도된 사용) |

#### ruff 오류 1건

```
S105 Possible hardcoded password assigned to: "jwt_secret"
  --> app/config.py:10:23
   jwt_secret: str = "changeme-in-production"
```

- **B1 [Low]** **`jwt_secret`은 데드 코드**. `app/security.py`에서 확인했듯이 비밀번호/JWT 인증은 익명 닉네임 세션 모델로 폐기됨. `app/config.py`에서 필드 자체를 제거해야 한다 (CLAUDE.md의 인증 모델 일관성 + ruff 클린).
- **위치**: `backend/app/config.py:10`
- **검증**: `grep -n "jwt_secret" backend/app/**/*.py` 결과 `config.py` 1곳만 사용. 다른 import 없음.

### 3.2 프론트엔드

| 도구 | 결과 |
|---|---|
| TypeScript (`tsc --noEmit`) | ✅ Clean |
| ESLint (next lint) | ✅ No warnings or errors |

---

## 4. 의존성 취약점

### 4.1 백엔드 — pip-audit

```
Found 1 known vulnerability in 1 package
pip 26.0.1  CVE-2026-3219
```

- **C1 [Low]** `pip 26.0.1` — pip 자체는 빌드 도구이며 런타임 인스톨 안 함. `pip install --upgrade pip`으로 즉시 해소. 출시 일정에 영향 없음.
- 그 외 런타임 의존성(FastAPI, SQLAlchemy, Alembic, Pydantic, structlog) 취약점 없음.

### 4.2 프론트엔드 — npm audit (13 vulnerabilities)

```
13 vulnerabilities (6 moderate, 6 high, 1 critical)
```

| 패키지 | 등급 | CVE/Advisory 수 | 처치 |
|---|---|---|---|
| **next** (14.2.5) | 🔴 **Critical** | 17건 | **`next@14.2.35`로 업그레이드** (설계서 P0-1) |
| postcss | Moderate | 1건 | next 업그레이드와 함께 해소 |
| **glob** (eslint-config-next 체인) | High | 1건 | dev only — `npm audit fix --force` |
| **minimatch** (typescript-eslint 체인) | High | 3건 | dev only — `npm audit fix` |
| esbuild (vite/vitest) | Moderate | 1건 | dev only — `vitest@4` 마이너 업글 |

#### Next.js 17개 advisory 발췌 (중요)

- GHSA-gp8f-8m3g-qvj9 — Cache Poisoning
- GHSA-f82v-jwr5-mffw — **Authorization Bypass in Middleware** (CVE-2025-29927, 설계서 P0-1)
- GHSA-3h52-269p-cp9r — Dev server origin verification (information exposure)
- GHSA-4342-x723-ch2f — SSRF via middleware redirect
- GHSA-q4gf-8mx6-v5v3 / GHSA-mwv6-3258-q52c / GHSA-5j59-xgg2-r9c4 — Server Components DoS (3종)
- 그 외 이미지 최적화/캐시 관련 다수

**모두 14.2.35에서 해소.** 우리는 `output: 'export'` 모바일 빌드 + `output: 'standalone'` 웹 빌드 둘 다 해당 경로를 일부 사용하므로 업그레이드는 **출시 차단(P0)**.

#### 액션 아이템

- **C2 [Critical]** `web/package.json`: `"next": "14.2.5"` → `"^14.2.35"` → `npm install` → `next build` 회귀 테스트.
- **C3 [High]** `npm audit fix` (비강제) 1회 적용 → minimatch/glob/postcss 동시 해소.
- **C4 [High]** `eslint-config-next` 메이저 업그레이드는 보류(브레이킹 변경). next 14.2.35 호환되는 14.x 마이너만 적용.
- **C5 [Medium]** vitest/esbuild 업그레이드는 dev 전용 + 영향 도구 한정 → V1.1로 이연 가능.

---

## 5. 디자인 토큰 준수 (`design-token-guardian` 에이전트)

총 **5건 위반, 모두 `web/app/settings/page.tsx`에 집중**.

| # | 라인 | 카테고리 | 위반 | 수정 |
|---|---|---|---|---|
| D1 | 48 | Radius | `rounded` (기본값) | `rounded-sm` |
| D2 | 55 | Radius | `rounded` (기본값) | `rounded-sm` |
| D3 | 48 | 다크 모드 토큰 | `dark:bg-gray-900` (Tailwind 기본) | `dark:bg-paper-deep` |
| D4 | 55 | 다크 모드 토큰 | `dark:bg-gray-900` | `dark:bg-paper-deep` |
| D5 | 49 | i18n | 하드코딩 `"한국어"` | `t("settings.langKo")` + ko/en JSON 추가 |

**준수 양호 항목**:
- ✅ 하드코딩 hex 0건 (메타태그 SEO 색은 허용)
- ✅ 인라인 `font-family` 0건
- ✅ 이모지 0건
- ✅ `framer-motion` import 0건
- ✅ 금지 radius (md/lg/xl/2xl) 0건
- ✅ 비허용 shadow 0건 (`Board.tsx` lithic 예외만 사용)

#### 액션 아이템

- **E1 [Medium]** 5건을 한 PR로 일괄 수정. 작업량 < 1시간. 출시 전 처리.

---

## 6. i18n 파리티 + 한국어 카피 (`korean-copy-qa` 에이전트)

### 6.1 키 파리티

```
ko.json: 348 keys
en.json: 348 keys
ko-only: 0
en-only: 0
배열 길이 불일치: 0
```

✅ **완벽 일치**. 양 파일 동시 추가 규칙이 잘 지켜지고 있음. 네이티브 플러그인 키(햅틱 토글, 공유, 오프라인 배너) 추가 시 동일 규칙 유지.

### 6.2 하드코딩 한국어 (고객 노출 4건)

| # | 파일:줄 | 값 | 제안 키 |
|---|---|---|---|
| K1 | `web/app/layout.tsx:14` | `"Baduk — 조용한 승부"` (메타 타이틀) | `app.metaTitle` |
| K2 | `web/app/layout.tsx:15` | `"KataGo Human-SL과 두는 한국식 바둑 ..."` (메타 설명) | `app.metaDescription` |
| K3 | `web/app/settings/page.tsx:49` | `"한국어"` | `settings.langKo` (D5와 동일) |
| K4 | `web/components/RankPicker.tsx:36` | `${n}단` / `${n}급` 리터럴 | `settings.suffixDan` / `settings.suffixKyu` |

> 메타 타이틀이 **"Baduk — 조용한 승부"** 인데, 우리는 §6.1에서 앱 이름을 **"AI 바둑 / AI Baduk"** 으로 확정했습니다. 메타 타이틀도 일관되게 갱신해야 합니다 → 설계서 P0-6 콘텐츠 갱신 작업에 추가.

### 6.3 바둑 용어 불일치 (4건)

| # | 키 | 현재 | 권장 | 이유 |
|---|---|---|---|---|
| T1 | `game.komiLabel` (ko) | "코미" | **"덤"** | 한국기원 공식 표기. "코미"는 일본어 외래어 |
| T2 | `game.handicap` (ko) | "대국방식" | **"핸디캡"** | 같은 화면 `game.sectionHandicap` ("핸디캡")과 통일 |
| T3 | `admin.inProgress`, `admin.endReasonActive` (ko) | "진행중" | **"진행 중"** | 국립국어원 띄어쓰기 표준 |
| T4 | `home.valueDesc3` (ko) | `scoreLead`, `ownership` 영문 혼용 | **"집 차이", "영역 판정"** | 일반 사용자 대상 마케팅 카피에 영문 기술 용어 부적절 |

### 6.4 영어 카피 점검 (2건)

| # | 키 | 현재 | 권장 | 이유 |
|---|---|---|---|---|
| E1 | `game.info`, `moves`, `move`, `captures`, `toMove`, `winrate` (en) | `"INFO"`, `"MOVES"`, ... (ALL CAPS) | sentence case (`"Info"`, `"Moves"`) | Editorial 시스템상 ALL CAPS는 masthead/badge 전용 |
| E2 | `game.color` (en) | `"Order"` | `"Color"` 또는 `"Stone color"` | 흑/백 선택 맥락에 부적절 |

### 6.5 어색한 번역 / 호칭 (5건)

| # | 키 | 현재 | 권장 |
|---|---|---|---|
| N1 | `game.colorYou` (ko) | `"당신"` | `"나"` (`game.you`와 통일) |
| N2 | `errors.NOT_YOUR_TURN` (ko) | `"당신 차례가 아닙니다"` | `"지금은 내 차례가 아닙니다"` |
| N3 | `game.yourTurn` (ko) | `"당신 차례"` | `"내 차례"` |
| N4 | `admin.refreshed` (ko) | `"자동 새로고침 {sec}초"` | `"{sec}초마다 자동 새로고침"` |
| N5 | `session.expiredDesc` (en) | `"Please set a nickname to continue"` | `"Your session has expired. Please choose a nickname to continue."` |

#### 액션 아이템

- **F1 [Medium]** 6.2~6.5 항목 일괄 수정. 키 추가/이전 + 호칭 정리. 작업량 1~1.5시간. 설계서 P0-6 콘텐츠 갱신과 함께 처리.

---

## 7. 보안/품질 — 설계서 P0/P1 매핑 검증

설계서의 P0/P1 항목 일부는 본 베이스라인 시점에 이미 일부 구현되어 있었습니다. 정확한 현재 상태:

| 설계서 ID | 항목 | 현재 상태 | 비고 |
|---|---|---|---|
| P0-1 | Next.js 14.2.5 → 14.2.35+ | ❌ 미적용 | npm audit critical 17건 — **출시 차단** |
| P0-2 | `cookie_secure=True` 강제 | ⚠️ 부분 — `settings.cookie_secure` 변수 존재, prod 강제 X | 환경변수 검증 |
| P0-3 | 보안 응답 헤더 | ❌ `app/middleware/` 디렉터리 자체 미존재 | 신규 작성 |
| P0-4 | 레이트 리밋 | ⚠️ 부분 적용 | `/games/{id}/hint` 30/min, `/analyze` 60/min, `/session` 적용. **WS `move` 핸들러 미적용** (`app/api/ws.py:148`) |
| P0-5 | Cloudflare 신뢰 헤더 | ❌ `_client_key`가 `X-Forwarded-For` 사용 | `CF-Connecting-IP` 우선 + IP 화이트리스트 |
| P0-6 | Privacy/Terms 갱신 | ❌ 익명 세션 모델 미반영 + 메타태그 옛 카피 | 본 보고서 §6.2의 메타 타이틀/설명 갱신 포함 |
| P0-7 | GRAC 표시 | ❌ 약관에 미표기 | 약관 끝 블록 추가 |
| P0-8 | Apple App Privacy 라벨 | — | 콘솔 작업 (코드 변경 없음) |
| P0-9 | Google Data Safety | — | 콘솔 작업 |
| P0-10 | WS 단일 세션 race | ⚠️ `_connections` 핸드오프 부분 구현, 백그라운드 ↔ 포그라운드 시나리오 검증 미흡 | 모바일 E2E로 검증 |
| P0-11 | WS 재접속 in-flight 큐 | ❌ `web/lib/ws.ts`에 송신 큐 없음 | 신규 |
| P0-12 | 세션 만료 후 WS 절단 | ❌ heartbeat 없음 | 신규 |

**기존에 이미 처리된 항목** (설계서에서 별도 작업 불필요): 룰 엔진 100% 커버리지, 단일 세션 정책 기본 골격, 익명 세션 모델, alembic 마이그레이션, design-token-check 훅.

---

## 8. 출시 전 즉시 조치 액션 리스트

우선순위 순. 모두 설계서 1주~2주차 범위 내 처리.

### 🔴 출시 차단 (Critical)

| # | 작업 | 작업량 | 매핑 |
|---|---|---|---|
| 1 | **Next.js 14.2.5 → 14.2.35** | 0.3일 | C2 / P0-1 |

### 🟠 High (1주차 안에)

| # | 작업 | 작업량 | 매핑 |
|---|---|---|---|
| 2 | `npm audit fix` (비강제) — minimatch/glob/postcss 해소 | 0.2일 | C3 |
| 3 | `game_service.py` 분기 커버리지 +5~10 테스트 → 80% 게이트 통과 | 0.5일 | A1 |
| 4 | `app/config.py` `jwt_secret` 데드 코드 제거 (ruff S105 해소) | 0.2일 | B1 |
| 5 | WS `move` 핸들러 레이트 리밋 추가 | 0.3일 | P0-4 일부 |
| 6 | Cloudflare 신뢰 헤더 (`CF-Connecting-IP`) 사용 + IP 화이트리스트 | 0.5일 | P0-5 |
| 7 | 보안 응답 헤더 미들웨어 신규 작성 | 0.5일 | P0-3 |

### 🟡 Medium (2~3주차)

| # | 작업 | 작업량 | 매핑 |
|---|---|---|---|
| 8 | 디자인 토큰 5건 일괄 수정 (`settings/page.tsx`) | 0.1일 | E1 |
| 9 | i18n 카피 12건 일괄 수정 (덤/핸디캡/진행 중/호칭/메타태그) | 0.2일 | F1 |
| 10 | Capacitor 모킹 테스트 추가 | 0.5일 | A3 |
| 11 | aiosqlite teardown 경고 정리 | 0.3일 | A2 |
| 12 | WS heartbeat (세션 만료 동기화) | 0.5일 | P0-12 |
| 13 | WS 송신 큐 (재접속 in-flight 보존) | 0.5일 | P0-11 |

### ⚪ Low / V1.1 이연

- pip 업그레이드 (C1)
- vitest/esbuild 업그레이드 (C5)
- eslint-config-next 메이저 (C4)

**총 작업량**: Critical/High 2.5일 + Medium 2.1일 = **약 4.6일** (병렬 실행 시 2~3일).

---

## 9. 다음 단계

1. ✅ **본 보고서 + 설계서 사용자 검토**
2. ✅ **§8 Critical/High 7건 즉시 패치** (옵션 A) — §11 부록 참조
3. 검토 후 `superpowers:writing-plans` 스킬로 **구현 계획서** 작성
4. 1주차 시작 (Day 1: 도메인 + 개발자 계정 등록)과 동시에 잔여 Medium 항목 처리

---

## 부록 — 실행 명령 기록

```
# 백엔드
cd backend && source .venv311/bin/activate
KATAGO_MOCK=true pytest --cov=app --cov-report=term-missing -q       # 334 passed, 79.50%
KATAGO_MOCK=true pytest --cov=app --cov-fail-under=80 -q             # FAIL (79.50% < 80%)
ruff check .                                                          # 1 error (S105 jwt_secret)
mypy app                                                              # Success
bandit -r app -ll                                                     # 0 medium/high
pip-audit                                                             # 1 (pip 자체)

# 프론트엔드
cd web
npm test -- --run                                                     # 51 passed
npm run type-check                                                    # Clean
npm run lint                                                          # Clean
npm audit                                                             # 13 vulns (1 critical, 6 high, 6 mod)

# QA 에이전트
design-token-guardian → 5 violations (settings/page.tsx)
korean-copy-qa       → 12 issues (terminology + naturalness)
```

> E2E (Playwright)·visual-qa·a11y-auditor는 Docker 스택 기동이 필요해 본 베이스라인에 포함하지 않았다. 1주차 후반(Cloudflare Tunnel 가동 후) 실행해 별도 보고서로 첨부.

---

## 11. 부록 — Critical + High 패치 적용 결과 (2026-05-03)

§8의 Critical 1건 + High 6건을 본 베이스라인 직후 일괄 패치했다. 적용 내역:

| # | 작업 | 변경 파일 | 결과 |
|---|---|---|---|
| 1 | **Next.js 14.2.5 → 14.2.35** | `web/package.json`, `package-lock.json` | npm audit 13건 (Critical 1, High 6) → **10건 (Critical 0, High 4)** — Auth Bypass·Cache Poisoning·SSRF 등 17개 advisory 해소. 잔여 4건은 Next 15/16 메이저 업그레이드 필요 (DoS류, V1.1 의제) |
| 2 | **`npm audit fix`** (비강제) | `package-lock.json` | 적용 — 잔여는 모두 `--force` 필요라 미진행 |
| 3 | **`jwt_secret` 데드 코드 제거** | `backend/app/config.py` | ruff S105 1건 → **0건** |
| 4 | **WS `move`/`pass`/`undo` 레이트 리밋** | `backend/app/api/ws.py` | move+pass: 60/min/세션, undo: 20/min/세션. `error.code=rate_limited` 응답 후 연결 유지 |
| 5 | **Cloudflare 신뢰 헤더 (CF-Connecting-IP)** | `backend/app/client_ip.py` (신규), `backend/app/config.py` (`cf_trusted_proxy: bool`), `backend/app/api/session.py` | `X-Forwarded-For` 신뢰 폐기 (스푸핑 위험). `cf_trusted_proxy=True` 시에만 CF 헤더 사용 |
| 6 | **보안 응답 헤더 미들웨어 분리 + 보강** | `backend/app/middleware/security_headers.py` (신규), `backend/app/middleware/__init__.py` (신규), `backend/app/main.py` | 기존 X-Content-Type-Options / X-Frame-Options / Referrer-Policy / HSTS에 **Content-Security-Policy + Permissions-Policy** 추가. CSP는 Next.js 14 호환(`unsafe-inline`/`unsafe-eval` 허용, frame-ancestors none, ws/wss connect 허용) |
| 7 | **`game_service.py` 커버리지 70% → 73%, 전체 79.50% → 80.03%** | `backend/tests/api/test_game_service_errors.py` (신규, 8개 테스트), `backend/tests/test_client_ip.py` (신규, 5개 테스트) | INVALID_BOARD_SIZE / INVALID_HANDICAP / INVALID_COLOR / FORBIDDEN / GAME_NOT_ACTIVE / IllegalMoveError 변환 / white user_color / handicap 경로 + client_ip 4개 분기 모두 검증. **`--cov-fail-under=80` CI 게이트 통과** |

### 11.1 패치 후 최종 상태

| 검증 | 적용 전 | 적용 후 |
|---|---|---|
| 백엔드 pytest | 334 통과, 79.50% | **347 통과, 80.03%** ✅ 게이트 통과 |
| 프론트엔드 vitest | 51 통과 | 51 통과 |
| ruff | 1 error (S105) | **0 errors** ✅ |
| mypy strict | 48 files clean | 51 files clean |
| bandit | 0 med/high | 0 med/high |
| TypeScript / ESLint | clean | clean |
| **npm audit critical** | **1** | **0** ✅ |
| npm audit total | 13 (1 C, 6 H, 6 M) | 10 (0 C, 4 H, 6 M) |

### 11.2 코드 변경 요약

```
backend/app/client_ip.py                         | 신규 (33줄)
backend/app/middleware/__init__.py               | 신규 (0줄)
backend/app/middleware/security_headers.py       | 신규 (75줄, 기존 main.py에서 분리 + 보강)
backend/app/config.py                            | -1 (jwt_secret) +7 (cf_trusted_proxy)
backend/app/main.py                              | -27 (인라인 미들웨어 → import)
backend/app/api/session.py                       | -7 (_client_key) +1 (import)
backend/app/api/ws.py                            | +18 (rate_limit 가드 2건)
backend/tests/api/test_game_service_errors.py    | 신규 (213줄, 8 tests)
backend/tests/test_client_ip.py                  | 신규 (75줄, 5 tests)
web/package.json                                 | next/eslint-config-next 14.2.5 → 14.2.35
web/package-lock.json                            | (재생성)
```

### 11.3 잔여 의제

본 패치 이후에도 계획에 남는 항목:

- **§8 Medium 6건** (디자인 토큰 5건, i18n 카피 12건, Capacitor 모킹 테스트, aiosqlite teardown, WS heartbeat, WS 송신 큐) — 1~2주차 작업 안에 분산
- **잔여 npm audit 10건** (Next 14.x 4 high + dev-only 6 moderate) — 모두 메이저 업그레이드 필요, V1.1 의제
- **개발자 계정·도메인·Cloudflare Tunnel** 등 인프라 작업은 본 베이스라인 범위 외 — 1주차 시작 시 별도 진행
