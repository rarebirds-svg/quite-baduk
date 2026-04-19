# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Web app to play Go (Baduk) against KataGo's Human-SL model. Three sibling directories — no monorepo tooling; each has its own build/test system.

- `backend/` — FastAPI (Python 3.11) + SQLAlchemy 2 async + SQLite
- `web/` — Next.js 14 App Router + TypeScript + Tailwind + Zustand
- `e2e/` — Playwright (hits the running Docker stack)

## Commands

### Backend (from `backend/`)

```bash
source .venv311/bin/activate            # venv already exists at .venv311
pip install -e ".[dev]"                 # after dep changes
uvicorn app.main:app --reload           # local dev (set KATAGO_MOCK=true in .env)
pytest                                  # full suite (170 tests)
pytest tests/rules/test_ko.py::test_simple_ko  # single test
pytest --cov=app --cov-fail-under=80    # CI-equivalent coverage gate
ruff check .                            # lint (rules E,F,I,B,UP,S,W; line 100)
mypy app                                # strict mode
alembic upgrade head                    # apply migrations
alembic revision --autogenerate -m "…"  # new migration
```

### Frontend (from `web/`)

```bash
npm run dev                             # localhost:3000, needs backend at :8000
npm run build && npm start
npm run lint                            # next lint / eslint
npm run type-check                      # tsc --noEmit
npm test -- --run                       # Vitest (jsdom)
npm test -- --run tests/board.test.ts   # single file
```

### End-to-end (from `e2e/`)

```bash
docker-compose up --build -d            # (from repo root) stack must be running
npm install && npm run install-browsers # first time only
npm test                                # playwright test
npx playwright test tests/review.spec.ts
```

### Docker (from repo root)

```bash
cp .env.example .env                    # set KATAGO_MOCK=true for dev without the 200MB model
docker-compose up --build               # web :3000, backend :8000, nightly backup sidecar
```

## Architecture

### Rules Engine — `backend/app/core/rules/`

Pure Python, no framework deps, 100% line coverage. Treat as a library — callers pass `GameState` in, get a new `GameState` out. `engine.py` is the public surface (`play`, `pass_move`, `score`, `build_sgf`, `is_game_over`, `IllegalMoveError`). Sub-modules (`board`, `captures`, `ko`, `scoring`, `handicap`, `sgf_coord`) are implementation details. Korean rules: komi 6.5 even, 0.5 with handicap. Do not add I/O or DB calls here.

### KataGo Adapter — `backend/app/core/katago/`

`adapter.py` manages one KataGo subprocess over GTP (stdin/stdout). Single `asyncio.Lock` serializes commands — GTP is strictly request/response. On process death, the adapter restarts and replays `_ReplayState` (boardsize, komi, profile, plays) to restore position. `mock.py` is a deterministic stand-in selected when `KATAGO_MOCK=true`; all tests use it. `strength.py` maps UI rank → `(human_sl_profile, max_visits)`; higher ranks use more visits (7d=512) and are slow on CPU.

### Engine pool — `backend/app/engine_pool.py`

Process-wide singletons: one shared `KataGoAdapter`, a `dict[game_id, asyncio.Lock]` to serialize per-game mutations, and a `dict[game_id, GameState]` cache so we don't replay SGF from DB on every move. The adapter is a single shared subprocess — before issuing commands for a given game you must re-seed the board state (`clear_board` + replay). The per-game `asyncio.Lock` must be held while doing this so another game's handler can't interleave.

### WebSocket session — `backend/app/api/ws.py`

`_connections: dict[int, WebSocket]` enforces one active WS per `game_id`. A new connection evicts the old one with code `SESSION_REPLACED` — user-facing error referenced in README troubleshooting. Auth is via `access_token` HttpOnly cookie (same as REST).

### Game flow — `backend/app/services/game_service.py`

`create_game` → `place_move` → (optional) `undo_move` → auto-finalize on two consecutive passes or resign. `place_move` applies the user's move via the pure rules engine, then calls KataGo for the AI reply, then persists both to DB. Keep rules-engine purity: DB and KataGo calls live in the service layer, not in `core/rules/`.

### Frontend state — `web/store/`

Zustand: `authStore` (user session), `gameStore` (board + move list + analysis). Board rendering is SVG in `components/Board.tsx`. WebSocket client in `lib/ws.ts` reconnects on disconnect and reconciles with the `state` payload from the server (authoritative). `lib/i18n/` is a small homegrown dictionary loader, not i18next.

### Auth

Email + bcrypt password, JWT (access + refresh) in HttpOnly cookies. `app/security.py` issues/verifies; `app/deps.py` exposes FastAPI dependencies. Refresh flow is cookie-only (no header auth).

## Conventions

- Backend uses `from __future__ import annotations` and modern generics (`list[…]`, `X | None`). ruff's `UP` rules enforce this.
- `mypy` is `strict`; don't add `# type: ignore` without a comment.
- `ruff` forbids `print` — use the configured `structlog` JSON logger.
- Tests are colocated by layer: `tests/rules/`, `tests/katago/`, `tests/api/`. `conftest.py` provides DB + FastAPI test-client fixtures.
- Frontend path alias: none — use relative imports. Tailwind classes only; no CSS modules.
- Docker is the reference deployment. If a change works locally but breaks the Docker build, the Docker build wins.

