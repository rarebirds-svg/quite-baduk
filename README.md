# AI 바둑 (AI Go)

Play the game of Go (Baduk) against the **KataGo** AI in your browser — then learn from it. Rank
selection from **18k to 7d** (Human-SL model), handicap games, Korean-rules scoring, hint, undo,
review + analysis, plus a public learning layer: **911 professional game records**, **420 daily
puzzles**, a Go **glossary** and **FAQ**, and live **spectating** — all browsable without an account.

[![version](https://img.shields.io/badge/version-0.3.0-8b2e2e)](https://github.com/rarebirds-svg/quite-baduk/releases/tag/v0.3.0)
![stack: Next.js + FastAPI + SQLite + KataGo](https://img.shields.io/badge/stack-Next.js%20%2B%20FastAPI%20%2B%20KataGo-blue)

## Features

### Play

- 🎯 **Rank picker** — 12 preset strength levels from 18-kyu (beginner) to 7-dan (strong amateur)
- 📐 **Board sizes** — 9×9, 13×13, 19×19
- 🪨 **Handicap games** — standard Korean handicap positions (2 to 9 stones)
- 🧠 **KataGo Human-SL model** — AI plays *like a human* at the chosen rank, not just weaker
- 📋 **SGF export** — download any of your games
- 🔁 **Undo** — take back the last two plies (your move + AI response)
- 💡 **Hint** — ask KataGo for the top-3 recommended moves with winrate
- 🔬 **Review + analysis** — replay any finished game move by move with winrate / ownership overlay
- 📊 **Personal stats** — win/loss by rank and handicap

### Learn & browse (no login required)

- ♟️ **Pro game library** — 911 SGF records across two collections (625 masterpieces, 286 world-final
  games), with per-game analysis, themed collections, and a monthly "masterpiece" pick
- 🧩 **Daily challenge** — 420 GoGameGuru puzzles; a deterministic daily pick plus a random mode
- 📖 **Glossary** — Go terms with markdown articles, board diagrams, and images
- ❓ **FAQ** — how AI ranks work, Korean vs Japanese rules, review/analysis usage, and more
- 👀 **Spectate** — watch in-progress AI games and replay finished ones, indexed for SEO (sitemap)

### Platform

- 🌐 **i18n** — Korean and English, instant switching
- 🌗 **Dark mode** — `next-themes`, class-based, full token coverage
- 🎨 **Editorial design system** — "Editorial Hardcover" tokens (paper/ink/oxblood/gold/moss),
  serif + sans + mono typography, shadcn-based UI primitives
- 🔒 **Sessions** — ephemeral nickname-only login. Opaque random session token in an HttpOnly cookie;
  idle TTL 1 hour. No email, no password, no PII.
- 🛠️ **Admin console** — sessions, login history, stats, and pro-game uploads
- ⚙️ **Autonomous ops** — launchd-scheduled agents for backups, content drafting, pro-game ingest,
  health watchdog, and an orchestrator (see [Operations](#operations))

## Architecture

```
┌─ Next.js 14 (React) ──────┐      HTTPS REST + WebSocket
│  SVG board, i18n, theme   │────────────────┐
└───────────────────────────┘                │
                                             ▼
┌─ FastAPI (Python 3.11) ──────────────────────────┐
│  Auth · Games · Analysis · WS                    │
│  Rules Engine (pure) · KataGo Adapter (async)    │
└─────────────────────────────────────────────────┘
       │                               │ stdin/stdout (GTP)
       ▼                               ▼
┌─ SQLite (WAL) ─┐          ┌─ KataGo binary ─┐
│ baduk.db        │          │ b18c384nbt-     │
│ + backups/       │          │   humanv0 model │
└────────────────┘          └────────────────┘
```

- **Rules engine** (`backend/app/core/rules/`): pure-Python implementation of Go rules, 100% test coverage
- **KataGo adapter** (`backend/app/core/katago/`): async subprocess with GTP protocol, auto-restart, state replay
- **Mock mode**: set `KATAGO_MOCK=true` to run without the KataGo binary (for local dev / tests)

### Screens

| Route | Login | Purpose |
|-------|-------|---------|
| `/` | — | Landing page |
| `/game/new` · `/game/play/[id]` · `/game/review/[id]` | ✓ | Create, play, review a game |
| `/history` · `/settings` | ✓ | Personal game history, profile settings |
| `/daily` | ✓ | Daily + random puzzle challenges |
| `/spectate` · `/spectate/[id]` | — | Browse / watch in-progress & finished AI games |
| `/spectate/pro` · `/spectate/pro/[id]` | — | Pro game library + per-game detail (SEO) |
| `/spectate/themes/[slug]` · `/spectate/picks` · `/spectate/picks/monthly/[yyyymm]` | — | Themed collections, monthly masterpiece pick |
| `/glossary` · `/glossary/[slug]` | — | Go glossary index + articles |
| `/faq` · `/faq/[slug]` | — | FAQ index + articles |
| `/privacy` · `/terms` · `/support` · `/supporters` | — | Public info pages |
| `/admin/*` | ✓ (admin) | Sessions, login history, stats, pro-game management |

### API surface

Public (no auth): `GET /api/health`, `GET /api/spectate`, `GET /api/spectate/{id}`,
`GET /api/spectate/pro[...]` (list, detail, themes, monthly pick, sitemap).
Session: `POST/GET/DELETE /api/session`, `GET/POST /api/games[...]` (+ `hint`, `analyze`, `sgf`,
`resign`), `WS /api/ws/games/{id}`, `GET /api/stats`, `GET/POST /api/daily[...]`.
Admin: `GET /api/admin/*` (summary, engine, sessions, games, login-history) and `/api/admin/pro-games`
(upload/list/delete).

## Prerequisites

- Python 3.11 and Node.js 20+
- ~250 MB of disk space for the KataGo binary + Human-SL model (skipped when `KATAGO_MOCK=true`)

## Quick Start

```bash
git clone <your-fork> baduk && cd baduk
cp backend/.env.example backend/.env
# For development without downloading the KataGo model:
echo "KATAGO_MOCK=true" >> backend/.env

./start.sh   # bring the native dev stack up (backend :8000 + web :3000)
./stop.sh    # bring it down
```

`start.sh` boots backend (uvicorn from `backend/.venv311`) and web (`npm run dev`) as background processes. PIDs live in `.run/`. First boot downloads KataGo (~10 MB) and the Human-SL model (~200 MB) unless `KATAGO_MOCK=true`.

For prod (launchd on macOS), see `backend/deploy/README.md`.

### Access

| Service  | URL                      |
|----------|--------------------------|
| Frontend | http://localhost:3000    |
| API      | http://localhost:8000    |
| Health   | http://localhost:8000/api/health |

### First Game

1. Visit http://localhost:3000 — enter a nickname (2–32 chars, no email/password)
2. On **새 대국 / New Game** — pick your rank, board size, handicap, AI opponent
3. Click the board to place stones
4. Use **힌트 / Hint** to ask KataGo for suggestions
5. After the game ends, find it under **전적 / History** and click **Review** to replay with analysis

## Environment Variables

Copy `.env.example` → `.env` and override as needed.

| Variable        | Default                             | Description                                                 |
|-----------------|-------------------------------------|-------------------------------------------------------------|
| `APP_ENV`       | `development`                       | Set to `production` to enable Secure cookies + HSTS header. |
| `JWT_SECRET`    | `changeme-in-production`            | Reserved for future signed-cookie support. Currently unused (sessions use opaque random tokens stored in DB). Keep it set anyway. |
| `KATAGO_MOCK`   | `false`                             | `true` skips model download and uses a deterministic mock.  |
| `CORS_ORIGINS`  | `http://localhost:3000`             | Comma-separated allowed origins.                            |
| `KATAGO_ANALYZE_MAX_DEADLINE_SEC` | `15`               | Wall-clock budget for one `kata-analyze` call. Lower on fast CPUs.|

Backend-only env vars (set in `backend/.env` or `~/.baduk.env` for prod launchd):

| Variable              | Default                                                |
|-----------------------|--------------------------------------------------------|
| `DATABASE_URL`        | `sqlite+aiosqlite:///./data/baduk.db`                  |
| `KATAGO_BIN_PATH`     | `backend/katago/bin/katago`                            |
| `KATAGO_MODEL_PATH`   | `backend/katago/models/b18c384nbt-humanv0.bin.gz`      |
| `KATAGO_CONFIG_PATH`  | `backend/katago/config.cfg`                            |
| `KATAGO_TIMEOUT_SEC`  | `60`                                                   |

## Backup & Restore

Prod uses a launchd backup job (`com.inkbaduk.backup`) running `ops/backup.sh` daily. Snapshots land in `~/baduk-backups/{daily,weekly,monthly}/` with retention.

**Manual backup:**

```bash
sqlite3 backend/data/baduk.db ".backup '/tmp/baduk-manual.db'"
```

**Restore:**

```bash
launchctl bootout gui/$(id -u)/com.baduk.api
cp <backup.db> backend/data/baduk.db
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.baduk.api.plist
```

## Operations

Prod runs as macOS **launchd** agents directly from the repo work tree (no Docker): `com.baduk.api`
(uvicorn :8000) and `com.baduk.web` (`npm start` :3000). Alongside the app, a set of autonomous
agents run on schedules — plists in `ops/launchd/`, runner scripts in `ops/`, runbooks and state in
`docs/ops/`.

| Agent | Schedule | Role |
|-------|----------|------|
| `com.inkbaduk.backup` | daily | Multi-generation SQLite backups (daily/weekly/monthly) |
| `com.inkbaduk.ops-watchdog` | hourly | Staleness + KataGo/DB health checks, auto-recovery |
| `com.inkbaduk.ops-orchestrator` | 12:00 / 18:00 | Headless Claude Code — status reports, PR watch |
| `com.inkbaduk.dev-cycle` | 02:00 | Autonomous bug-fix cycle (commits a branch; human pushes/PRs) |
| `com.inkbaduk.content-draft` | Sat/Wed 02:00 | Drafts & publishes glossary/FAQ content |
| `com.inkbaduk.content-ingest` | Sun 03:00 | Ingests public-domain pro game records |
| `com.inkbaduk.analytics-weekly` | Sun 09:00 | Weekly analytics report |

The hardening work (single-node machine-restart recovery, hung-process auto-correction) and a
Cloudflare Workers **external health monitor** live under `ops/cloudflare/health-monitor/`. See
`docs/ops/` for autonomy policy and runbooks.

## Development

### Local backend

```bash
cd backend
python3.11 -m venv .venv311 && source .venv311/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # set KATAGO_MOCK=true
uvicorn app.main:app --reload
```

### Local frontend

```bash
cd web
npm install
npm run dev
```

### Tests

```bash
# Backend (~499 tests, Rules Engine 100% coverage)
cd backend && source .venv311/bin/activate && pytest

# Frontend (Vitest — ~136 tests)
cd web && npm run test -- --run

# End-to-end (9 Playwright scenarios; boots its own native stack on alt ports — see e2e/README.md)
# NOTE: the e2e job is currently disabled in CI pending a rewrite for the nickname-only flow.
BADUK_API_PORT=18000 BADUK_WEB_PORT=13000 bash e2e/scripts/start-stack.sh
PLAYWRIGHT_BASE_URL=http://localhost:13000 npx --prefix e2e playwright test
bash e2e/scripts/stop-stack.sh
```

## Troubleshooting

**KataGo model download fails**
Set `KATAGO_MOCK=true` in `.env` and rebuild. The mock adapter plays deterministic moves, enough to exercise the UI.

**Port conflicts**
Pass `BADUK_API_PORT` / `BADUK_WEB_PORT` to `start.sh` or `e2e/scripts/start-stack.sh` to bind alt ports.

**"SESSION_REPLACED" error**
You opened the same game in another tab or window. The backend enforces a single WebSocket per game to keep state consistent.

**KataGo CPU usage / slow response**
Higher ranks (5d/7d) use more visits (256/512) and take longer per move. For CPU-only hardware, use 18k–3k for responsive play.

## Production Checklist

Before deploying publicly:

- [ ] Set `APP_ENV=production`. This auto-enables `Secure` cookies and `Strict-Transport-Security`.
- [ ] Put an HTTPS-terminating reverse proxy (Caddy, Nginx, Cloudflare Tunnel) in front. The backend's built-in `SecurityHeadersMiddleware` adds the baseline (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, HSTS); a CSP / Permissions-Policy is best layered at the proxy.
- [ ] Update `CORS_ORIGINS` to your production domain
- [ ] Replace placeholder support address in `web/app/privacy/page.tsx` and `web/app/terms/page.tsx`
- [ ] Run `bandit`, `pip-audit`, `npm audit` in CI and fix any `high` findings
- [ ] Ensure the launchd backup job (`com.inkbaduk.backup`) is loaded or swap for off-host backup storage
- [ ] Replace placeholder PWA icons under `web/public/icons/` with branded artwork (see icons/README.md)

## Quality Report

A full audit from five specialized review agents (Rules, KataGo, API, Frontend, Security) lives at [docs/QUALITY_REPORT.md](docs/QUALITY_REPORT.md).

## Project Layout

```
baduk/
├── backend/              FastAPI + Rules Engine + KataGo adapter
│   └── data/
│       ├── pro_games/    SGF library (masterpieces, world_finals)
│       └── gogameguru/   Daily-challenge puzzle SGFs
├── web/                  Next.js 14 (App Router, TS, Tailwind)
│   ├── components/
│   │   ├── ui/           shadcn primitives (Editorial-themed)
│   │   └── editorial/    Custom primitives + Go domain icons
│   └── content/          Glossary + FAQ markdown articles
├── e2e/                  Playwright end-to-end tests
├── docs/
│   ├── superpowers/
│   │   ├── specs/        Design spec
│   │   └── plans/        Implementation plan
│   ├── ops/             Autonomy policy, runbooks, agentic state
│   ├── reviews/          Individual review-agent reports
│   └── QUALITY_REPORT.md
├── start.sh / stop.sh   Native dev stack bootstrap
└── ops/
    ├── launchd/         launchd plists for scheduled agents
    ├── cloudflare/      External health monitor (Workers)
    └── *.sh            backup, watchdog, orchestrator, content runners
```

## License

MIT
