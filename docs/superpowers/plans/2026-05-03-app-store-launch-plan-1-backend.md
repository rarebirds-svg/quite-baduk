# App Store Launch — Plan 1: Backend Infra & Quality

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the single-adapter KataGo stack into a 4-worker Metal-accelerated pool, deploy it on Mac mini M4 behind Cloudflare Tunnel as `https://api.<domain>`, harden the remaining backend P0/P1 quality items from `docs/reviews/2026-05-03-pre-launch-qa-baseline.md`, and leave the door open for the Capacitor mobile shell (Plan 2).

**Architecture:** Replace `engine_pool._adapter: KataGoAdapter` with `_pool: KataGoPool`. The pool is a fixed-size list of independently running KataGo subprocesses; `KataGoPool.adapter_for(game_id)` returns a sticky-pinned adapter via least-loaded assignment. Per-game `asyncio.Lock` semantics in `engine_pool.game_lock` are unchanged. Deployment moves out of Docker and runs natively under launchd; public reachability is provided by `cloudflared` (no inbound port required). SQLite WAL stays — no schema migration beyond an FK index Alembic revision.

**Tech Stack:** Python 3.11 + FastAPI + SQLAlchemy 2 async + Alembic (backend); KataGo v1.15.3 built from source with `-DUSE_BACKEND=METAL` (engine); cloudflared (tunnel); launchd (process supervisor); rclone or `aws s3 cp` (R2 backup).

---

## Day 0 Prerequisites

These must be true before Task 1. They're tracked in **Plan 3**, not here, but executing this plan without them blocks at Task D2.

- A domain is registered (e.g. `aibaduk.app`) and its nameservers point at Cloudflare. The exact subdomain `api.<domain>` is reserved for this work.
- The user has shell access to the target Mac mini M4 with Xcode CLI tools installed (`xcode-select --install`).
- Homebrew is installed and the user can run `brew install`.
- The repo is checked out at `~/projects/baduk` (or equivalent path that the launchd plist can hard-code).

If any of the above is missing, halt and resolve in Plan 3 first.

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `backend/katago/build_macos.sh` | Create | One-shot script: `git clone KataGo`, `cmake -DUSE_BACKEND=METAL`, install binary into `backend/katago/bin/katago` |
| `backend/katago/README.md` | Modify | Document Metal vs Eigen build paths + tune cache location |
| `backend/app/core/katago/pool.py` | Create | `KataGoPool` — fixed-size pool, sticky game-to-adapter assignment, parallel start/stop |
| `backend/tests/katago/test_pool.py` | Create | Unit tests for pool: assignment, least-loaded balancing, release, concurrent start |
| `backend/app/engine_pool.py` | Modify | Replace `_adapter` with `_pool: KataGoPool`; `get_adapter(game_id)` resolves through pool; legacy `get_adapter()` (no arg) preserved for callsites that don't need pinning |
| `backend/app/services/game_service.py` | Modify | Switch `get_adapter()` calls to `get_adapter(game.id)`; release pool slot on game finalize |
| `backend/app/api/ws.py` | Modify | Same — pinned adapter via `get_adapter(game_id)` |
| `backend/app/api/games.py` | Modify | Pinned adapter |
| `backend/app/api/analysis.py` | Modify | Pinned adapter |
| `backend/app/core/katago/strength.py` | Modify | Cap `max_visits` to 256, drop 7d/6d entries from public table |
| `web/lib/i18n/ko.json`, `en.json` | Modify | Remove 7d/6d from rank picker labels (see Plan 2 for selector UI; backend silently rejects them via `INVALID_AI_RANK`) |
| `backend/app/main.py` | Modify | Lifespan starts the pool, stops on shutdown |
| `backend/tests/api/test_concurrent_games.py` | Create | Integration test: two games on the pool make moves concurrently and don't share state |
| `backend/app/errors.py` | Modify | `GameError.detail` flows into the HTTP response body (P1-1) |
| `backend/tests/api/test_error_response.py` | Create | Asserts `{"code": ..., "detail": ...}` shape |
| `backend/app/services/analysis_service.py` | Modify | `/analyze?moveNum=N` re-plays to N before analysis (P1-2) |
| `backend/tests/api/test_analysis_movenum.py` | Create | Asserts moveNum N gives different output than moveNum N+5 |
| `backend/migrations/versions/0003_fk_indexes.py` | Create | Alembic revision adding indexes on `moves.game_id`, `analyses.game_id`, `session_history.session_id` (P1-7) |
| `backend/app/schemas/game.py` | Modify | Pydantic `Field(ge=…, le=…)` constraints on `moveNum`, `page`, etc. (P1-9) |
| `backend/app/config.py` | Modify | `cors_origins.split` whitespace-tolerant; `cookie_samesite: str` setting; `katago_pool_size: int = 4` |
| `backend/tests/conftest.py` | Modify | Fixture teardown order — `db_session` closes before `db_engine.dispose()` (cleans up aiosqlite teardown race) |
| `backend/app/api/ws.py` | Modify | WS handoff race fix (P0-10): atomic swap on `_connections[game_id]` under a per-key asyncio.Lock |
| `backend/app/api/ws.py` | Modify | Heartbeat: server pings every 30s, validates session row still exists, closes with code `SESSION_EXPIRED` if not (P0-12) |
| `backend/tests/api/test_ws_lifecycle.py` | Create | Heartbeat + session-expiry close tests |
| `backend/deploy/com.baduk.api.plist` | Create | launchd service definition |
| `backend/deploy/cloudflared.yml` | Create | Tunnel routing config |
| `backend/deploy/run_local_prod.sh` | Create | Wrapper script launchd invokes (activates venv, sets env, exec uvicorn) |
| `backend/deploy/r2_backup.sh` | Create | Daily backup → Cloudflare R2 with rclone |
| `backend/deploy/README.md` | Create | Production setup runbook |

---

## Phase A — KataGo Metal pool

### Task A1: Build KataGo Metal binary on Mac mini

**Files:**
- Create: `backend/katago/build_macos.sh`
- Modify: `backend/katago/README.md`

This task is a runbook (no Python code). It produces a working `backend/katago/bin/katago` binary that uses the M4 GPU via Apple's Metal framework. The output binary is per-host — do not commit it.

- [ ] **Step 1: Install build prerequisites**

```bash
brew install cmake libzip eigen
xcode-select --install || true
```

Expected: `brew list cmake libzip eigen` shows all three.

- [ ] **Step 2: Create `backend/katago/build_macos.sh`**

```bash
#!/usr/bin/env bash
# Build KataGo with Metal backend on Apple Silicon. Idempotent: checks
# out a fresh clone into `vendor/KataGo` if missing, then re-runs cmake
# only when the build/ directory is absent.
set -euo pipefail

KATAGO_VERSION="v1.15.3"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR="${SCRIPT_DIR}/vendor"
SRC="${VENDOR}/KataGo"
BIN_OUT="${SCRIPT_DIR}/bin/katago"

mkdir -p "${VENDOR}" "${SCRIPT_DIR}/bin"

if [ ! -d "${SRC}" ]; then
  git clone --depth 1 --branch "${KATAGO_VERSION}" \
    https://github.com/lightvector/KataGo.git "${SRC}"
fi

cd "${SRC}/cpp"
if [ ! -d build ]; then
  mkdir build
fi
cd build
cmake -DUSE_BACKEND=METAL -DCMAKE_BUILD_TYPE=Release ..
cmake --build . --parallel "$(sysctl -n hw.ncpu)"

cp katago "${BIN_OUT}"
echo "OK: built ${BIN_OUT}"
"${BIN_OUT}" version
```

- [ ] **Step 3: Make it executable and run**

```bash
chmod +x backend/katago/build_macos.sh
./backend/katago/build_macos.sh
```

Expected: ends with `KataGo Version v1.15.3` line printed by `katago version`.

If Metal build fails (e.g. cmake error about Metal framework), fall back to Eigen:

```bash
# In build_macos.sh, change USE_BACKEND from METAL to EIGEN. Slower
# (CPU only) but guarantees a binary so you can keep moving.
```

- [ ] **Step 4: Run a 30-second benchmark to seed the GPU tune cache**

```bash
./backend/katago/bin/katago benchmark \
  -model backend/katago/models/b18c384nbt-humanv0.bin.gz \
  -t 30
```

Expected: roughly 200–400 visits/second on M4 GPU. First run may sit silent for ~60s tuning — that is normal and only happens once. Tune cache lives at `~/.katago/`.

- [ ] **Step 5: Update `backend/katago/README.md`**

Add a section at the top:

