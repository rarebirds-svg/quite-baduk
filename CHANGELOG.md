# Changelog

## [Unreleased]

### Added
- Capacitor 8 Android 앱 셸 (`web/android/`) — 기존 Next.js 웹앱을 네이티브 WebView로 감싼 모바일 클라이언트.
  - Bearer 토큰 인증 (`lib/sessionToken.ts`, Capacitor Preferences) — HttpOnly 쿠키와 병행; 웹 브라우저는 쿠키, 앱은 Bearer.
  - 정적 export 빌드 스크립트 (`web/scripts/build-app.sh`): `BUILD_TARGET=app`으로 `output:"export"` 전환, 웹 전용 라우트 임시 제외 후 `web/out` 생성.
  - 쿼리 진입점 라우트 헬퍼 (`lib/routes.ts`): 동적 세그먼트 대신 `/game/play?id=` 등 쿼리스트링 방식으로 네이티브 내비게이션.
  - 오프라인 배너 (`components/AppShellBridge.tsx`): 네트워크 단절 시 인라인 안내 표시.
  - 착수 햅틱: 착수 성공 시 Capacitor Haptics로 짧은 진동 피드백.
  - 앱 셸 환경에서 후원 링크 숨김 (`IS_APP_SHELL` 감지).
- CI 잡 `app-shell-build` 추가: `npm ci` + `bash scripts/build-app.sh` — 정적 export 가능 여부를 PR마다 검증.
- 착수 확인(2단계) 옵션 — 설정 › 착수 방식 (자동 / 한 번에 착수 / 확인 후 착수). 자동은 터치 기기(`pointer: coarse`)에서만 확인 단계를 두며, 가착수는 반투명 돌로 표시되고 같은 자리 재탭 또는 착수 버튼으로 확정한다 (`store/movePrefStore.ts`, `components/MoveConfirmToggle.tsx`).
- 착수음 토글을 대국 사이드바와 설정 화면에 노출 (`components/SoundToggle.tsx`) — 기존엔 복기 모달에만 있었다.
- 레전드 기사 인트로 카드 (`components/PersonaIntro.tsx`) — 첫 수 전에 기사 이름·국기·전성기·한 줄 소개를 보여준다.
- 비활성 계가 버튼에 툴팁 — 종반 감지 전에는 언제 열리는지 안내한다.
- 전적·기보 일괄 백업 — `GET /api/games/export`가 세션의 모든 대국을 SGF 파일 + `games.json` 요약으로 묶은 zip을 내려준다. 전적 화면 "모든 대국" 옆 버튼으로 노출. 닉네임 세션이 7일 뒤 사라져도 기보를 스스로 보관할 수 있다.
- 급수 문답이 판 크기도 함께 추천·적용 — "처음이에요"·"규칙은 알아요"·"작은 판 위주"는 9×9, 나머지는 19×19 (`components/RankAdvisor.tsx`의 `ADVISOR_PRESETS`).

### Fixed
- 같은 대국을 두 탭에서 열면 두 탭이 서로의 WebSocket을 1.5초마다 밀어내던 핑퐁 차단 — `SESSION_REPLACED`를 받은 탭은 재연결을 멈추고 "이 탭에서 이어두기" 버튼으로만 다시 붙는다. 오해를 부르던 "세션이 종료됐습니다" 문구도 연결 교체 안내로 교체.
- 사용자 기권 후 결과 줄이 `결과:`로 비던 문제 — 기권 응답의 `result`(`W+R`/`B+R`)를 화면에 반영.
- 첫 대국 힌트 코치마크와 30초 장고 프롬프트가 동시에 쌓이던 문제 — 코치마크가 닫힌 뒤에만 장고 타이머를 돌린다.
- 상단 테마·언어 토글의 접근성 이름이 `Theme: undefined`/영문 하드코딩이던 문제 — i18n 라벨로 교체.
- 프로 기보 기사명 인코딩 깨짐(`åœ‹æ ¾è ¡`) — `parse_pro_sgf`가 CA[] 없는 SGF를 ISO-8859-1로 읽던 sgfmill 기본값을 UTF-8로 고정하고, 주간 CWI 인제스트·시드·관리자 업로드가 HTTP 헤더 charset 대신 바이트를 직접 디코드(`decode_sgf_bytes`). 기적재 행은 `python -m scripts.repair_pro_mojibake`(`--dry-run` 지원)로 복구.

