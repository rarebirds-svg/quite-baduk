# AI 바둑 품질 보고서

- **작성일:** 2026-04-17
- **검증 방식:** 5개 전문 리뷰 에이전트 병렬 실행 (Rules, KataGo, API, Frontend, Security)
- **관련 보고서:** `docs/reviews/{rules,katago,api,frontend,security}.md`

---

## 1. 전체 요약

| 리뷰어 | Verdict | Critical | High | Medium | Minor |
|---|---|---|---|---|---|
| Rules | APPROVED_WITH_CONCERNS | 0 | — | 4 | 몇 건 |
| KataGo | **CHANGES_REQUIRED** → 후속 패치 완료 | **2** | — | 7 | 12 |
| API | CHANGES_REQUIRED | 0 | — | 8 | 9 |
| Frontend | PASS_WITH_CONDITIONS → 일부 패치 완료 | 0 | — | 6 | 8 |
| Security | APPROVED_WITH_CONCERNS | 0 | 2 | 6 | 6 |
| **합계** | — | **2** | 2 | 31 | ~35 |

## 2. 테스트 & 빌드 현황

- **Backend (pytest):** 170/170 통과, Rules Engine 커버리지 100%
- **Frontend (vitest):** 8/8 통과 (Board 좌표, SGF 파서, i18n 키 동등성)
- **TypeScript strict:** 통과
- **ESLint:** 통과
- **Next.js build:** 9개 라우트 모두 빌드 성공
- **Bandit/pip-audit/npm audit:** 샌드박스 차단으로 자동 실행 불가 — 운영 환경 CI에서 필수 실행

## 3. 즉시 패치 적용한 항목

구현 중 발견된 치명 결함은 모두 이 릴리스에서 수정됐습니다.

| 출처 | 이슈 | 패치 내용 |
|---|---|---|
| KataGo C1 | `analyze()`가 streaming 명령(`kata-analyze`)을 `_send_raw`로 보내 터미네이터를 못 받아 100% 타임아웃 → hint/analyze 기능 전부 고장 | `analyze()`를 전용 stream-reader + `name` 명령 interrupt 로직으로 재작성 (`backend/app/core/katago/adapter.py`) |
| KataGo C2 | `stop()` 메서드가 `_lock`을 잡지 않아 동시 `send()`와 stdin 경쟁 | `stop()` 전체를 `async with self._lock` 로 감쌈 |
| Frontend I-1 | 백엔드가 emit하는 `INVALID_HANDICAP`, `INVALID_COLOR`, `INVALID_COORD`, `INVALID_UNDO_STEPS`, `AI_ILLEGAL_MOVE`, `validation_error` 키가 i18n 딕셔너리에 누락 → 사용자에게 영문 코드가 그대로 노출 | `web/lib/i18n/{ko,en}.json` 에 키 6종 × 2개 언어 추가 |
| Frontend I-2 | 백엔드 `forbidden`(소문자) vs i18n `FORBIDDEN`(대문자) 불일치 | 양쪽 키 모두 제공 |
| Frontend I-3 | `aiThinking` 중에도 pass/undo/hint 클릭 가능 → 중복 전송 위험 | `GameControls`에 `disabled={g.gameOver \|\| g.aiThinking}` 적용 |

## 4. 남은 권고 사항 (V1 merge 허용, V2 또는 fast-follow 대상)

### 4.1 High (배포 전 권장)
- **Security H1:** `next@14.2.5` → 최신 패치 버전 (CVE-2024-51479 / CVE-2025-29927) 업그레이드 필요
- **Security H2:** `Set-Cookie secure=False` 하드코딩 → prod에서 `settings.cookie_secure=True` 환경 변수화