```markdown
## Apple Silicon (M-series) production build

```bash
./build_macos.sh
```

Produces `bin/katago` linked against Metal. First start performs a
GPU benchmark/tune (60–120s, cached at `~/.katago/`). Subsequent
starts are instant.

If the Metal build fails on your Xcode toolchain (cmake error about
the Metal framework), switch `USE_BACKEND=METAL` to `USE_BACKEND=EIGEN`
in the script. Eigen is CPU-only — about 30× slower — but unblocks
testing. Production must be on Metal.
```

- [ ] **Step 6: Commit**

```bash
git add backend/katago/build_macos.sh backend/katago/README.md
git commit -m "feat(katago): macOS Metal build script + benchmark step"
```

---

### Task A2: Implement `KataGoPool` with unit tests

**Files:**
- Create: `backend/app/core/katago/pool.py`
- Test: `backend/tests/katago/test_pool.py`

- [ ] **Step 1: Write the failing test — pool creation and size**

Create `backend/tests/katago/test_pool.py`:

```python
"""Unit tests for KataGoPool. We inject MockKataGoAdapter via the
``adapter_factory`` parameter so no real KataGo subprocess is spawned."""
from __future__ import annotations

import pytest

from app.core.katago.mock import MockKataGoAdapter
from app.core.katago.pool import KataGoPool


def _mock_pool(size: int = 4) -> KataGoPool:
    return KataGoPool(size=size, adapter_factory=MockKataGoAdapter)


def test_pool_size_matches_constructor_argument() -> None:
    pool = _mock_pool(size=4)
    assert pool.size == 4


def test_pool_rejects_zero_or_negative_size() -> None:
    with pytest.raises(ValueError):
        KataGoPool(size=0, adapter_factory=MockKataGoAdapter)
    with pytest.raises(ValueError):
        KataGoPool(size=-1, adapter_factory=MockKataGoAdapter)
```

- [ ] **Step 2: Run the test, confirm it fails**

```bash
cd backend && source .venv311/bin/activate
KATAGO_MOCK=true pytest tests/katago/test_pool.py -v
```

Expected: `ImportError: cannot import name 'KataGoPool' from 'app.core.katago.pool'`.

- [ ] **Step 3: Implement the pool — file scaffold**

Create `backend/app/core/katago/pool.py`:

```python
"""Pool of :class:`KataGoAdapter` subprocesses for concurrent game serving.

A single ``KataGoAdapter`` serializes every GTP command through one
``asyncio.Lock``. With one shared adapter, two games running in parallel
block each other on every move. We instead keep ``size`` adapter
instances and pin each game to one of them: the assignment is sticky
per ``game_id``, and the per-game ``asyncio.Lock`` in
:mod:`app.engine_pool` continues to provide turn ordering on the
adapter-shared boardsize/komi state.

When a game first arrives we pick the least-loaded adapter (fewest
already-pinned games). Re-balancing across pool resizes is not handled —
the pool size is fixed at startup.
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable

from app.core.katago.adapter import KataGoAdapter


class KataGoPool:
    def __init__(
        self,
        size: int = 4,
        *,
        adapter_factory: Callable[[], KataGoAdapter] | None = None,
    ) -> None:
        if size < 1:
            raise ValueError("KataGoPool size must be >= 1")
        factory = adapter_factory or KataGoAdapter
        self._adapters: list[KataGoAdapter] = [factory() for _ in range(size)]
        self._game_assignment: dict[int, int] = {}
        self._lock = asyncio.Lock()

    @property
    def size(self) -> int:
        return len(self._adapters)
```

- [ ] **Step 4: Run the test, confirm it passes**

```bash
KATAGO_MOCK=true pytest tests/katago/test_pool.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Add tests for `adapter_for` assignment**

Append to `backend/tests/katago/test_pool.py`:

```python
@pytest.mark.asyncio
async def test_adapter_for_returns_same_adapter_for_same_game() -> None:
    pool = _mock_pool(size=4)
    a1 = await pool.adapter_for(game_id=42)
    a2 = await pool.adapter_for(game_id=42)
    assert a1 is a2


@pytest.mark.asyncio
async def test_adapter_for_balances_across_workers() -> None:
    """First 4 distinct games should land on 4 distinct adapters
    (least-loaded picks idx 0, 1, 2, 3 in turn since each starts empty)."""
    pool = _mock_pool(size=4)
    seen = set()
    for gid in (1, 2, 3, 4):
        a = await pool.adapter_for(gid)
        seen.add(id(a))
    assert len(seen) == 4


@pytest.mark.asyncio
async def test_adapter_for_5th_game_reuses_least_loaded() -> None:
    pool = _mock_pool(size=4)
    for gid in (1, 2, 3, 4):
        await pool.adapter_for(gid)
    # 5th game must reuse one of the existing adapters (counts go 2/1/1/1)
    a5 = await pool.adapter_for(5)
    assert any(a5 is adapter for adapter in pool._adapters)


@pytest.mark.asyncio
async def test_release_clears_assignment() -> None:
    pool = _mock_pool(size=2)
    a1 = await pool.adapter_for(game_id=1)
    await pool.release(game_id=1)
    # After release, a fresh assignment is allowed (could land on either
    # adapter — both have count 0 again).
    a1_after = await pool.adapter_for(game_id=1)
    # Either adapter is acceptable, but the slot must have been freed:
    assert pool._game_assignment[1] in (0, 1)
    assert a1_after in pool._adapters
```

- [ ] **Step 6: Run the new tests — they fail because methods are missing**

```bash
KATAGO_MOCK=true pytest tests/katago/test_pool.py -v
```

Expected: 4 fails on `AttributeError: 'KataGoPool' object has no attribute 'adapter_for'`.

- [ ] **Step 7: Implement `adapter_for` and `release`**

Append to `backend/app/core/katago/pool.py`:

```python
    async def adapter_for(self, game_id: int) -> KataGoAdapter:
        """Return the pinned adapter for ``game_id``. New games are
        assigned to the adapter currently serving the fewest games."""
        async with self._lock:
            idx = self._game_assignment.get(game_id)
            if idx is None:
                counts = [0] * len(self._adapters)
                for assigned_idx in self._game_assignment.values():
                    counts[assigned_idx] += 1
                idx = counts.index(min(counts))
                self._game_assignment[game_id] = idx
            return self._adapters[idx]

    async def release(self, game_id: int) -> None:
        """Drop a game's assignment so the slot can be reused."""
        async with self._lock:
            self._game_assignment.pop(game_id, None)
```

- [ ] **Step 8: Run all pool tests — must pass**

```bash
KATAGO_MOCK=true pytest tests/katago/test_pool.py -v
```

Expected: 6 passed.

- [ ] **Step 9: Add `start_all` and `stop_all` with tests**

Append to `backend/tests/katago/test_pool.py`:

```python
@pytest.mark.asyncio
async def test_start_all_starts_every_adapter() -> None:
    pool = _mock_pool(size=3)
    await pool.start_all()
    for a in pool._adapters:
        assert a.started is True  # Mock exposes this flag


@pytest.mark.asyncio
async def test_stop_all_swallows_per_adapter_errors() -> None:
    """One adapter blowing up on stop must not abort the others."""
    pool = _mock_pool(size=3)
    await pool.start_all()

    async def explode() -> None:
        raise RuntimeError("boom")

    pool._adapters[1].stop = explode  # type: ignore[method-assign]
    # Should not raise.
    await pool.stop_all()
    assert pool._adapters[0].started is False
    assert pool._adapters[2].started is False
```

Append to `backend/app/core/katago/pool.py`:

```python
    async def start_all(self) -> None:
        await asyncio.gather(*(a.start() for a in self._adapters))

    async def stop_all(self) -> None:
        await asyncio.gather(
            *(a.stop() for a in self._adapters),
            return_exceptions=True,
        )
```

- [ ] **Step 10: Run — all 8 tests pass**

```bash
KATAGO_MOCK=true pytest tests/katago/test_pool.py -v
```

Expected: 8 passed.

- [ ] **Step 11: Verify `MockKataGoAdapter` exposes `started`**

```bash
grep -n "started" backend/app/core/katago/mock.py
```

If `started` is not a property on the mock, add the assertion path: open the file and add `self.started: bool = False` to `__init__`, set to True in `start()` and False in `stop()`. Re-run tests.

- [ ] **Step 12: Commit**

```bash
git add backend/app/core/katago/pool.py backend/tests/katago/test_pool.py
git commit -m "feat(katago): KataGoPool with sticky game-to-adapter assignment"
```

---

### Task A3: Wire `engine_pool.py` to use `KataGoPool`

**Files:**
- Modify: `backend/app/engine_pool.py`
- Modify: `backend/app/services/game_service.py`
- Modify: `backend/app/api/ws.py`
- Modify: `backend/app/api/games.py`
- Modify: `backend/app/api/analysis.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_engine_pool.py` (extend existing if present, else create)

- [ ] **Step 1: Add the pool size setting**

Edit `backend/app/config.py`. Inside `Settings`:

```python
    # Worker pool size. With Metal on M4, 4 concurrent KataGo subprocesses
    # share one GPU comfortably; raise after profiling if you ever see all
    # four queues backed up at peak. 1 is for tests/dev.
    katago_pool_size: int = 4