## UI/UX 디자인 시스템 규칙 (0.3.0+ · Editorial Hardcover / Journal)

공개 서비스 수준의 UI를 위해 디자인 시스템이 도입되었습니다. 모든 새 프론트엔드 코드는 아래 규칙을 따릅니다. 스펙: `docs/superpowers/specs/2026-04-20-ui-ux-uplift-design.md`.

**색상** — 토큰만 사용. 하드코딩 hex 금지.
- `bg-paper` / `bg-paper-deep` / `text-ink` / `text-ink-mute` / `text-ink-faint`
- 악센트: `oxblood` (primary), `gold` (승률 강조), `moss` (성공·최적수)
- 다크 모드: 모든 토큰에 `dark:` 변형 — 예) `bg-paper dark:bg-paper` (토큰 자체가 모드별 값 가짐)
- 원본 값은 `web/app/globals.css` CSS 변수로만 선언

**타이포그래피** — Tailwind 클래스만.
- `font-serif` (Newsreader — 헤딩·영문 본문) / `font-sans` (Pretendard — 한글 본문·UI) / `font-mono` (IBM Plex Mono — 숫자·좌표)
- 인라인 `style={{ fontFamily: ... }}` 금지
- 숫자는 `tabular-nums` 기본. `web/lib/i18n/`를 거치지 않은 하드코딩 한국어 문자열 금지

**아이콘** — `lucide-react` 사용. 이모지 금지. 기본 크기 16px, `strokeWidth={1.5}`. 바둑 전용 기호(패스·기권·핸디캡)는 `web/components/editorial/icons/`의 독자 SVG.

**모션** — Tailwind transition / CSS keyframes만. `framer-motion` 금지. 정의된 easing: `transition-base` 150ms, `transition-stone` 300ms `cubic-bezier(.2,.7,.2,1)`. 장식용 entry/stagger 애니메이션 금지.

**Radius / Shadow** — `rounded-none` (카드·보드), `rounded-sm` (2px 기본), `rounded-full` (토글·배지·돌)만. 그림자는 사용하지 않음 — 위계는 규칙선과 배경 대비로.

**컴포넌트 구조**
- `web/components/ui/` — shadcn 프리미티브 (Button, Card, Dialog, Input, Select, Tabs, Tooltip, DropdownMenu, Sheet, Separator 등). 설치 직후 Editorial 토큰으로 재스타일링.
- `web/components/editorial/` — 독자 프리미티브: `Hero` `RuleDivider` `StatFigure` `DataBlock` `PlayerCaption` `KeybindHint` `EmptyState` `Spinner` `BrandMark`. Go 도메인 아이콘도 여기.
- `web/app/` 화면 파일에는 UI 로직을 직접 쓰지 말 것 — 프리미티브 조합만.

**다크 모드** — `next-themes` `attribute="class"` 사용. `ThemeBootstrapper`와 `lib/theme.ts`는 폐기 예정 (Phase 1에서 next-themes로 교체).

**i18n** — 새 문구는 `web/lib/i18n/ko.json`과 `en.json`에 **동시** 추가. 키 누락은 `korean-copy-qa` 에이전트가 체크.

**자동 가드** — `.claude/hooks/design-token-check.sh`가 `Write`/`Edit` 후 `web/components/*` 또는 `web/app/*`에서 하드코딩 hex·이모지를 검출해 경고합니다. `design-token-guardian` 에이전트로 수동 감사 가능.

## 프로젝트 에이전트 팀

`.claude/agents/` 에 5개 커스텀 에이전트 정의:

- **`editorial-implementer`** — 화면 1개를 디자인 스펙대로 구현 (frontend-design 스킬 강제, sonnet)
- **`design-token-guardian`** — 토큰 준수 감사 (read-only, haiku)
- **`visual-qa`** — Playwright 스크린샷 + 라이트/다크 시각 회귀 (sonnet)
- **`korean-copy-qa`** — ko/en i18n 자연스러움 + 바둑 용어 일관성 (sonnet)
- **`a11y-auditor`** — axe + 키보드 흐름 + 대비 (sonnet)

Phase 2/3의 독립적 화면은 `editorial-implementer`를 병렬 호출해 동시 작업. 구현 완료 후 `design-token-guardian` + `visual-qa`로 일괄 리뷰.

## Environment

Backend reads from `backend/.env` (see `.env.example`). Root `.env` is consumed by `docker-compose.yml` and passed to the backend container. Key vars: `KATAGO_MOCK` (skip model download — use for all dev and tests), `JWT_SECRET` (must be strong in prod), `DB_PATH`, `KATAGO_*` paths, `CORS_ORIGINS`.

## Reference

- `docs/QUALITY_REPORT.md` — outstanding security/quality items from the 5-agent review (referenced by README's Production Checklist; consult before shipping changes in those areas).
- `docs/superpowers/specs/` and `docs/superpowers/plans/` — original design spec and implementation plan.
- `CHANGELOG.md` — versioned history. 0.2.0 added 9×9/13×13 board sizes; time controls, user-vs-user, OAuth still deferred.