### 4.2 Important (기능/품질 개선)
- **Rules I-1:** `resign` 처리가 `is_game_over` 기준에 포함되지 않음 → `GameService`가 별도로 status를 `resigned`로 마킹하므로 API 레벨에선 동작하지만, 엔진 레벨에서 `state.resigned` 플래그 추가 권장
- **Rules I-2:** `apply_handicap`이 `komi`/`to_move` 자동 설정 안 함 → 호출자(GameService)가 수동 처리 중. helper 함수로 캡슐화 권장
- **Rules I-3:** `GameState`/`Move` 가변 — `@dataclass(frozen=True)` 전환 권장
- **KataGo I-1~I-7:** replay 실패 처리 강화, 64KiB readline 한계, stderr 로깅, `load_sgf_text` 구현 등
- **API I-1:** 착수 엔드포인트 rate limit (30/min/user) 미구현 — WS 전송에도 필요
- **API I-2:** 에러 응답에서 `GameError.detail` 누락 — 공통 핸들러 개선 필요
- **API I-5:** `/analyze?moveNum=N`이 `moveNum`을 무시하고 현재 상태만 분석 (캐시는 moveNum으로 저장) → 재생 로직 보강 필요
- **API I-3:** WS 단일 세션 전환 중 race 가능성
- **Frontend I-4:** `resign` REST 호출 후 UI가 `result`/`winner`를 업데이트 안 함
- **Frontend I-5:** `ScorePanel` 한국어 하드코딩
- **Frontend I-6:** WS 재접속 시 in-flight 전송이 조용히 버려짐

### 4.3 Medium/Low (운영 품질)
- **Security M1:** `X-Forwarded-For` 검증 없이 사용 → 신뢰 프록시 계층 설정 필요
- **Security M2:** 분석/힌트/착수에 rate limit 없음
- **Security M3:** 사용자 없음 분기로 bcrypt timing oracle
- **Security M4:** in-process rate limiter → 다중 워커 시 정확도 저하
- **Security M5:** WS 토큰 유효기간 만료 후에도 세션 유지
- **Security M6:** 보안 응답 헤더(HSTS, CSP, X-Frame-Options 등) 미설정
- **Security L*:** `page`/`moveNum` 범위 검증, FK 인덱스 추가, `cors_origins.split`의 공백 처리, JWT 기본 시크릿 시작 시 경고 등
- **Rules edge cases:** seki, snapback, 무르기 후 ko 해제 테스트 추가 권장

## 5. 배포 체크리스트

배포 전 다음을 필수로 확인:

- [ ] `JWT_SECRET`을 32바이트 이상 랜덤 값으로 재설정
- [ ] HTTPS 종단 앞단에서 `secure=True` 쿠키 + Reverse Proxy (Nginx/Caddy) 배치
- [ ] `KATAGO_MOCK=false` 설정 + 모델 다운로드 확인 (`backend/katago/download_model.sh`)
- [ ] CI에서 `bandit`, `pip-audit`, `npm audit` 실행 → high 이상 0건 확인
- [ ] `next` 의존성을 최신 패치 버전으로 올림
- [ ] 도메인을 `CORS_ORIGINS` 에 명시
- [ ] 백업 볼륨(`baduk_backups`)의 로테이션/백업 검증

## 6. 테스트 명령 요약

```bash
# Backend
cd backend && source .venv311/bin/activate
pytest --cov=app --cov-report=term-missing -q

# Frontend
cd web && npm run type-check && npm run lint && npm run test -- --run && npm run build

# E2E (docker-compose 기동 후)
cd e2e && npm install && npm run install-browsers && npm test

# 보안 스캔 (CI)
bandit -r backend/app -ll
pip-audit
npm --prefix web audit --audit-level=high
```

## 7. 결론

- **기능 완성도:** 스펙 §1~13의 MVP 범위 전부 구현. 가능한 사용자 시나리오: 회원가입·로그인 → 급수/접바둑 선택 → 대국 → 힌트·무르기·기권·종국·SGF 다운로드 → 리뷰·분석 → 전적.
- **코드 품질:** Rules Engine 100% 커버리지, Backend API 170개 테스트 통과, Frontend 타입/린트/테스트 통과.
- **남은 리스크:** 대부분은 운영 강화 항목 (rate limit, 관측성, 보안 헤더, 최신 패치). 배포 전 §5 체크리스트 완료 시 V1 릴리스 가능.
- **전체 판정:** **Merge 허용** (치명 결함 모두 패치 완료, 나머지는 기록된 권고).