```

- [ ] **Step 2: Read current `engine_pool.py`**

```bash
cat backend/app/engine_pool.py
```

Note the public surface: `get_adapter()`, `set_adapter()`, `cache_state()`, `get_cached_state()`, `clear_cached_state()`, `game_lock()`, `set_adapter_owner()`, `_states`. Tests in `backend/tests/api/test_undo_flow.py` call `set_adapter(MockKataGoAdapter())` directly. We must keep that exact entry point working.

- [ ] **Step 3: Rewrite `backend/app/engine_pool.py`**

```python
"""Process-wide KataGo + game-state singletons.

* ``_pool`` is a :class:`KataGoPool` of subprocess-backed adapters.
* ``_game_locks`` serializes per-game mutations on top of the pool.
* ``_states`` caches the rules-engine state per game so we don't replay
  SGF from the DB on every move.

Tests can override the engine layer with :func:`set_adapter` (single
mock that all games share) or :func:`set_pool` (full pool replacement).
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.core.katago.adapter import KataGoAdapter
from app.core.katago.pool import KataGoPool
from app.core.rules.engine import GameState

_pool: KataGoPool | None = None
_game_locks: dict[int, asyncio.Lock] = {}
_states: dict[int, GameState] = {}
# Tracks which game id currently owns the adapter's boardsize/komi state.
# When a different game asks for the adapter, the caller must reseed.
_adapter_owners: dict[int, int] = {}  # adapter_idx -> game_id


def get_pool() -> KataGoPool:
    global _pool
    if _pool is None:
        from app.config import settings

        _pool = KataGoPool(size=settings.katago_pool_size)
    return _pool


def set_pool(pool: KataGoPool) -> None:
    """Test-only: replace the pool."""
    global _pool
    _pool = pool
    _adapter_owners.clear()


def set_adapter(adapter: KataGoAdapter) -> None:
    """Backwards-compatible single-adapter override used by existing
    tests. Builds a 1-slot pool around the supplied adapter so every
    game shares it."""
    pool = KataGoPool(size=1, adapter_factory=lambda: adapter)
    # Replace the internally-built adapter with the caller's instance —
    # the factory ran once and produced ``adapter`` itself, so this is
    # already correct, but we re-assign for clarity.
    pool._adapters[0] = adapter
    set_pool(pool)


async def get_adapter(game_id: int | None = None) -> KataGoAdapter:
    """Return the adapter pinned to ``game_id``. When ``game_id`` is
    None, returns the first adapter — used by warm-up paths that
    don't yet have a game id."""
    pool = get_pool()
    if game_id is None:
        return pool._adapters[0]
    return await pool.adapter_for(game_id)


def set_adapter_owner(game_id: int) -> None:
    """Mark ``game_id`` as the current owner of its pinned adapter's
    GTP state. Used by ``game_service`` to skip redundant
    ``clear_board`` + replay sequences when the same game plays
    twice in a row."""
    # Best-effort: we don't know the adapter index here without pool
    # lookup, but the existing call sites only need to know "I just
    # synced", so we record by game id directly.
    _adapter_owners[game_id] = game_id


def is_adapter_owner(game_id: int) -> bool:
    return _adapter_owners.get(game_id) == game_id


async def release_game(game_id: int) -> None:
    """Free the pool slot and per-game lock when a game finalizes."""
    pool = get_pool()
    await pool.release(game_id)
    _game_locks.pop(game_id, None)
    _states.pop(game_id, None)
    _adapter_owners.pop(game_id, None)


@asynccontextmanager
async def game_lock(game_id: int) -> AsyncIterator[None]:
    lock = _game_locks.setdefault(game_id, asyncio.Lock())
    async with lock:
        yield


def cache_state(game_id: int, state: GameState) -> None:
    _states[game_id] = state


def get_cached_state(game_id: int) -> GameState | None:
    return _states.get(game_id)


def clear_cached_state(game_id: int) -> None:
    _states.pop(game_id, None)
```

- [ ] **Step 4: Find all `get_adapter()` callers**

```bash
grep -rn "get_adapter()" backend/app | grep -v test_
```

Expected output (5 callsites):
```
backend/app/api/admin.py: …get_adapter()…
backend/app/api/ws.py: …get_adapter()…
backend/app/api/analysis.py: …get_adapter()…
backend/app/services/game_service.py: …multiple…
backend/app/api/games.py: …get_adapter()…
```

- [ ] **Step 5: Update each caller to pass `game_id`**

For each match above:

- `backend/app/api/games.py`: `adapter = get_adapter()` → `adapter = await get_adapter(game.id)`
- `backend/app/api/analysis.py`: same
- `backend/app/api/ws.py`: same (use `game.id`)
- `backend/app/services/game_service.py`: every `get_adapter()` → `await get_adapter(game.id)` (the file already has `async` everywhere)
- `backend/app/api/admin.py`: this one uses `get_adapter()` for status. Use `await get_adapter(None)` (returns slot 0) since admin doesn't have a game id.

Be careful: `get_adapter` is now `async`. Every call must be awaited. Search for any non-awaited call after editing.

```bash
grep -rn "= get_adapter(" backend/app | grep -v "await"
```

Expected: empty after edits.

- [ ] **Step 6: Update `app/main.py` lifespan to start/stop the pool**

Modify `lifespan()` in `backend/app/main.py`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await enable_wal()

    from app.engine_pool import get_pool
    pool = get_pool()
    await pool.start_all()

    from app.session_purge import run_purge_loop

    purge_task = asyncio.create_task(
        run_purge_loop(
            interval_sec=settings.session_purge_interval_sec,
            ttl_sec=settings.session_idle_ttl_sec,
        )
    )
    try:
        yield
    finally:
        purge_task.cancel()
        try:
            await purge_task
        except asyncio.CancelledError:
            pass
        await pool.stop_all()
```

- [ ] **Step 7: Add `release_game` calls when a game finalizes**

Edit `backend/app/services/game_service.py`. Locate every `game.status = "finished"` or `"resigned"` assignment. After the `await db.commit()` that follows, add:

```python
                from app.engine_pool import release_game
                await release_game(game.id)
```

Approximate locations (search by `game.status = "finished"` and `game.status = "resigned"`):
- The `ai_passed_scored` block in `place_move`
- The auto-resign streak block in `place_move`
- `score_by_request`
- `resign_game`

If a callsite is awkward to import-locally, hoist `from app.engine_pool import release_game` to the file's top imports.

- [ ] **Step 8: Run the full backend suite**

```bash
KATAGO_MOCK=true pytest -q
```

Expected: 347 passed (same as baseline). If anything fails, the pool wiring is the suspect — most likely a missed `await` in front of `get_adapter`.

- [ ] **Step 9: Run mypy + ruff**

```bash
ruff check . && mypy app
```

Expected: clean.

- [ ] **Step 10: Commit**

```bash
git add backend/app/engine_pool.py backend/app/main.py \
        backend/app/api/games.py backend/app/api/ws.py \
        backend/app/api/analysis.py backend/app/api/admin.py \
        backend/app/services/game_service.py backend/app/config.py
git commit -m "refactor(engine): route adapter access through KataGoPool"
```

---

### Task A4: Cap strength at 5d / max_visits=256

**Files:**
- Modify: `backend/app/core/katago/strength.py`
- Test: `backend/tests/katago/test_strength.py` (extend or create)

- [ ] **Step 1: Read current `strength.py`**

```bash
cat backend/app/core/katago/strength.py
```

Note the rank → (profile, max_visits) mapping. The 1.0 launch only ships 18-kyu through 5-dan. 6d/7d are still expressible internally but the public selector and validator must reject them.

- [ ] **Step 2: Write the failing test**

Append to `backend/tests/katago/test_strength.py`:

