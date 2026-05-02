# Start/Stop Scripts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `start.sh` and `stop.sh` at the project root so a single command brings the Docker stack up (with `.env` bootstrap, health wait, browser open, log tail) or down.

**Architecture:** Two thin POSIX-`sh` wrappers around `docker compose`. No new runtime dependencies. macOS-only (uses `open` for browser). `start.sh` is the only one with any logic; `stop.sh` is a one-liner.

**Tech Stack:** Bash, `docker compose` (v2), `curl`, macOS `open`.

---

## File Structure

- Create: `start.sh` — bring stack up, wait for health, open browser, tail logs.
- Create: `stop.sh` — bring stack down.

Both at project root, both `chmod +x`. No tests (consistent with the existing `backup.sh` at the root, which also has none).

---

## Task 1: stop.sh

**Files:**
- Create: `stop.sh`

- [ ] **Step 1: Write the script**

`stop.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
docker compose down
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x stop.sh`
Verify: `ls -l stop.sh` shows `-rwxr-xr-x`.

- [ ] **Step 3: Smoke test**

Pre-req: stack is up (`docker compose ps` shows running containers). If not, start it manually first with `docker compose up -d`.

Run: `./stop.sh`
Expected: containers stop and are removed; `docker compose ps` shows nothing for this project.

- [ ] **Step 4: Commit**

```bash
git add stop.sh
git commit -m "feat: add stop.sh to bring docker stack down"
```

---

## Task 2: start.sh

**Files:**
- Create: `start.sh`

- [ ] **Step 1: Write the script**

`start.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# 1. Docker daemon check
if ! docker info >/dev/null 2>&1; then
  echo "Docker Desktop이 실행 중이 아닙니다. Docker Desktop을 먼저 실행해 주세요." >&2
  exit 1
fi

# 2. .env bootstrap
if [ ! -f .env ]; then
  cp .env.example .env
  echo ".env 파일이 없어서 .env.example로부터 생성했습니다."
fi

# 3. Compose up
echo "Docker 스택을 빌드하고 띄웁니다..."
docker compose up --build -d

# 4. Health wait (max 60s)
echo -n "스택 준비를 기다리는 중"
ready=0
for i in $(seq 1 60); do
  if curl -fs http://localhost:8000/health >/dev/null 2>&1 \
     && curl -fs http://localhost:3000 >/dev/null 2>&1; then
    ready=1
    break
  fi
  echo -n "."
  sleep 1
done
echo

if [ "$ready" -ne 1 ]; then
  echo "스택이 60초 안에 준비되지 않았습니다. 'docker compose logs'로 확인하세요." >&2
  exit 1
fi

echo "준비 완료. 브라우저를 엽니다: http://localhost:3000"

# 5. Browser open (macOS)
open http://localhost:3000 || true

# 6. Tail logs (Ctrl+C exits the tail, containers keep running; use ./stop.sh to stop)
echo "로그를 따라갑니다. Ctrl+C로 빠져나와도 컨테이너는 계속 실행됩니다. 종료는 ./stop.sh"
exec docker compose logs -f
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x start.sh`
Verify: `ls -l start.sh` shows `-rwxr-xr-x`.

- [ ] **Step 3: Smoke test — happy path**

Pre-req: Docker Desktop is running; stack is currently down (`./stop.sh` first if needed).

Run: `./start.sh`
Expected:
- "Docker 스택을 빌드하고 띄웁니다..." printed
- compose build/start output
- "스택 준비를 기다리는 중....." (some dots)
- "준비 완료. 브라우저를 엽니다: http://localhost:3000"
- Default browser opens to localhost:3000
- `docker compose logs -f` starts streaming
- Ctrl+C returns to shell; `docker compose ps` shows containers still running.

Then `./stop.sh` to clean up.

- [ ] **Step 4: Smoke test — Docker not running**

Pre-req: Quit Docker Desktop.

Run: `./start.sh`
Expected: "Docker Desktop이 실행 중이 아닙니다. Docker Desktop을 먼저 실행해 주세요." printed to stderr; exit code 1 (`echo $?` shows 1).

Restart Docker Desktop afterwards.

- [ ] **Step 5: Smoke test — idempotent**

Pre-req: Stack already running from a previous `./start.sh`.

Run: `./start.sh`
Expected: compose detects no changes, health wait passes near-instantly, browser opens, logs tail. No errors.

Then `./stop.sh` to clean up.

- [ ] **Step 6: Commit**

```bash
git add start.sh
git commit -m "feat: add start.sh to launch docker stack with health wait and browser open"
```

---

## Task 3: README pointer

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Find the existing dev/setup section**

Run: `grep -n -E "docker compose up|docker-compose up|getting started|시작하기" README.md`

Identify a near-the-top section that mentions running the stack (e.g. "Quick start" or equivalent). Note the line number.

- [ ] **Step 2: Add a one-liner**

Add a short note in that section pointing to `./start.sh` as the convenience entrypoint and `./stop.sh` to stop. Keep it 1–2 sentences. Match the existing language (Korean if surrounding text is Korean, English otherwise).

Example phrasing (Korean): "macOS에서는 `./start.sh` 한 줄로 스택을 빌드·실행하고 브라우저까지 열 수 있습니다. 종료는 `./stop.sh`."

Do not remove or rewrite the existing `docker compose up --build` instructions — `start.sh` is an addition, not a replacement.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: mention start.sh / stop.sh in README"
```

---

## Self-Review

- **Spec coverage:** All six `start.sh` behaviors (Docker check, .env bootstrap, compose up, health wait, browser open, log tail) → Task 2 Step 1. `stop.sh` → Task 1. Smoke tests cover the three test scenarios in the spec (fresh clone substituted for "happy path"; Docker quit; idempotent).
- **Out-of-scope items honored:** No flags, no Linux/Windows branching, no port preflight, no backup-sidecar healthcheck.
- **Placeholders:** None. Every step has concrete code or commands.
- **Commit cadence:** One commit per script + one for README. Frequent and small.