## [0.3.0] - 2026-06-06

### Added
- Public learning layer, browsable without an account:
  - Pro game library — 911 SGF records (625 masterpieces, 286 world-final games) with per-game
    analysis, themed collections, and a deterministic monthly "masterpiece" pick.
  - Daily challenge — 420 GoGameGuru puzzles with a daily deterministic pick and a random mode.
  - Glossary and FAQ — markdown articles with board diagrams and images.
  - Spectating — watch in-progress AI games and replay finished ones; pro games expose SEO metadata
    and a dynamic sitemap.
- Editorial Hardcover design system — paper/ink/oxblood/gold/moss tokens, serif/sans/mono
  typography, shadcn-based UI primitives, and custom editorial primitives.
- Admin console — sessions, login history, stats, and pro-game upload/management.
- Autonomous operations — launchd-scheduled agents for backups, content drafting, pro-game ingest,
  a health watchdog, and an orchestrator; plus a Cloudflare Workers external health monitor.
- Phase B single-node hardening — machine-restart recovery and hung-process auto-correction.

### Changed
- Authentication is now ephemeral nickname-only sessions (opaque random token in an HttpOnly cookie,
  1-hour idle TTL); email/password login removed.
- Dark mode migrated to `next-themes` (class-based) with full token coverage.
- Version bumped to 0.3.0 across `backend/pyproject.toml` and `web/package.json`.

### Notes
- The end-to-end (Playwright) job is temporarily disabled in CI pending a rewrite for the
  nickname-only flow.

## [0.2.0] - 2026-04-18

### Added
- 9×9 and 13×13 board sizes selectable at new-game time (default 19×19).
- Handicap tables extended to 9×9 (2–5 stones) and 13×13 (2–9 stones).

### Changed
- `Board` now carries its `size` as an instance attribute; `BOARD_SIZE` module constant removed from public API.
- `games.board_size` column added; `sgf_coord.gtp_to_xy` / `xy_to_gtp` take an explicit `size` argument.

### Removed
- Legacy 19×19-only DB schema. The 0002 migration drops and recreates `games`, `moves`, `analyses`.

## [0.1.0] - 2026-04-18

Initial release — MVP.

### Features
- Web-based Go board (19x19 SVG)
- Account system (email + password, JWT HttpOnly cookie)
- Rank selection: 18k, 15k, 12k, 10k, 7k, 5k, 3k, 1k, 1d, 3d, 5d, 7d (KataGo Human-SL model)
- Handicap games: 2–9 stones, Korean rules (komi 0.5)
- Even games: komi 6.5
- In-game actions: move, pass, resign, undo (2 plies), hint (top-3 winrate)
- Automatic rule enforcement: ko, suicide, capture
- Territory scoring (Korean rules)
- Game review: move-by-move replay + position analysis (winrate, top moves, ownership)
- SGF export (download)
- Personal history and stats
- i18n: Korean and English
- Dark mode
- Single-session policy per game (WebSocket)
- Auto-restart of KataGo subprocess with state replay
- Daily SQLite backup with 30-day rolling retention

### Architecture
- Frontend: Next.js 14 (App Router, TypeScript, Tailwind)
- Backend: FastAPI (Python 3.11, SQLAlchemy 2, Alembic, Pydantic v2)
- AI engine: KataGo v1.15.3 (Eigen CPU build) + `b18c384nbt-humanv0` model
- Database: SQLite with WAL
- Real-time: WebSocket
- Deployment: Docker Compose (web + backend + backup services)

### Quality
- 170 backend tests (pytest), Rules Engine 100% line coverage
- 8 frontend tests (Vitest)
- 5 end-to-end scenarios (Playwright)
- 5-agent parallel code review — see `docs/QUALITY_REPORT.md`

### Known Limitations
- No time controls (byoyomi, Fischer)
- No user-vs-user games
- No social login / OAuth
- No admin console
- Rate limiting only on login/signup (not on move/analyze endpoints)

See `docs/QUALITY_REPORT.md` for the full list of open recommendations.

[0.3.0]: https://github.com/rarebirds-svg/quite-baduk/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/rarebirds-svg/quite-baduk/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/rarebirds-svg/quite-baduk/releases/tag/v0.1.0