```python
def test_rank_to_config_caps_max_visits_at_256() -> None:
    """Every supported rank must have max_visits <= 256 in v1.0."""
    from app.core.katago.strength import (
        rank_to_config,
        SUPPORTED_AI_RANKS,
    )

    for rank in SUPPORTED_AI_RANKS:
        cfg = rank_to_config(rank, "balanced", None)
        assert cfg.max_visits <= 256, (
            f"{rank} exceeds the v1.0 cap (got {cfg.max_visits})"
        )


def test_supported_ranks_excludes_6d_and_7d() -> None:
    from app.core.katago.strength import SUPPORTED_AI_RANKS

    assert "6d" not in SUPPORTED_AI_RANKS
    assert "7d" not in SUPPORTED_AI_RANKS
    assert "5d" in SUPPORTED_AI_RANKS


def test_unsupported_rank_raises() -> None:
    import pytest as _pytest
    from app.core.katago.strength import rank_to_config, UnsupportedRank

    with _pytest.raises(UnsupportedRank):
        rank_to_config("9d", "balanced", None)
```

- [ ] **Step 3: Run — fails because `SUPPORTED_AI_RANKS`/`UnsupportedRank` don't exist or 7d still in table**

```bash
KATAGO_MOCK=true pytest tests/katago/test_strength.py -v
```

- [ ] **Step 4: Modify `strength.py`**

Open `backend/app/core/katago/strength.py`. At the top, define:

```python
class UnsupportedRank(ValueError):
    """Raised when a caller asks for a rank not in the public 1.0 set."""


SUPPORTED_AI_RANKS: tuple[str, ...] = (
    "18k", "15k", "12k", "10k", "7k", "5k", "3k", "1k",
    "1d", "3d", "5d",
)
```

In `rank_to_config`, before the existing lookup:

```python
def rank_to_config(rank: str, style: str, player: str | None) -> ...:
    if rank not in SUPPORTED_AI_RANKS:
        raise UnsupportedRank(rank)
    ...
```

In the existing visit table, change any `512` (7d) and `384` (6d) entries — drop them entirely or, if you keep them for a future flag-flip, ensure they're outside the public set. Cap any remaining entry to 256:

```python
# Before: "5d": ProfileConfig(profile="strong", max_visits=384),
# After:  "5d": ProfileConfig(profile="strong", max_visits=256),
```

- [ ] **Step 5: Run — must pass**

```bash
KATAGO_MOCK=true pytest tests/katago/test_strength.py -v
```

- [ ] **Step 6: Make `INVALID_AI_RANK` a `GameError`**

In `backend/app/services/game_service.py`, in `create_game`, before calling `rank_to_config`:

```python
from app.core.katago.strength import SUPPORTED_AI_RANKS, UnsupportedRank
if ai_rank not in SUPPORTED_AI_RANKS:
    raise GameError("INVALID_AI_RANK", ai_rank)
```

- [ ] **Step 7: Append a test in `test_game_service_errors.py`**

```python
@pytest.mark.asyncio
async def test_create_game_rejects_unsupported_rank(
    db_session: AsyncSession,
) -> None:
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, nickname="rankt")
    with pytest.raises(GameError) as exc:
        await create_game(
            db_session,
            session=s,
            ai_rank="7d",
            handicap=0,
            user_color="black",
            board_size=9,
        )
    assert exc.value.code == "INVALID_AI_RANK"
```

- [ ] **Step 8: Run full suite**

```bash
KATAGO_MOCK=true pytest -q
```

Expected: 350 passed.

- [ ] **Step 9: Commit**

```bash
git add backend/app/core/katago/strength.py \
        backend/tests/katago/test_strength.py \
        backend/app/services/game_service.py \
        backend/tests/api/test_game_service_errors.py
git commit -m "feat(strength): cap v1.0 ranks at 5d, max_visits=256"
```

---

### Task A5: Concurrent-games integration test

**Files:**
- Create: `backend/tests/api/test_concurrent_games.py`

This proves the pool actually parallelizes — without it, the `engine_pool` rewrite could still funnel everything through one adapter and tests wouldn't catch it.

- [ ] **Step 1: Create the test file**

```python
"""Integration test: two simultaneous games on a 4-worker mock pool
must land on different adapter instances and not interfere with each
other's GameState cache."""
from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.katago.mock import MockKataGoAdapter
from app.core.katago.pool import KataGoPool
from app.engine_pool import get_pool, set_pool
from app.models import Session
from app.services.game_service import create_game, place_move


def _mock_pool(size: int = 4) -> KataGoPool:
    return KataGoPool(size=size, adapter_factory=MockKataGoAdapter)


@pytest.mark.asyncio
async def test_two_games_use_different_adapters(
    db_session: AsyncSession,
) -> None:
    set_pool(_mock_pool(size=4))
    pool = get_pool()
    await pool.start_all()

    s1 = Session(token="s1-tok", nickname="p1", nickname_key="p1")  # noqa: S106
    s2 = Session(token="s2-tok", nickname="p2", nickname_key="p2")  # noqa: S106
    db_session.add_all([s1, s2])
    await db_session.commit()
    await db_session.refresh(s1)
    await db_session.refresh(s2)

    g1 = await create_game(
        db_session, session=s1, ai_rank="5k", handicap=0,
        user_color="black", board_size=9,
    )
    g2 = await create_game(
        db_session, session=s2, ai_rank="5k", handicap=0,
        user_color="black", board_size=9,
    )

    a1 = await pool.adapter_for(g1.id)
    a2 = await pool.adapter_for(g2.id)
    assert a1 is not a2, (
        "Pool gave the same adapter to two distinct games — pool is "
        "not balancing."
    )


@pytest.mark.asyncio
async def test_concurrent_moves_do_not_corrupt_state(
    db_session: AsyncSession,
) -> None:
    set_pool(_mock_pool(size=4))
    await get_pool().start_all()

    s1 = Session(token="cm1", nickname="cm1", nickname_key="cm1")  # noqa: S106
    s2 = Session(token="cm2", nickname="cm2", nickname_key="cm2")  # noqa: S106
    db_session.add_all([s1, s2])
    await db_session.commit()
    await db_session.refresh(s1)
    await db_session.refresh(s2)

    g1 = await create_game(
        db_session, session=s1, ai_rank="5k", handicap=0,
        user_color="black", board_size=9,
    )
    g2 = await create_game(
        db_session, session=s2, ai_rank="5k", handicap=0,
        user_color="black", board_size=9,
    )

    # Fire both moves at once.
    r1, r2 = await asyncio.gather(
        place_move(db_session, game=g1, session=s1, coord="D4"),
        place_move(db_session, game=g2, session=s2, coord="E5"),
    )
    assert r1.game_state.board.size == 9
    assert r2.game_state.board.size == 9
    # Each game's user move must persist in the right state.
    assert r1.game_state.board.get(3, 5) == "B"  # D4 in 9x9
    assert r2.game_state.board.get(4, 4) == "B"  # E5 in 9x9
```

- [ ] **Step 2: Run**

```bash
KATAGO_MOCK=true pytest tests/api/test_concurrent_games.py -v
```

Expected: 2 passed. If `test_concurrent_moves_do_not_corrupt_state` fails with state mismatch, the per-game lock isn't being honored — verify `engine_pool.game_lock` is still wrapping mutations in `place_move`.

- [ ] **Step 3: Run full suite**

```bash
KATAGO_MOCK=true pytest --cov=app --cov-fail-under=80 -q
```

