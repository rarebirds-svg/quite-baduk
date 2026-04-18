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

## Environment

Backend reads from `backend/.env` (see `.env.example`). Root `.env` is consumed by `docker-compose.yml` and passed to the backend container. Key vars: `KATAGO_MOCK` (skip model download — use for all dev and tests), `JWT_SECRET` (must be strong in prod), `DB_PATH`, `KATAGO_*` paths, `CORS_ORIGINS`.

## Reference

- `docs/QUALITY_REPORT.md` — outstanding security/quality items from the 5-agent review (referenced by README's Production Checklist; consult before shipping changes in those areas).
- `docs/superpowers/specs/` and `docs/superpowers/plans/` — original design spec and implementation plan.
- `CHANGELOG.md` — versioned history. 0.2.0 added 9×9/13×13 board sizes; time controls, user-vs-user, OAuth still deferred.
