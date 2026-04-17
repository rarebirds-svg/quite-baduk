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
from typing import TYPE_CHECKING, Any

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
        timeout_sec: float | None = None,
    ) -> None:
        self.bin_path = bin_path or settings.katago_bin_path
        self.model_path = model_path or settings.katago_model_path
        self.config_path = config_path or settings.katago_config_path
        self.timeout = float(timeout_sec or settings.katago_timeout_sec)

        self._proc: asyncio.subprocess.Process | None = None
        self._lock = asyncio.Lock()
        self._replay = _ReplayState()
        self._starting = False

    # ── lifecycle ─────────────────────────────────────────────────────────────

    @property
    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    async def start(self) -> None:
        if self.is_alive:
            return
        args = [
            self.bin_path, "gtp",
            "-model", self.model_path,
            "-config", self.config_path,
        ]
        self._proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

    async def stop(self) -> None:
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
                except asyncio.TimeoutError:
                    self._proc.terminate()
                    try:
                        await asyncio.wait_for(self._proc.wait(), timeout=2.0)
                    except asyncio.TimeoutError:
                        self._proc.kill()
                        await self._proc.wait()
        finally:
            self._proc = None

    async def _ensure_alive(self) -> None:
        if self.is_alive or self._starting:
            return
        self._starting = True
        try:
            await self.start()
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
        except asyncio.TimeoutError:
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
        await self.send(f"kata-set-param humanSLProfile {profile}")
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

    async def analyze(self, max_visits: int = 100) -> AnalysisResult:
        # kata-analyze is async/streaming; use a single snapshot via lz-analyze-like call
        # Use 'kata-analyze interval 0 maxmoves 10' then stop manually.
        # Simpler: use 'kata-genmove_analyze' is complex. Instead, send kata-raw analysis.
        # We fall back to: playouts via kata-analyze with minimal time.
        r = await self.send(f"kata-analyze interval 1000 maxmoves 5 ownership true", timeout=self.timeout)
        return parse_analysis(r.body)

    async def load_sgf_text(self, sgf: str) -> None:
        # loadsgf requires a file path; a simpler approach is clear_board + replay moves.
        # SGF replay is owned by caller; this method is a stub for future extension.
        raise NotImplementedError("Use clear_board + play() loop to replay a game")

    async def version(self) -> str:
        r = await self.send("version")
        return r.body