Expected: 352 passed, coverage ≥ 80%.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/api/test_concurrent_games.py
git commit -m "test(engine): two games on 4-adapter mock pool stay isolated"
```

---

## Phase B — Backend quality fixes (P1)

### Task B1: `GameError.detail` flows into HTTP error body (P1-1)

**Files:**
- Modify: `backend/app/errors.py`
- Test: `backend/tests/api/test_error_response.py` (new)

- [ ] **Step 1: Read current error handler**

```bash
cat backend/app/errors.py
```

Note the existing `GameError` handler only emits `code`. Clients can't distinguish "you tried to play on F5" from "you tried to play on F6" — both surface as `INVALID_COORD`. The fix preserves `detail` as a separate field.

- [ ] **Step 2: Write the failing test**

Create `backend/tests/api/test_error_response.py`:

```python
"""GameError responses must include both ``code`` and ``detail`` so
clients can show targeted error toasts (the ``detail`` is e.g. the
exact illegal coordinate, not just the category)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_game_error_response_includes_detail(client: AsyncClient) -> None:
    # Create a session
    r = await client.post("/api/session", json={"nickname": "errbody"})
    assert r.status_code == 201

    # Create a game
    r = await client.post(
        "/api/games",
        json={
            "ai_rank": "5k",
            "handicap": 99,  # invalid → INVALID_HANDICAP with detail="99"
            "user_color": "black",
            "board_size": 9,
        },
    )
    assert r.status_code == 400
    body = r.json()
    assert body["detail"]["code"] == "INVALID_HANDICAP"
    assert body["detail"]["detail"] == "99"
```

- [ ] **Step 3: Run — fails (current handler emits only code)**

```bash
KATAGO_MOCK=true pytest tests/api/test_error_response.py -v
```

- [ ] **Step 4: Patch the handler**

Modify the `GameError` handler in `backend/app/errors.py`:

```python
@app.exception_handler(GameError)
async def _game_error_handler(_req: Request, exc: GameError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "detail": {
                "code": exc.code,
                "detail": exc.detail,
            }
        },
    )
```

The outer `detail` matches FastAPI's default error envelope so existing toast wiring keeps working; the inner `code`/`detail` is what the client now reads.

- [ ] **Step 5: Update existing client code that reads error responses**

Frontend won't be touched here (Plan 2). For the backend, find any test that asserts `body["detail"] == "INVALID_…"` (string equality) and update it to `body["detail"]["code"]`:

```bash
grep -rn '"detail"\] ==' backend/tests
```

For each match, change the comparison to `["detail"]["code"]`.

- [ ] **Step 6: Run full suite**

```bash
KATAGO_MOCK=true pytest -q
```

Expected: all passing. If something breaks, the existing assertion expected the bare string — fix to use the dict shape.

- [ ] **Step 7: Commit**

```bash
git add backend/app/errors.py backend/tests/api/test_error_response.py backend/tests
git commit -m "fix(api): GameError responses now carry detail alongside code"
```

---

### Task B2: `/analyze?moveNum=N` replays to N before analyzing (P1-2)

**Files:**
- Modify: `backend/app/services/analysis_service.py` (or wherever the endpoint lives — likely `backend/app/api/analysis.py`)
- Test: `backend/tests/api/test_analysis_movenum.py` (new)

- [ ] **Step 1: Read current analyze endpoint**

```bash
cat backend/app/api/analysis.py
```

Confirm: the cache is keyed on `(game_id, move_number)` but the analysis itself runs against the *current* board, ignoring `moveNum`. Reading review for an early move surfaces the *latest* analysis cached at that key.

- [ ] **Step 2: Write the failing test**

Create `backend/tests/api/test_analysis_movenum.py`:

```python
"""Reviewing moveNum=3 must analyze the board state after move 3, not
after the latest move."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analyze_at_early_move_differs_from_latest(
    client: AsyncClient,
) -> None:
    r = await client.post("/api/session", json={"nickname": "movenum"})
    assert r.status_code == 201

    r = await client.post(
        "/api/games",
        json={"ai_rank": "5k", "handicap": 0,
              "user_color": "black", "board_size": 9},
    )
    gid = r.json()["id"]

    # Play five plies via WS to populate moves 1..5 (mock adapter responds
    # deterministically).
    # NOTE: we use the test client's WS support if available; otherwise
    # fall back to direct service calls. The point is to fill moves 1..5.
    from app.services.game_service import place_move
    from app.models import Game, Session
    from sqlalchemy import select
    from app.db import AsyncSessionLocal
    coords = ["D4", "C3", "F5", "E6", "G7"]
    async with AsyncSessionLocal() as db:
        sess = (await db.execute(select(Session))).scalars().first()
        game = (await db.execute(select(Game).where(Game.id == gid))).scalar_one()
        for c in coords:
            await place_move(db, game=game, session=sess, coord=c)

    # Now hit the analyze endpoint at moveNum=2 and moveNum=10
    r2 = await client.get(f"/api/games/{gid}/analyze?moveNum=2")
    r10 = await client.get(f"/api/games/{gid}/analyze?moveNum=10")
    assert r2.status_code == 200
    assert r10.status_code == 200
    # The two responses must differ — analyzing at move 2 looks at a
    # mostly-empty board; at move 10 the board is much fuller.
    j2 = r2.json()
    j10 = r10.json()
    assert j2 != j10
```

- [ ] **Step 3: Run — should fail (returns same payload for both)**

- [ ] **Step 4: Add a `_replay_to_move(game, target_move)` helper**

In `backend/app/services/game_service.py` (where `_replay_state` already lives), add:

```python
async def _replay_state_to(
    db: AsyncSession, game: Game, target_move: int
) -> GameState:
    """Re-play the moves table up to (and including) ``target_move`` and
    return the resulting :class:`GameState`. ``target_move=0`` returns
    the initial state (empty board with handicap stones, if any)."""
    from app.core.rules.engine import GameState, Move
    from app.core.rules.board import Board
    from app.core.rules.handicap import apply_handicap, HANDICAP_TABLES
    from app.core.rules.engine import play

    state = GameState(board=Board(game.board_size), komi=game.komi)
    if game.handicap > 0:
        state.board = apply_handicap(state.board, game.handicap)
        state.to_move = WHITE  # handicap = white plays next
    res = await db.execute(
        select(MoveRow)
        .where(MoveRow.game_id == game.id, MoveRow.is_undone.is_(False))
        .order_by(MoveRow.move_number.asc())
    )
    rows = res.scalars().all()
    for row in rows:
        if row.move_number > target_move:
            break
        if row.coord is None:
            # resign — stop replay there
            break
        state = play(state, Move(color=row.color, coord=row.coord))
    return state
```

- [ ] **Step 5: Wire `analyze` to use the helper**

In `backend/app/api/analysis.py`, locate the analyze endpoint. After fetching `game` and validating the cache, before calling the adapter, replay to `moveNum` and seed the adapter with that board:

```python
state = await _replay_state_to(db, game, moveNum)
adapter = await get_adapter(game.id)
await adapter.start()
await adapter.set_boardsize(game.board_size)
await adapter.set_komi(game.komi)
await adapter.clear_board()
for mv in state.move_history:
    await adapter.play(mv.color, mv.coord)
res = await adapter.analyze(side=state.to_move, max_visits=cfg.max_visits)
```

- [ ] **Step 6: Run — should pass**

```bash
KATAGO_MOCK=true pytest tests/api/test_analysis_movenum.py -v
```

- [ ] **Step 7: Run full suite**

```bash
KATAGO_MOCK=true pytest -q
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/game_service.py backend/app/api/analysis.py \
        backend/tests/api/test_analysis_movenum.py
git commit -m "fix(analyze): respect moveNum by replaying state before analyzing"
```

---

### Task B3: FK index Alembic migration (P1-7)

**Files:**
- Create: `backend/migrations/versions/0003_fk_indexes.py`

- [ ] **Step 1: Inspect the existing latest migration revision**

```bash
ls backend/migrations/versions/ | sort
```

Use the highest existing revision number as `down_revision`.

- [ ] **Step 2: Generate a new revision**

```bash
cd backend && source .venv311/bin/activate
alembic revision -m "add fk indexes"
```

This creates `backend/migrations/versions/<hash>_add_fk_indexes.py`.

- [ ] **Step 3: Edit the generated file**

Alembic auto-fills `revision` (the generated hash) and `down_revision` (the previous head) — keep those untouched. Only replace the body. Open the new file under `backend/migrations/versions/`:

```python
"""add fk indexes

Revision ID: <auto-filled by alembic>
Revises: <auto-filled by alembic>
Create Date: <auto-filled by alembic>

Without these, the foreign-key columns we filter most often (moves.game_id,
analyses.game_id, session_history.session_id) trigger full-table scans on
SELECTs and on cascade DELETEs. This is fine at 100 games but degrades
linearly. The fix is one migration.
"""
from alembic import op


# Leave revision / down_revision / branch_labels / depends_on at the
# values alembic auto-generated. Only the upgrade/downgrade bodies
# below need to change.


