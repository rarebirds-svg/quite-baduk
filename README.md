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

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- ~2 GB of disk space for the Docker images + KataGo model

## Quick Start

```bash
git clone <your-fork> baduk && cd baduk
cp .env.example .env
# For development without downloading the KataGo model:
echo "KATAGO_MOCK=true" >> .env

docker-compose up --build
```

On macOS, you can use the included launcher script instead — it auto-starts Docker Desktop if needed, bootstraps `.env`, waits for the stack to be healthy, and opens your browser:

```bash
./start.sh   # bring the stack up
./stop.sh    # bring the stack down
```

First boot downloads the KataGo binary (~10 MB) and the Human-SL model (~200 MB) unless `KATAGO_MOCK=true`.

### Access

| Service  | URL                      |
|----------|--------------------------|
| Frontend | http://localhost:3000    |
| API      | http://localhost:8000    |
| Health   | http://localhost:8000/api/health |

### First Game

1. Visit http://localhost:3000/signup and create an account
2. Go to **새 대국 / New Game** — pick your rank and handicap
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

Backend-only env vars (configure inside the backend container):

| Variable              | Default                                             |
|-----------------------|-----------------------------------------------------|
| `DB_PATH`             | `/data/baduk.db`                                    |
| `KATAGO_BIN_PATH`     | `/usr/local/bin/katago`                             |
| `KATAGO_MODEL_PATH`   | `/katago/models/b18c384nbt-humanv0.bin.gz`          |
| `KATAGO_CONFIG_PATH`  | `/katago/config.cfg`                                |
| `KATAGO_TIMEOUT_SEC`  | `60`                                                |

## Backup & Restore

The `backup` service in `docker-compose.yml` writes a dated copy of the SQLite DB to the `baduk_backups` volume every 24 hours and prunes files older than 30 days.

**Manual backup:**

```bash
docker-compose exec backend sqlite3 /data/baduk.db ".backup '/backups/manual.db'"
```

**Restore:**

```bash
docker-compose stop backend
docker cp <backup.db> $(docker-compose ps -q backend):/data/baduk.db
docker-compose start backend
```

## Development

### Local backend (no Docker)

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

# End-to-end (requires running docker-compose)
cd e2e && npm install && npm run install-browsers && npm test
```

## Troubleshooting

**KataGo model download fails**
Set `KATAGO_MOCK=true` in `.env` and rebuild. The mock adapter plays deterministic moves, enough to exercise the UI.

**Port conflicts**
Edit `docker-compose.yml` port mappings, e.g. `"3001:3000"` and `"8001:8000"`.

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
- [ ] Ensure the `backup` service is scheduled or swap for off-host backup storage
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
└── docker-compose.yml
```

## License

MIT
