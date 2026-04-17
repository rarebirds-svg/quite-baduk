# KataGo Adapter Review

**Reviewer:** KataGo-Reviewer
**Date:** 2026-04-17

## Test Execution

Attempted:

```
cd /Users/daegong/projects/baduk/backend
source .venv311/bin/activate
pytest tests/katago/ --cov=app.core.katago --cov-report=term-missing -v
```

Execution was blocked in this review session ("Permission to use Bash has been denied") so coverage numbers could not be produced. Review proceeded as a static audit; the tests should be run manually before sign-off.

**Test suite inventory** (static):

- `tests/katago/test_analysis.py` — 7 cases: empty, single, multi-sorted, top-move-winrate, ownership (361), ownership-wrong-count-ignored, last-line-wins.
- `tests/katago/test_gtp_parser.py` — 7 cases: success, error, with id, empty body, multiline, garbage, empty.
- `tests/katago/test_strength.py` — all 12 ranks parametrized, unknown-raises, frozen.
- `tests/katago/test_mock_adapter.py` — 8 async cases: start/stop, play/board, genmove top-left, genmove sequential, clear_board reset, undo, komi+profile, analyze returns hints, final_score.

**Uncovered behaviors (no tests exist):**

- `KataGoAdapter.send()` restart-after-failure path (the most safety-critical branch).
- `_replay_state` end-to-end replay after simulated subprocess death.
- Timeout propagation → `TimeoutError` → restart → reissue.
- Concurrency: spec §11.3 calls for "동시 5개 → 순차 처리" (5 concurrent requests serialized). No such test.
- `analyze()` end-to-end (the command wiring is almost certainly broken — see Critical #1).
- `_send_raw` with partial-line / multi-chunk stdout reads.

Coverage of `app.core.katago` will appear high (parser + mock + strength are thoroughly tested), but the real adapter's subprocess/lock/restart code is almost entirely unexercised. Coverage tools will report high line coverage while the risky paths remain untested.

---

## Findings

### Critical

**C1. `analyze()` will time out — `kata-analyze` is a streaming command with no terminator.**

File: `backend/app/core/katago/adapter.py:255-261`

```python
async def analyze(self, max_visits: int = 100) -> AnalysisResult:
    r = await self.send(f"kata-analyze interval 1000 maxmoves 5 ownership true", timeout=self.timeout)
    return parse_analysis(r.body)
```

`kata-analyze` emits `info move ...` lines continuously at `interval` centiseconds and only terminates (with the blank-line GTP response) when KataGo receives another GTP command (typically an empty line or any follow-up). `_send_raw` waits for `\n\n`, which never arrives, so every `analyze()` call will hit the 60 s timeout, trigger a restart, and still fail. This also orphans the subprocess every call.

The correct pattern is either:

- Use `kata-genmove_analyze` + read lines until the final `play` response, discarding the analysis stream; or
- Write `kata-analyze ...\n`, read until we have N snapshots, then write `\n` (empty command / `protocol_version`) to stop the stream, then consume the terminator; or
- Use KataGo's JSON analysis engine (`katago analysis`) instead of GTP for analysis — this is actually the documented approach and would simplify parsing.

The spec (§5.3, §5.5) relies on analysis working for the hint and review flows. This blocks the `hint` and `analyze` endpoints end-to-end. **Must fix before backend integration.**

**C2. `stop()` races with in-flight `send()`.**

File: `backend/app/core/katago/adapter.py:116-135`

```python
async def stop(self) -> None:
    if not self._proc:
        return
    try:
        if self._proc.returncode is None:
            try:
                await self._send_raw("quit")
            ...
```

`stop()` writes `quit` directly via `_send_raw`, bypassing the lock. If a caller holds `_lock` running `genmove`, `stop()` will interleave bytes on stdin, corrupt the GTP stream, and then may set `_proc = None` while the other coroutine is still awaiting a readline on the same stream. This is a data-race and a classic source of AsyncIO "readline on closed transport" exceptions during shutdown.

Fix: acquire `self._lock` (or a dedicated shutdown lock) and/or set a "stopping" flag that `_ensure_alive` respects so in-flight sends fail fast.

### Important

**I1. `_replay_state` errors are silently swallowed and corrupt bookkeeping.**

File: `backend/app/core/katago/adapter.py:147-157`

Each replay step calls `_send_raw` (no lock, no restart, no retry, no error check). If KataGo rejects e.g. an unknown `humanSLProfile` after a build change, the exception propagates out of `_ensure_alive`, which leaks the `_starting = True` state path through `finally` (OK) but leaves `self._proc` alive without the replayed board state. The next `send()` call will believe the process is healthy and resume playing against a clean KataGo — effectively a silent de-sync.

Recommendations:
1. Check `GTPResult.ok` and raise on failure so callers observe replay failure.
2. On replay failure, call `self._proc.kill()` and re-raise so `send()`'s retry-or-fail policy is consistent.
3. Add structured logging around each replay step (the spec §10.7 requires `structlog`).

**I2. `send()` retry reissues the command but `_replay_state` is not retry-protected.**

File: `backend/app/core/katago/adapter.py:189-199`

The `except ... self._proc = None; await self._ensure_alive(); return await self._send_raw(...)` path calls `_ensure_alive` which calls `_replay_state`, which calls `_send_raw`. If any replay step itself raises (timeout, broken pipe), that exception leaks out of `send()` without a second retry. The spec §10.1 promises "프로세스 재기동 → 활성 대국마다 `clear_board` → `komi` → 저장된 moves 순서 재생". A single flaky start during replay and the request fails with no further retry. Policy should be: full restart + replay is one atomic attempt; on partial replay failure, either kill and retry once, or propagate a well-typed error the Game Service can surface as "AI 재접속 중".

**I3. Timeout orphan: stale bytes on stdout after timeout.**

File: `backend/app/core/katago/adapter.py:183-186`

On `asyncio.wait_for` timeout, the inner `readline()` is cancelled but KataGo may still write the delayed response to stdout. The current code handles this only indirectly by nulling `_proc` in `send()`'s except block. That drops the still-running KataGo (leak until Python GC kills stdin), and *only* `BrokenPipeError`/`RuntimeError`/`TimeoutError` hit the restart path — other IO exceptions (e.g. `LimitOverrunError`, `IncompleteReadError`) won't trigger restart and will surface as 500s.

Recommend widening the except list to `OSError, asyncio.IncompleteReadError, asyncio.LimitOverrunError` and explicitly `self._proc.kill()` before nulling.

**I4. `_send_raw` buffer unbounded; `readline()` default limit is 64 KiB.**

File: `backend/app/core/katago/adapter.py:172-181`

For 19×19 ownership in a multi-move snapshot (say 10 moves × 361 floats), a single `kata-analyze` line can easily exceed 64 KiB and raise `LimitOverrunError`. Two fixes:

1. Construct the subprocess streams with a raised `limit=` (via custom `StreamReader` or `create_subprocess_exec` via `asyncio.subprocess.PIPE` + post-wrap). Python ≥ 3.11 supports `limit` through `asyncio.create_subprocess_exec`? Actually no — workaround is to read in chunks with `read(N)` and split on `\n\n`.
2. Use `read(n)` loops instead of `readline()` for analysis-heavy responses.

Combined with C1, this should be fixed as part of a proper analysis-stream design.

**I5. `load_sgf_text` is unimplemented but required by spec §5.5.**

File: `backend/app/core/katago/adapter.py:263-266`

Spec §5.5 "리뷰·분석 모드: KataGo에 SGF 로드 + `kata-analyze 100` → 승률·ownership·상위수 파싱". The analyze flow needs either SGF loading (`loadsgf /path`) or a replay via `clear_board` + `play` loop. The TODO comment says "Use clear_board + play() loop" — fine, but then the `Game Service` must orchestrate that, and this should be documented in the adapter's public API or implemented here (e.g. `replay_moves(moves: list[tuple[color, coord]])`). Otherwise the Game Service will re-implement logic that already lives in `_replay_state`.

**I6. Mock `set_boardsize` silently lies.**

File: `backend/app/core/katago/mock.py:44-46`

```python
async def set_boardsize(self, size: int) -> None:
    self.board_size = size
    self.board = Board()
```

`Board()` is hardcoded 19×19 (`BOARD_SIZE` constant). If a test calls `set_boardsize(13)`, `self.board_size = 13` but the underlying `Board` is still 19×19, so `genmove` iterates `range(13)` over a 19×19 board and never visits cells `(13..18, *)`. For V1 the spec pins the game to 19×19 (§1.3 excludes 9×9/13×13), so this is inert — but the mock will quietly mislead any test that tries other sizes. Either reject non-19 sizes explicitly, or make `Board` size-parametrized.

**I7. No adapter-level tests for restart / replay / concurrency.**

Spec §11.3 explicitly requires: "프로세스: 시작·강제종료 후 재기동·상태 복원" and "요청 큐: 동시 5개 → 순차 처리". Neither is covered. Recommend adding tests that:

1. Monkey-patch `asyncio.create_subprocess_exec` with a fake subprocess that can be forced to exit, then assert `send()` restarts and replays `boardsize/komi/profile/plays`.
2. Launch 5 concurrent `send()` tasks against a stub subprocess and assert they are serialized (observed order on the fake stdin matches invocation order).
3. Inject a slow response to verify the 60 s timeout path and subsequent restart.

Without these, the most load-bearing adapter logic is effectively untested.

### Minor

**M1. `parse_gtp` id parsing accepts ambiguous `=42pass`.**

File: `backend/app/core/katago/adapter.py:51-60`

If the GTP response is `=42 pass\n\n`, the parser correctly peels the id. But `=42pass` (no space) would also be parsed as id=42, body="pass". GTP standard requires whitespace between id and body; accepting the tight form is harmless and existing test `test_parse_with_id` exercises the spec case only.

**M2. `analyze()` hard-codes `interval 1000 maxmoves 5`, ignores the `max_visits` parameter.**

File: `backend/app/core/katago/adapter.py:255-261`

The function accepts `max_visits=100` but never forwards it. Either remove the parameter or compose the GTP command with `maxmoves` / `allow` etc. accordingly.

**M3. `MockKataGoAdapter.clear_board` does not reset `self.board_size`.**

File: `backend/app/core/katago/mock.py:40-42`

Minor consistency issue (resets board to default 19×19 shape but keeps `self.board_size` value). Tied to I6.

**M4. `MockKataGoAdapter.play` silently accepts invalid coords.**

File: `backend/app/core/katago/mock.py:58-68`

If `gtp_to_xy` returns `None` (only "pass") or raises, the `if xy is None: return` path handles pass; but invalid coordinates will `raise ValueError` from `gtp_to_xy`, not the caught `None`. Mock should either validate explicitly (and raise a `ValueError` that parallels real KataGo's "illegal move") or catch and log. Currently exceptions propagate — probably fine but inconsistent with the real adapter, which returns `ValueError(f"KataGo rejected play ...")`.

**M5. `__init__.py` import order risks circular imports.**

File: `backend/app/core/katago/__init__.py:2`

`from app.core.katago.adapter import GTPResult, KataGoAdapter, parse_gtp` — `adapter.py` imports from `app.core.katago.analysis` and `app.core.katago.strength` (fine). `mock.py` imports `GTPResult` from `adapter`. Working today; watch if future changes make `adapter` import `mock` for any reason.

**M6. `genmove` body strip lowercases implicitly only when comparing to `"pass"/"resign"`.**

File: `backend/app/core/katago/adapter.py:243-246`

`r.body.strip()` is stored without case-normalization. KataGo returns moves as upper-case (`Q16`) and `pass`/`resign` as lower-case. The comparison `move.lower() not in ("pass", "resign")` is correct. But the stored coord in `_replay.plays` keeps KataGo's casing; `_replay_state` sends it back verbatim, which KataGo accepts. No bug, but worth a comment: the tuple is GTP-format, not normalized.

**M7. `set_profile` updates `_replay.profile` only after both commands succeed, but if the second (`maxVisits`) fails, `humanSLProfile` is already applied to KataGo without being recorded.**

File: `backend/app/core/katago/adapter.py:216-226`

Edge case — after partial failure, the in-memory `_replay.profile` is stale relative to the live process. After a restart-and-replay, state will be consistent. Low severity.

**M8. `config.cfg` is minimal (4 settings).**

File: `backend/katago/config.cfg`

Works, but omits settings useful for determinism and CI:

- `reportAnalysisWinratesAs = BLACK` (or `SIDETOMOVE`) — affects how `kata-analyze` winrate is oriented. Currently KataGo default is `SIDETOMOVE`, and `analysis.py` assumes side-to-move, so leaving default is fine — but document it.
- `allowResignation = true|false` — if `false`, `genmove` never returns `resign`, which is probably desired for the human-SL UX.
- `resignThreshold = -0.9` — if resignation is enabled.
- `maxTime = 5.0` — per-move time cap in seconds; without it, `numSearchThreads=2` + `maxVisits=800` can easily exceed the 60 s adapter timeout on slow CPUs for strong profiles (`7d` = 512 visits).

**M9. `download_model.sh` does not verify checksum.**

File: `backend/katago/download_model.sh`

Given the model is downloaded fresh on every first container boot, a checksum (sha256) verification would catch truncated downloads and detect upstream asset changes. 80 MB silent corruption would break KataGo with opaque errors.

**M10. Dockerfile pins `KATAGO_VER=1.15.3` but downloads a v1.x asset at runtime.**

File: `backend/Dockerfile:8`

The build pins the binary version, which is good. Suggest also pinning or digest-verifying the model asset in `download_model.sh` to keep the human-SL behavior stable across deploys.

**M11. `config.cfg` uses `logToStderr = true` but adapter discards stderr (`DEVNULL`).**

File: `backend/app/core/katago/adapter.py:113`, `backend/katago/config.cfg:2`

Operational telemetry is thrown away. Spec §10.7 wants `structlog`-formatted observability including "KataGo 명령·응답 요약". Consider piping stderr through a background consumer that re-emits via `structlog` at `debug` level (rate-limited), or at least keeping the last N lines in a ring buffer for `/api/health` diagnostics.

**M12. `genmove` after `resign` still records nothing — fine — but no test.**

File: `backend/app/core/katago/adapter.py:243-247`

The mock never returns "resign", so the pass/resign branch is uncovered. Worth a small unit test with a subclass that injects a resign response.

---

## Spec Alignment Checklist

| Spec requirement | Status |
|---|---|
| Human-SL model `b18c384nbt-humanv0` | Met — `config.py:13`, `download_model.sh:4` |
| 12-rank mapping 18k→7d | Met exactly — `strength.py` matches §6.2 table |
| GTP via subprocess | Met — `asyncio.create_subprocess_exec` with PIPE |
| Async single-lock serialization | Met — `asyncio.Lock` in `send()` |
| Auto-restart on crash | Partially met — one retry; does not handle `_replay_state` partial failure (I2) |
| State replay (boardsize/komi/profile/plays) | Met — `_replay_state` reapplies all 4; handicap via `play()` is correctly covered by `plays` |
| 60 s default timeout | Met — `katago_timeout_sec = 60` in `config.py` |
| `kata-analyze` parser producing winrate/topMoves/ownership | Parser met; caller broken (C1) |
| Mock adapter for tests | Met — deterministic; has I6 caveat on non-19 sizes |
| `KATAGO_MOCK=true` env | Partial — `config.py` exposes it, `download_model.sh` honors it, but no adapter factory actually reads the flag to choose real vs mock. There must be a selector (`get_katago_adapter()` factory) somewhere the Game Service imports; it is **not** in this review scope's files. Verify a factory exists (suggested location: `app/core/katago/__init__.py` or `services/game_service.py`). |

---

## Verdict

**CHANGES_REQUIRED**

Blocking items before merge:

- **C1**: `analyze()` is wired to an unterminated GTP streaming command and will always time out. This breaks `/hint` and `/analyze` endpoints.
- **C2**: `stop()` racing `send()` can corrupt the GTP stream at shutdown.
- **I1, I2**: Replay-path error handling leaves the adapter in silently-desynced states.
- **I7**: The restart/replay/concurrency paths mandated by spec §11.3 have zero coverage; at least two integration tests are required before this can be trusted in production.

Strong points worth preserving:

- Strength mapping is exact to spec and nicely structured.
- GTP parser and analysis parser are small, pure, and well-tested.
- Mock adapter is deterministic and suitable for API-layer tests given the 19×19 V1 scope.
- Dockerfile + download script handle the model correctly, and `KATAGO_MOCK` short-circuit at image build is clean.

**Critical issues count: 2** (C1, C2).
**Important issues count: 7** (I1–I7).
**Minor issues count: 12** (M1–M12).

**STATUS:** review complete; test suite not executed due to sandboxed bash.