def upgrade() -> None:
    op.create_index(
        "ix_moves_game_id", "moves", ["game_id"], unique=False
    )
    op.create_index(
        "ix_analyses_game_id", "analyses", ["game_id"], unique=False
    )
    op.create_index(
        "ix_session_history_session_id",
        "session_history",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_session_history_session_id")
    op.drop_index("ix_analyses_game_id")
    op.drop_index("ix_moves_game_id")
```

- [ ] **Step 4: Apply locally**

```bash
alembic upgrade head
```

Expected: prints "Running upgrade … -> 0003_fk_indexes".

- [ ] **Step 5: Run tests**

```bash
KATAGO_MOCK=true pytest -q
```

The conftest creates schema via `Base.metadata.create_all`, which already adds these indexes if the model classes declare them. To keep ORM truth in sync with the migration, also add `index=True` on the model fields:

In `backend/app/models/move.py`, the `game_id` Column should already be `ForeignKey("games.id")` — add `index=True`:

```python
game_id: Mapped[int] = mapped_column(
    ForeignKey("games.id", ondelete="CASCADE"), index=True
)
```

Repeat for `backend/app/models/analysis_cache.py` (`game_id`) and `backend/app/models/session_history.py` (`session_id`).

- [ ] **Step 6: Re-run tests**

```bash
KATAGO_MOCK=true pytest -q
```

Expected: all passing.

- [ ] **Step 7: Commit**

```bash
git add backend/migrations/versions backend/app/models
git commit -m "perf(db): add foreign-key indexes (moves, analyses, session_history)"
```

---

### Task B4: Pydantic range constraints + cors_origins whitespace (P1-8, P1-9)

**Files:**
- Modify: `backend/app/schemas/game.py`
- Modify: `backend/app/config.py`
- Test: `backend/tests/api/test_validation.py` (new)

- [ ] **Step 1: Add range constraints to schemas**

Open `backend/app/schemas/game.py`. For any `moveNum`, `page`, `limit` field, add `Field(ge=…, le=…)`:

```python
from pydantic import BaseModel, Field


class AnalysisQuery(BaseModel):  # adapt name to actual schema
    moveNum: int = Field(ge=0, le=2000)


class HistoryQuery(BaseModel):
    page: int = Field(ge=1, le=10_000, default=1)
    limit: int = Field(ge=1, le=100, default=20)
```

If the project uses query parameters directly (not Pydantic), add `Query(..., ge=0, le=2000)` in the FastAPI handler instead:

```python
from fastapi import Query

@router.get(…)
async def analyze_endpoint(
    game_id: int,
    moveNum: int = Query(..., ge=0, le=2000),
    …
):
```

- [ ] **Step 2: Tolerate whitespace in `cors_origins`**

In `backend/app/config.py`, expose a parsed list as a property:

```python
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
```

In `backend/app/main.py`, swap the CORS middleware call:

```python
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,  # was .split(",")
        …
    )
```

- [ ] **Step 3: Write the failing test**

Create `backend/tests/api/test_validation.py`:

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analyze_rejects_negative_movenum(client: AsyncClient) -> None:
    # Set up a session + game first (small fixture inline)
    r = await client.post("/api/session", json={"nickname": "neg"})
    assert r.status_code == 201
    r = await client.post(
        "/api/games",
        json={"ai_rank": "5k", "handicap": 0,
              "user_color": "black", "board_size": 9},
    )
    gid = r.json()["id"]
    r = await client.get(f"/api/games/{gid}/analyze?moveNum=-1")
    assert r.status_code == 422  # validation error


def test_cors_origins_list_strips_whitespace() -> None:
    from app.config import Settings
    s = Settings(cors_origins=" http://a , http://b ")
    assert s.cors_origins_list == ["http://a", "http://b"]
```

- [ ] **Step 4: Run — passes if Step 1+2 are correct**

```bash
KATAGO_MOCK=true pytest tests/api/test_validation.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/game.py backend/app/config.py \
        backend/app/main.py backend/tests/api/test_validation.py
git commit -m "fix(api): range constraints on moveNum/page; tolerant cors split"
```

---

### Task B5: Investigate aiosqlite teardown warnings

**Files:**
- Modify (maybe): `backend/tests/conftest.py`

The baseline run reports ~9 `RuntimeError: Event loop is closed` pytest warnings. They're cosmetic (originate from aiosqlite's worker thread after the test loop closes) but worth understanding before launch so they don't mask a real failure later.

- [ ] **Step 1: Reproduce + count**

```bash
cd backend && source .venv311/bin/activate
KATAGO_MOCK=true pytest -q 2>&1 | grep -c "Event loop is closed"
```

Note the count.

- [ ] **Step 2: Read current `conftest.py` teardown order**

```bash
sed -n '40,75p' backend/tests/conftest.py
```

- [ ] **Step 3: Try explicit AsyncSession close**

If the `db_session` fixture lacks an explicit close, add one:

```python
@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncSession:
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as s:
        try:
            yield s
        finally:
            await s.close()
```

Re-run and count again. If the count drops, ship the fix.

- [ ] **Step 4: If the warning is irreducible**

aiosqlite has a known race where its worker thread tries one last call after the loop is gone. If Step 3 doesn't help, **leave it** — add a comment to `conftest.py` documenting that the warning is cosmetic and the upstream issue (link to aiosqlite issue tracker if known). Do not try to silence with `filterwarnings` — that masks real regressions.

- [ ] **Step 5: Commit (only if changes were made)**

```bash
git add backend/tests/conftest.py
git commit -m "test(conftest): explicit AsyncSession close to reduce teardown warnings"
```

If no changes, no commit.

---

### Task B6: Audit for SQLite-specific SQL

**Files:**
- (Audit only — produces commits only if findings.)

- [ ] **Step 1: Grep for SQLite-specific constructs**

```bash
cd backend
grep -rEn 'JULIANDAY|RANDOM\(\)|INSERT OR REPLACE|PRAGMA |strftime\(' app | grep -v ".venv" | grep -v __pycache__
```

- [ ] **Step 2: For each match, decide**

- `PRAGMA foreign_keys=ON` in `db.py` and conftest is fine (only inside the SQLite branch of `enable_wal`). Leave.
- `INSERT OR REPLACE` would require change to `INSERT … ON CONFLICT` for portability. If found, replace.
- `RANDOM()` — replace with Python random + parameter binding.
- `JULIANDAY` / `strftime` — replace with SQLAlchemy date functions.

- [ ] **Step 3: If any changes were made, run tests**

```bash
KATAGO_MOCK=true pytest -q
```

- [ ] **Step 4: Commit any changes**

```bash
git commit -m "refactor(db): replace SQLite-specific SQL with portable forms"
```

If no findings, no commit needed.

---

## Phase C — WebSocket reliability

### Task C1: WS single-session race fix (P0-10)

**Files:**
- Modify: `backend/app/api/ws.py`
- Test: `backend/tests/api/test_ws_lifecycle.py` (new — Task C2 also writes here)

- [ ] **Step 1: Read current `_connections` swap logic**

The relevant block in `backend/app/api/ws.py`:

```python
existing = _connections.get(game_id)
if existing is not None:
    try:
        await existing.send_json({"type": "error", "code": "SESSION_REPLACED"})
        await existing.close()
    except Exception:  # noqa: S110
        pass

await websocket.accept()
_connections[game_id] = websocket
```

Race: two near-simultaneous connections both see `existing` as the *original* (or as None), both close it, both insert themselves. Final state is unpredictable.

- [ ] **Step 2: Add a per-game-id lock around the swap**

At module scope, alongside `_connections`:

```python
_connection_locks: dict[int, asyncio.Lock] = {}


def _get_connection_lock(game_id: int) -> asyncio.Lock:
    lock = _connection_locks.get(game_id)
    if lock is None:
        lock = asyncio.Lock()
        _connection_locks[game_id] = lock
    return lock
```

Wrap the swap:

```python
    async with _get_connection_lock(game_id):
        existing = _connections.get(game_id)
        if existing is not None:
            try:
                await existing.send_json({"type": "error", "code": "SESSION_REPLACED"})
                await existing.close()
            except Exception:  # noqa: S110
                pass
        await websocket.accept()
        _connections[game_id] = websocket
```

- [ ] **Step 3: Write the failing test**

Create `backend/tests/api/test_ws_lifecycle.py`:

```python
"""WebSocket session replacement must be atomic — under racing
connection attempts, exactly one connection must end up registered."""
from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_concurrent_connections_settle_to_single_active(
    client: AsyncClient,
) -> None:
    # Set up a session + game
    r = await client.post("/api/session", json={"nickname": "wsrace"})
    assert r.status_code == 201
    cookies = r.cookies
    r = await client.post(
        "/api/games",
        json={"ai_rank": "5k", "handicap": 0,
              "user_color": "black", "board_size": 9},
        cookies=cookies,
    )
    gid = r.json()["id"]

    # We can't easily race two real WS connects through the test
    # client. Instead drive the swap helper directly.
    from app.api.ws import _connections, _get_connection_lock

    class FakeWS:
        def __init__(self, name: str) -> None:
            self.name = name
            self.closed = False
        async def accept(self) -> None: pass
        async def send_json(self, _: dict) -> None: pass
        async def close(self) -> None:
            self.closed = True

    ws_a = FakeWS("a")
    ws_b = FakeWS("b")

    async def install(ws: FakeWS) -> None:
        async with _get_connection_lock(gid):
            existing = _connections.get(gid)
            if existing is not None:
                await existing.send_json({"type": "error", "code": "SESSION_REPLACED"})
                await existing.close()
            await ws.accept()
            _connections[gid] = ws

    await asyncio.gather(install(ws_a), install(ws_b))
    assert _connections[gid] in (ws_a, ws_b)
    # The loser must be closed
    losers = [w for w in (ws_a, ws_b) if w is not _connections[gid]]
    assert all(w.closed for w in losers)
    _connections.pop(gid, None)
```

- [ ] **Step 4: Run — must pass after the lock is in place**

