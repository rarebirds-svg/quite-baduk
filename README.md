# AI 바둑 (AI Go)

Play the game of Go (Baduk) against the **KataGo** AI in your browser.
Rank selection from **18k to 7d** (Human-SL model), handicap games **2–9 stones**, Korean rules territory scoring, SGF export, hint, undo, review + analysis, per-user history, Korean/English UI with dark mode.

![stack: Next.js + FastAPI + SQLite + KataGo](https://img.shields.io/badge/stack-Next.js%20%2B%20FastAPI%20%2B%20KataGo-blue)

## Features

- 🎯 **Rank picker** — 12 preset strength levels from 18-kyu (beginner) to 7-dan (strong amateur)
- 🪨 **Handicap games** — standard Korean handicap positions (2 to 9 stones)
- 🧠 **KataGo Human-SL model** — AI plays *like a human* at the chosen rank, not just weaker
- 📋 **SGF import/export** — download your games, load any SGF
- 🔁 **Undo** — take back the last two plies (your move + AI response)
- 💡 **Hint** — ask KataGo for the top-3 recommended moves with winrate
- 🔬 **Review + analysis** — replay any finished game move by move with winrate overlay
- 📊 **Personal stats** — win/loss by rank and handicap
- 🌐 **i18n** — Korean and English, instant switching
- 🌗 **Dark mode**
- 🔒 **Sessions** — ephemeral nickname-only login. Opaque random session token in an HttpOnly cookie; idle TTL 1 hour. No email, no password, no PII.

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
# Backend (170 tests, Rules Engine 100% coverage)
cd backend && source .venv311/bin/activate && pytest

# Frontend (Vitest)
cd web && npm run test -- --run

# End-to-end (boots its own native stack on alt ports — see e2e/README.md)
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
├── web/                  Next.js 14 (App Router, TS, Tailwind)
├── e2e/                  Playwright end-to-end tests
├── docs/
│   ├── superpowers/
│   │   ├── specs/        Design spec
│   │   └── plans/        Implementation plan
│   ├── reviews/          Individual review-agent reports
│   └── QUALITY_REPORT.md
├── start.sh / stop.sh   Native dev stack bootstrap
└── ops/                 launchd plists, backup, runbooks, agentic state
```

## License

MIT
