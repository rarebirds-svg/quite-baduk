"""KataGo GTP adapter: manages the KataGo subprocess and GTP protocol.

Design:
- asyncio.subprocess for stdin/stdout
- single asyncio.Lock to serialize commands (GTP is request/response)
- automatic restart if process dies
- timeouts on each command
- optional state replay for recovery after restart
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.config import settings
from app.core.katago.analysis import AnalysisResult, parse_analysis
from app.core.katago.strength import StrengthConfig

if TYPE_CHECKING:
    pass


@dataclass
class GTPResult:
    ok: bool
    body: str
    id: int | None = None


def parse_gtp(response: str) -> GTPResult:
    """Parse a GTP response string.

    Format:
      '=[id] <body>\\n\\n'  → success
      '?[id] <error>\\n\\n' → error
      body may span multiple lines; terminator is '\\n\\n'.
    """
    text = response.strip("\r\n ")
    if not text:
        return GTPResult(ok=False, body="")
    status_char = text[0]
    if status_char not in ("=", "?"):
        return GTPResult(ok=False, body=text)
    ok = status_char == "="
    rest = text[1:].lstrip()

    # Optional id prefix
    id_val: int | None = None
    if rest and rest[0].isdigit():
        # peel off digits until space or newline
        i = 0
        while i < len(rest) and rest[i].isdigit():
            i += 1
        try:
            id_val = int(rest[:i])
            rest = rest[i:].lstrip()
        except ValueError:
            pass

    return GTPResult(ok=ok, body=rest, id=id_val)


@dataclass
class _ReplayState:
    """Commands to replay after a process restart to restore board state."""
    boardsize: int = 19
    komi: float | None = None
    profile: tuple[str, int] | None = None  # (profile_name, max_visits)
    plays: list[tuple[str, str]] = field(default_factory=list)  # [(color, coord)]


class KataGoAdapter:
    """Async adapter around the KataGo GTP subprocess."""

    def __init__(
        self,
        *,
        bin_path: str | None = None,
        model_path: str | None = None,
        config_path: str | None = None,
        human_model_path: str | None = None,
        timeout_sec: float | None = None,
    ) -> None:
        self.bin_path = bin_path or settings.katago_bin_path
        self.model_path = model_path or settings.katago_model_path
        self.config_path = config_path or settings.katago_config_path
        self.human_model_path = (
            human_model_path if human_model_path is not None else settings.katago_human_model_path
        )
        self.timeout = float(timeout_sec or settings.katago_timeout_sec)

        self._proc: asyncio.subprocess.Process | None = None
        self._lock = asyncio.Lock()
        self._replay = _ReplayState()
        self._starting = False

    # ── lifecycle ─────────────────────────────────────────────────────────────

    @property
    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    async def _spawn(self) -> None:
        """Raw subprocess spawn. Does not replay cached state — callers must
        use :meth:`start` or :meth:`_ensure_alive` to get a consistent board.
        """
        if self.is_alive:
            return
        args = [
            self.bin_path, "gtp",
            "-model", self.model_path,
            "-config", self.config_path,
        ]
        if self.human_model_path:
            args.extend(["-human-model", self.human_model_path])
        self._proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

    async def start(self) -> None:
        """Public, idempotent. Spawns the subprocess if necessary AND
        replays any cached :class:`_ReplayState` so the KataGo board always
        matches what this adapter has been told to play.

        This is the only safe public entry — direct ``_spawn`` calls would
        leave KataGo on a blank board even though the adapter's own history
        has progressed, which would make later ``play``/``genmove`` return
        coords illegal against the rules engine.
        """
        await self._ensure_alive()

    async def stop(self) -> None:
        async with self._lock:
            if not self._proc:
                return
            try:
                if self._proc.returncode is None:
                    try:
                        await self._send_raw("quit")
                    except Exception:
                        pass
                    try:
                        await asyncio.wait_for(self._proc.wait(), timeout=3.0)
                    except TimeoutError:
                        self._proc.terminate()
                        try:
                            await asyncio.wait_for(self._proc.wait(), timeout=2.0)
                        except TimeoutError:
                            self._proc.kill()
                            await self._proc.wait()
            finally:
                self._proc = None

    async def _ensure_alive(self) -> None:
        if self.is_alive or self._starting:
            return
        self._starting = True
        try:
            await self._spawn()
            await self._replay_state()
        finally:
            self._starting = False

    async def _replay_state(self) -> None:
        """Re-apply boardsize/komi/profile/plays after a restart."""
        await self._send_raw(f"boardsize {self._replay.boardsize}")
        if self._replay.komi is not None:
            await self._send_raw(f"komi {self._replay.komi}")
        if self._replay.profile:
            profile, visits = self._replay.profile
            await self._send_raw(f"kata-set-param humanSLProfile {profile}")
            await self._send_raw(f"kata-set-param maxVisits {visits}")
        for color, coord in self._replay.plays:
            await self._send_raw(f"play {color} {coord}")

    # ── raw I/O ───────────────────────────────────────────────────────────────

    async def _send_raw(self, cmd: str, timeout: float | None = None) -> GTPResult:
        """Send a command and read until we get a complete GTP response (ends with '\\n\\n')."""
        if self._proc is None or self._proc.stdin is None or self._proc.stdout is None:
            raise RuntimeError("KataGo process not running")
        line = (cmd.strip() + "\n").encode()
        self._proc.stdin.write(line)
        await self._proc.stdin.drain()

        buffer = b""
        deadline = timeout or self.timeout

        async def _read_until_blank() -> bytes:
            nonlocal buffer
            while True:
                chunk = await self._proc.stdout.readline()  # type: ignore[union-attr]
                if not chunk:
                    raise RuntimeError("KataGo closed stdout")
                buffer += chunk
                # GTP responses end with a blank line
                if buffer.endswith(b"\n\n") or buffer.endswith(b"\r\n\r\n"):
                    return buffer

        try:
            data = await asyncio.wait_for(_read_until_blank(), timeout=deadline)
        except TimeoutError:
            raise TimeoutError(f"KataGo timed out on: {cmd}")
        return parse_gtp(data.decode("utf-8", errors="replace"))

    async def send(self, cmd: str, timeout: float | None = None) -> GTPResult:
        """Public send with lock + restart protection."""
        async with self._lock:
            await self._ensure_alive()
            try:
                return await self._send_raw(cmd, timeout=timeout)
            except (RuntimeError, BrokenPipeError, TimeoutError):
                # Try restart once
                self._proc = None
                await self._ensure_alive()
                return await self._send_raw(cmd, timeout=timeout)

    # ── high-level GTP helpers ────────────────────────────────────────────────

    async def clear_board(self) -> None:
        await self.send("clear_board")
        self._replay.plays.clear()

    async def set_boardsize(self, size: int) -> None:
        await self.send(f"boardsize {size}")
        self._replay.boardsize = size
        self._replay.plays.clear()

    async def set_komi(self, komi: float) -> None:
        await self.send(f"komi {komi}")
        self._replay.komi = komi

    async def set_profile(self, profile_or_config: StrengthConfig | str, max_visits: int | None = None) -> None:
        if isinstance(profile_or_config, StrengthConfig):
            profile = profile_or_config.human_sl_profile
            visits = profile_or_config.max_visits
        else:
            profile = profile_or_config
            assert max_visits is not None
            visits = max_visits
        # humanSLProfile only works when the Human-SL model is loaded.
        # On standard models KataGo rejects the parameter — tolerate that
        # and still fall back to visit-count strength control.
        r = await self.send(f"kata-set-param humanSLProfile {profile}")
        if not r.ok:
            pass  # standard model without human-SL support — visits only
        await self.send(f"kata-set-param maxVisits {visits}")
        self._replay.profile = (profile, visits)

    async def play(self, color: str, coord: str) -> None:
        r = await self.send(f"play {color} {coord}")
        if not r.ok:
            raise ValueError(f"KataGo rejected play {color} {coord}: {r.body}")
        self._replay.plays.append((color, coord))

    async def undo(self) -> None:
        await self.send("undo")
        if self._replay.plays:
            self._replay.plays.pop()

    async def genmove(self, color: str) -> str:
        r = await self.send(f"genmove {color}")
        if not r.ok:
            raise ValueError(f"genmove failed: {r.body}")
        move = r.body.strip()
        if move.lower() not in ("pass", "resign"):
            # record so replay stays accurate
            self._replay.plays.append((color, move))
        return move

    async def final_score(self) -> str:
        r = await self.send("final_score")
        if not r.ok:
            raise ValueError(f"final_score failed: {r.body}")
        return r.body.strip()

    async def analyze(self, *, side: str = "B", max_visits: int = 100) -> AnalysisResult:
        """Run a one-shot analysis and return best moves + ownership.

        kata-analyze streams 'info move ...' lines until interrupted. To stop
        it we send a bare newline (the GTP-idiomatic way), then drain the
        final '= ...\\n\\n' response so subsequent commands stay in-sync with
        the subprocess pipe.

        The side argument is required by this KataGo build: omitting it makes
        the engine accept and immediately terminate the analyze with no info
        lines, so the caller gets zero hints. Pass state.to_move.
        """
        async with self._lock:
            await self._ensure_alive()
            if self._proc is None or self._proc.stdin is None or self._proc.stdout is None:
                return AnalysisResult()

            # Start streaming analysis. `interval 20` = 200ms cadence.
            # We cannot pass `maxvisits` to kata-analyze — at low visits the
            # engine completes the search before emitting any info lines and
            # we'd get zero hints. Instead, map `max_visits` to a wall-clock
            # deadline (≈ 20 ms per requested visit; clamped to [0.3s, 5.0s]),
            # and interrupt with a blank newline once we've collected enough.
            deadline_s = max(0.3, min(5.0, max_visits * 0.02))
            cmd = f"kata-analyze {side} interval 20 maxmoves 5 ownership true\n"
            self._proc.stdin.write(cmd.encode())
            await self._proc.stdin.drain()

            collected: list[str] = []
            deadline = asyncio.get_event_loop().time() + deadline_s
            pipe_healthy = True
            try:
                while asyncio.get_event_loop().time() < deadline:
                    remaining = max(0.05, deadline - asyncio.get_event_loop().time())
                    try:
                        line = await asyncio.wait_for(
                            self._proc.stdout.readline(), timeout=remaining
                        )
                    except TimeoutError:
                        break
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace")
                    if text.strip().startswith("info move"):
                        collected.append(text)
            finally:
                # Stop the analyze stream with a bare newline (standard GTP).
                try:
                    self._proc.stdin.write(b"\n")
                    await self._proc.stdin.drain()
                except Exception:
                    pipe_healthy = False
                # Drain any trailing 'info move' lines plus the final
                # GTP response ('= ...\\n\\n' or '? ...\\n\\n').
                buffer = b""
                saw_terminator = False
                try:
                    while True:
                        line = await asyncio.wait_for(
                            self._proc.stdout.readline(), timeout=1.5
                        )
                        if not line:
                            break
                        buffer += line
                        text = line.decode("utf-8", errors="replace")
                        if text.strip().startswith("info move"):
                            collected.append(text)
                        if buffer.endswith(b"\n\n") or buffer.endswith(b"\r\n\r\n"):
                            saw_terminator = True
                            break
                except TimeoutError:
                    pass
                # If we failed to resync the pipe, force a restart so the
                # next caller gets a clean state instead of reading stale bytes.
                if not saw_terminator or not pipe_healthy:
                    try:
                        if self._proc is not None:
                            self._proc.terminate()
                    except Exception:
                        pass
                    self._proc = None

            return parse_analysis("".join(collected), board_size=self._replay.boardsize)

    async def load_sgf_text(self, sgf: str) -> None:
        # loadsgf requires a file path; a simpler approach is clear_board + replay moves.
        # SGF replay is owned by caller; this method is a stub for future extension.
        raise NotImplementedError("Use clear_board + play() loop to replay a game")

    async def version(self) -> str:
        r = await self.send("version")
        return r.body