```bash
KATAGO_MOCK=true pytest tests/api/test_ws_lifecycle.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/ws.py backend/tests/api/test_ws_lifecycle.py
git commit -m "fix(ws): per-game-id lock around _connections swap (P0-10)"
```

---

### Task C2: WS heartbeat + session expiry (P0-12)

**Files:**
- Modify: `backend/app/api/ws.py`
- Test: append to `backend/tests/api/test_ws_lifecycle.py`

A mobile WebSocket can survive long after the underlying session has been purged (idle TTL, explicit logout). Without a heartbeat the WS keeps sending state updates to a no-longer-authenticated client.

- [ ] **Step 1: Add a heartbeat task**

In `backend/app/api/ws.py`, alongside the main `ws_game` coroutine, define:

```python
HEARTBEAT_SECONDS = 30


async def _heartbeat(websocket: WebSocket, game_id: int, sess: Session) -> None:
    """Every 30s, re-check that the session row still exists. If it
    doesn't, close the WS with a structured reason. Runs as a sibling
    task to the receive loop and is cancelled on disconnect."""
    while True:
        await asyncio.sleep(HEARTBEAT_SECONDS)
        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            row = await db.execute(
                select(Session).where(Session.id == sess.id)
            )
            if row.scalar_one_or_none() is None:
                try:
                    await websocket.send_json(
                        {"type": "error", "code": "SESSION_EXPIRED"}
                    )
                except Exception:  # noqa: S110
                    pass
                await websocket.close()
                return
```

- [ ] **Step 2: Spawn the heartbeat alongside `ws_game`**

Inside `ws_game`, after `_connections[game_id] = websocket` and before the receive loop:

```python
    hb_task = asyncio.create_task(_heartbeat(websocket, game_id, sess))
    try:
        # … existing receive loop …
    finally:
        hb_task.cancel()
        try:
            await hb_task
        except (asyncio.CancelledError, Exception):
            pass
        if _connections.get(game_id) is websocket:
            _connections.pop(game_id, None)
```

- [ ] **Step 3: Write the failing test**

Append to `backend/tests/api/test_ws_lifecycle.py`:

```python
@pytest.mark.asyncio
async def test_heartbeat_closes_ws_when_session_disappears(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The heartbeat must close the WS as soon as the underlying
    session row is gone."""
    from app.api import ws as ws_module
    from app.db import AsyncSessionLocal
    from app.models import Session

    # 1-second heartbeat for the test
    monkeypatch.setattr(ws_module, "HEARTBEAT_SECONDS", 0.1)

    closed = asyncio.Event()

    class FakeWS:
        async def send_json(self, _: dict) -> None: pass
        async def close(self) -> None: closed.set()

    # Insert + then delete a session row
    async with AsyncSessionLocal() as db:
        sess = Session(token="hb", nickname="hb", nickname_key="hb")  # noqa: S106
        db.add(sess)
        await db.commit()
        await db.refresh(sess)
        sess_copy = sess  # for the heartbeat
        from sqlalchemy import delete
        await db.execute(delete(Session).where(Session.id == sess.id))
        await db.commit()

    task = asyncio.create_task(
        ws_module._heartbeat(FakeWS(), 1, sess_copy)
    )
    await asyncio.wait_for(closed.wait(), timeout=2.0)
    task.cancel()
```

- [ ] **Step 4: Run — should pass**

```bash
KATAGO_MOCK=true pytest tests/api/test_ws_lifecycle.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/ws.py backend/tests/api/test_ws_lifecycle.py
git commit -m "feat(ws): heartbeat closes WS when session row vanishes (P0-12)"
```

---

## Phase D — Deployment

### Task D1: launchd service file

**Files:**
- Create: `backend/deploy/com.baduk.api.plist`
- Create: `backend/deploy/run_local_prod.sh`
- Create: `backend/deploy/README.md`

- [ ] **Step 1: Create the launcher script**

Create `backend/deploy/run_local_prod.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Activate venv
source .venv311/bin/activate

# Production env. Real secrets come from a sourced ~/.baduk.env on the
# Mac mini (see deploy/README.md). This script is checked in; the .env
# is not.
if [ -f "$HOME/.baduk.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$HOME/.baduk.env"
  set +a
fi

export APP_ENV=production
export KATAGO_MOCK=${KATAGO_MOCK:-false}
export KATAGO_BIN_PATH="$(pwd)/katago/bin/katago"
export DATABASE_URL=${DATABASE_URL:-"sqlite+aiosqlite:///./data/baduk.db"}

# launchd captures stdout/stderr; uvicorn already JSON-logs via structlog.
exec uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

```bash
chmod +x backend/deploy/run_local_prod.sh
```

- [ ] **Step 2: Create the plist**

Create `backend/deploy/com.baduk.api.plist`. Replace `__USER_HOME__` and `__PROJECT_PATH__` with absolute paths during deploy:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.baduk.api</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>__PROJECT_PATH__/backend/deploy/run_local_prod.sh</string>
  </array>

  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ProcessType</key><string>Interactive</string>

  <key>StandardOutPath</key>
  <string>__USER_HOME__/Library/Logs/baduk-api.log</string>
  <key>StandardErrorPath</key>
  <string>__USER_HOME__/Library/Logs/baduk-api.err</string>

  <key>WorkingDirectory</key>
  <string>__PROJECT_PATH__/backend</string>
</dict>
</plist>
```

- [ ] **Step 3: Document install in `backend/deploy/README.md`**

```markdown
# Production deployment (Mac mini)

## One-time setup

1. Build KataGo: `./backend/katago/build_macos.sh`
2. Create `~/.baduk.env`:

   ```
   SESSION_SECRET=<32-byte random>
   CORS_ORIGINS=https://yourdomain,https://localhost,capacitor://localhost
   COOKIE_SAMESITE=none
   CF_TRUSTED_PROXY=true
   KATAGO_POOL_SIZE=4
   KATAGO_HUMAN_MODEL_PATH=/path/to/b18c384nbt-humanv0.bin.gz
   ```

3. Customize the plist:

   ```bash
   sed -e "s|__PROJECT_PATH__|$HOME/projects/baduk|g" \
       -e "s|__USER_HOME__|$HOME|g" \
       backend/deploy/com.baduk.api.plist \
       > ~/Library/LaunchAgents/com.baduk.api.plist
   ```

4. Load:

   ```bash
   launchctl load ~/Library/LaunchAgents/com.baduk.api.plist
   ```

## Verify

```bash
curl -s http://127.0.0.1:8000/api/health
launchctl list | grep com.baduk.api
tail -f ~/Library/Logs/baduk-api.log
```

## Reload after a deploy

```bash
launchctl kickstart -k gui/$(id -u)/com.baduk.api
```
```

- [ ] **Step 4: Smoke-test on Mac mini**

```bash
./backend/deploy/run_local_prod.sh
# Ctrl-C after seeing "Application startup complete"
launchctl load ~/Library/LaunchAgents/com.baduk.api.plist
sleep 5
curl -s http://127.0.0.1:8000/api/health | python3 -m json.tool
```

Expected: `{"status": "ok"}` (or whatever the health endpoint returns).

- [ ] **Step 5: Reboot test (optional but strongly recommended)**

Reboot the Mac mini. After login, run the curl health check again. Expected: ok within 30 seconds of login.

- [ ] **Step 6: Commit**

```bash
git add backend/deploy/
git commit -m "feat(deploy): launchd service + production launcher"
```

---

### Task D2: Cloudflare Tunnel config

**Files:**
- Create: `backend/deploy/cloudflared.yml`
- Modify: `backend/deploy/README.md`

- [ ] **Step 1: Install cloudflared**

```bash
brew install cloudflared
```

- [ ] **Step 2: Authenticate (browser opens)**

```bash
cloudflared tunnel login
```

This stores `~/.cloudflared/cert.pem`. Pick the domain you registered.

- [ ] **Step 3: Create the tunnel**

```bash
cloudflared tunnel create baduk
```

Note the tunnel ID printed (UUID).

- [ ] **Step 4: Create `backend/deploy/cloudflared.yml`**

Replace `__TUNNEL_UUID__` and `__DOMAIN__`:

```yaml
tunnel: __TUNNEL_UUID__
credentials-file: __USER_HOME__/.cloudflared/__TUNNEL_UUID__.json

ingress:
  # API + WebSocket
  - hostname: api.__DOMAIN__
    service: http://127.0.0.1:8000

  # Frontend (when web/ is also running locally — see Plan 2)
  - hostname: __DOMAIN__
    service: http://127.0.0.1:3000

  # Catch-all
  - service: http_status:404
```

- [ ] **Step 5: Route DNS**

```bash
cloudflared tunnel route dns baduk api.<domain>
cloudflared tunnel route dns baduk <domain>
```

