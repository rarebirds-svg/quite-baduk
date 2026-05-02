# Start/Stop Scripts — Design

**Date:** 2026-05-02
**Topic:** Dev-stack launcher scripts at the project root.

## Goal

One-command launch and shutdown of the full Docker stack (backend, web, backup sidecar) for everyday development on macOS. Replace the multi-step "open Docker Desktop → cd to repo → docker compose up --build → wait → open browser" ritual with `./start.sh`.

## Files

- `start.sh` — bring the stack up, wait for health, open browser, then tail logs.
- `stop.sh` — bring the stack down.

Both at project root, executable (`chmod +x`).

## Behavior — `start.sh`

1. **Docker daemon check.** Run `docker info >/dev/null 2>&1`. If non-zero exit, print
   `Docker Desktop이 실행 중이 아닙니다. Docker Desktop을 먼저 실행해 주세요.` and exit 1.
2. **`.env` bootstrap.** If `./.env` is missing, copy `./.env.example` to `./.env` and print a notice. Do not overwrite an existing `.env`.
3. **Compose up.** `docker compose up --build -d` (v2 syntax — matches CI per commit `61abdab`).
4. **Health wait.** Poll once per second, up to 60 seconds total:
   - Backend ready when `curl -fs http://localhost:8000/api/health` exits 0.
   - Web ready when `curl -fs http://localhost:3000` exits 0 (any 2xx/3xx is fine — a 200 from the Next.js root or a redirect both count).
   - Print a single-line progress indicator (e.g. `Waiting for stack… 3s`).
   - On timeout, print `스택이 60초 안에 준비되지 않았습니다. 'docker compose logs'로 확인하세요.` and exit 1 (containers stay up so the user can inspect).
5. **Browser open.** `open http://localhost:3000` (macOS).
6. **Tail logs.** `exec docker compose logs -f`. Ctrl+C exits the tail; containers keep running. The user stops the stack with `./stop.sh`.

## Behavior — `stop.sh`

1. `docker compose down`. No flags (volumes preserved — SQLite DB and KataGo cache survive).

## Out of scope

- Linux / Windows portability. macOS only (matches the user's platform).
- `--no-build`, `--detach-only`, `--no-browser` flags. Add later if asked.
- Healthcheck for the backup sidecar.
- Preflight checks for ports 3000/8000 already in use — Docker will surface that error itself.

## Testing

Manual on macOS:

1. Fresh clone (no `.env`) → `./start.sh` should create `.env`, build, wait, open browser, tail logs.
2. Stack already running → `./start.sh` should be idempotent (compose handles this).
3. Docker Desktop quit → `./start.sh` should exit 1 with the Korean notice.
4. `./stop.sh` brings everything down; `docker ps` shows no baduk-* containers.

No automated tests — these are thin shell wrappers around `docker compose`.