Each command prints "Successfully created CNAME …".

- [ ] **Step 6: Run the tunnel manually first**

```bash
cloudflared tunnel --config backend/deploy/cloudflared.yml run baduk
```

In another shell:

```bash
curl -s https://api.<domain>/api/health | python3 -m json.tool
```

Expected: same `{"status": "ok"}`.

- [ ] **Step 7: Add `cloudflared` as a launchd service**

```bash
sudo cloudflared service install
```

This creates `/Library/LaunchDaemons/com.cloudflare.cloudflared.plist` and starts it. cloudflared looks for `/etc/cloudflared/config.yml` — copy our config there:

```bash
sudo mkdir -p /etc/cloudflared
sudo cp backend/deploy/cloudflared.yml /etc/cloudflared/config.yml
sudo cp ~/.cloudflared/<TUNNEL_UUID>.json /etc/cloudflared/
sudo launchctl unload /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
sudo launchctl load   /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
```

- [ ] **Step 8: Reboot test**

After reboot: `curl https://api.<domain>/api/health` works without you logging in.

- [ ] **Step 9: Update `backend/deploy/README.md`**

Add a "Cloudflare Tunnel" section with the steps above.

- [ ] **Step 10: Commit (config only — secrets stay out)**

```bash
git add backend/deploy/cloudflared.yml backend/deploy/README.md
git commit -m "feat(deploy): cloudflared tunnel config"
```

---

### Task D3: Cookie samesite + Capacitor CORS prep

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/api/session.py`

Capacitor WebViews load the app from `capacitor://localhost` (iOS) or `https://localhost` (Android), which most browsers treat as cross-site relative to `https://api.<domain>`. Cookie `samesite=lax` will then drop the cookie on every API call. Switching to `samesite=none; secure` fixes that.

- [ ] **Step 1: Add a configurable samesite to `Settings`**

In `backend/app/config.py`:

```python
    cookie_samesite: str = "lax"  # override to "none" in mobile prod
```

- [ ] **Step 2: Use it in `_set_session_cookie`**

In `backend/app/api/session.py`:

```python
def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_SESSION,
        token,
        httponly=True,
        samesite=settings.cookie_samesite,  # was "lax"
        secure=settings.cookie_secure,
        path="/",
    )
```

Also update `_clear_session_cookie` to pass the same flags so the browser actually deletes the cookie under HTTPS:

```python
def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        COOKIE_SESSION,
        path="/",
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )
```

- [ ] **Step 3: Validate via tests**

```bash
KATAGO_MOCK=true pytest -q
```

The default `cookie_samesite="lax"` keeps existing tests passing. Production sets `COOKIE_SAMESITE=none` via `~/.baduk.env`.

- [ ] **Step 4: Update the `~/.baduk.env` template in deploy README**

Already covered in Task D1 Step 3.

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/app/api/session.py
git commit -m "feat(session): cookie samesite is configurable for Capacitor"
```

---

### Task D4: SQLite → R2 backup script

**Files:**
- Create: `backend/deploy/r2_backup.sh`
- Modify: `backend/deploy/README.md`

- [ ] **Step 1: Install rclone**

```bash
brew install rclone
```

- [ ] **Step 2: Create an R2 bucket**

In the Cloudflare dashboard: R2 → Create bucket → name `baduk-backups`. Generate API tokens with R2 Read + Write.

- [ ] **Step 3: Configure rclone**

```bash
rclone config
```

Add a remote named `r2`, type `s3`, provider `Cloudflare`, paste the access key/secret/endpoint (from R2 dashboard).

- [ ] **Step 4: Create `backend/deploy/r2_backup.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

DB="data/baduk.db"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP="/tmp/baduk-${STAMP}.db"

# .backup is atomic and respects WAL.
sqlite3 "${DB}" ".backup '${TMP}'"
gzip -9 "${TMP}"
rclone copy "${TMP}.gz" "r2:baduk-backups/" --progress
rm -f "${TMP}.gz"

# Keep last 30 days
rclone delete --min-age 30d "r2:baduk-backups/"
```

```bash
chmod +x backend/deploy/r2_backup.sh
```

- [ ] **Step 5: Schedule via cron (or launchd)**

Add to `crontab -e`:

```
0 4 * * * /Users/<you>/projects/baduk/backend/deploy/r2_backup.sh >> /Users/<you>/Library/Logs/baduk-backup.log 2>&1
```

- [ ] **Step 6: Test once manually**

```bash
./backend/deploy/r2_backup.sh
rclone ls r2:baduk-backups/ | tail
```

Expected: a `baduk-<timestamp>.db.gz` listing.

- [ ] **Step 7: Restore drill (do once before launch)**

```bash
mkdir -p /tmp/restore-drill
rclone copy r2:baduk-backups/<latest>.db.gz /tmp/restore-drill/
gunzip /tmp/restore-drill/<latest>.db.gz
sqlite3 /tmp/restore-drill/<latest>.db "SELECT count(*) FROM games;"
```

Expected: a sane row count.

- [ ] **Step 8: Commit**

```bash
git add backend/deploy/r2_backup.sh backend/deploy/README.md
git commit -m "feat(deploy): nightly R2 backup with 30-day retention"
```

---

### Task D5: Production env runbook

**Files:**
- Modify: `backend/deploy/README.md`

- [ ] **Step 1: Add an "Environment variables" section**

```markdown
## ~/.baduk.env (required)

| Variable | Purpose |
|---|---|
| `APP_ENV=production` | Enables HSTS, secure cookie defaults |
| `SESSION_SECRET` | 32-byte random hex; rotate annually |
| `KATAGO_BIN_PATH` | Absolute path to `backend/katago/bin/katago` |
| `KATAGO_HUMAN_MODEL_PATH` | Absolute path to the .bin.gz model |
| `KATAGO_POOL_SIZE=4` | Pool worker count |
| `CORS_ORIGINS` | `https://<domain>,https://localhost,capacitor://localhost,ionic://localhost` |
| `COOKIE_SAMESITE=none` | Required for Capacitor WebViews |
| `CF_TRUSTED_PROXY=true` | Trust Cloudflare's CF-Connecting-IP |
| `DATABASE_URL=sqlite+aiosqlite:///./data/baduk.db` | (default) |

Generate `SESSION_SECRET`:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```
```

- [ ] **Step 2: Add a "First-launch checklist"**

```markdown
## First-launch checklist (do once)

- [ ] `./backend/katago/build_macos.sh` succeeds; `katago benchmark` shows >= 200 visits/s on M4
- [ ] `~/.baduk.env` populated
- [ ] launchd service loaded; `curl 127.0.0.1:8000/api/health` returns ok
- [ ] cloudflared service running; `curl https://api.<domain>/api/health` returns ok
- [ ] Cron entry installed for `r2_backup.sh`
- [ ] At least one R2 backup exists in the bucket
- [ ] One restore drill verified
- [ ] `tail -f ~/Library/Logs/baduk-api.log` shows JSON structlog lines
```

- [ ] **Step 3: Commit**

```bash
git add backend/deploy/README.md
git commit -m "docs(deploy): environment vars + first-launch checklist"
```

---

## Final Verification

After every task in Phase A–D is committed:

- [ ] **Local backend full suite passes**

```bash
cd backend && source .venv311/bin/activate
KATAGO_MOCK=true pytest --cov=app --cov-fail-under=80 -q
ruff check .
mypy app
```

Expected: all pass with coverage ≥ 80%.

- [ ] **Live backend smoke test through Cloudflare**

```bash
curl -s https://api.<domain>/api/health | python3 -m json.tool
curl -s -i https://api.<domain>/api/health | grep -E 'HSTS|Content-Security-Policy|X-Frame-Options'
```

Expected: 200 OK + all security headers present.

- [ ] **Concurrent live test (manual)**

Open two browsers (different profiles) at the *current* web frontend (`http://localhost:3000` or whatever Plan 2 brings up). Start two games simultaneously. Both must respond within 1.5s p95 even when both players move at the same time.

- [ ] **Tag the milestone**

```bash
git tag -a backend-launch-ready -m "Plan 1 complete — backend ready for mobile"
```

---

## Sign-off

Plan 1 is complete when **all** of the following are true:

- KataGo Metal builds and runs on the Mac mini
- 4-worker pool serves concurrent games (verified by `test_concurrent_games`)
- Strength is capped at 5d / 256 visits
- All P1 backend items (B1–B6) are committed
- WS race + heartbeat fixes (C1, C2) ship
- launchd, cloudflared, and R2 backup all auto-start on Mac mini reboot
- `https://api.<domain>/api/health` returns 200 with security headers from a different network

Plan 2 (Capacitor mobile shell) starts from this baseline.
