"""Tests for the KataGoAdapter GTP protocol layer.

The real adapter spawns a subprocess and pipes GTP commands over stdin/stdout.
These tests substitute a fake `_proc` with asyncio StreamReader/Writer-like
objects that scripted GTP responses can be queued onto, so we can exercise
`_send_raw`, the high-level wrappers (`play`, `undo`, `genmove`, …), the
restart-on-error path in `send`, and the lifecycle in `start` / `stop` —
none of which the mock adapter ever exercises.
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.katago.adapter import KataGoAdapter, parse_gtp

# ─── parse_gtp covers ─────────────────────────────────────────────────────────


def test_parse_gtp_success_with_id() -> None:
    r = parse_gtp("=12 OK\n\n")
    assert r.ok is True
    assert r.id == 12
    assert r.body == "OK"


def test_parse_gtp_error_with_body() -> None:
    r = parse_gtp("? illegal move\n\n")
    assert r.ok is False
    assert r.body == "illegal move"
    assert r.id is None


def test_parse_gtp_blank_body_is_failure() -> None:
    r = parse_gtp("\n\n")
    assert r.ok is False
    assert r.body == ""


def test_parse_gtp_unknown_status_char() -> None:
    """Anything not starting with '=' or '?' is treated as failure (defensive)."""
    r = parse_gtp("!! garbage\n\n")
    assert r.ok is False


# ─── helpers: a scriptable subprocess ─────────────────────────────────────────


class _FakeStdin:
    """Mimic asyncio.StreamWriter: collects writes; drain is a no-op."""

    def __init__(self) -> None:
        self.buffer = bytearray()

    def write(self, data: bytes) -> None:
        self.buffer.extend(data)

    async def drain(self) -> None:
        return None


class _FakeStdout:
    """Asyncio queue dressed as a StreamReader, returning pre-scripted lines."""

    def __init__(self, lines: list[bytes]) -> None:
        self._q: asyncio.Queue[bytes] = asyncio.Queue()
        for line in lines:
            self._q.put_nowait(line)

    async def readline(self) -> bytes:
        return await self._q.get()

    def feed(self, line: bytes) -> None:
        self._q.put_nowait(line)


def _make_fake_proc(lines: list[bytes]) -> Any:
    """Build a Mock that quacks like asyncio.subprocess.Process."""
    proc = Mock()
    proc.returncode = None
    proc.stdin = _FakeStdin()
    proc.stdout = _FakeStdout(lines)
    proc.terminate = Mock()
    proc.kill = Mock()
    proc.wait = AsyncMock(return_value=0)
    return proc


def _attach(adapter: KataGoAdapter, proc: Any) -> None:
    """Bypass _spawn — simulate a process already running."""
    adapter._proc = proc  # type: ignore[assignment]


# ─── _send_raw + send paths ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_raw_round_trips_a_response() -> None:
    adapter = KataGoAdapter()
    _attach(adapter, _make_fake_proc([b"= ok\n", b"\n"]))
    r = await adapter._send_raw("boardsize 19")
    assert r.ok is True
    # The command should have been written verbatim with a trailing newline.
    written = bytes(adapter._proc.stdin.buffer)  # type: ignore[union-attr]
    assert written == b"boardsize 19\n"


@pytest.mark.asyncio
async def test_send_raw_handles_crlf_terminator() -> None:
    adapter = KataGoAdapter()
    _attach(adapter, _make_fake_proc([b"= done\r\n", b"\r\n"]))
    r = await adapter._send_raw("clear_board")
    assert r.ok is True
    assert "done" in r.body


@pytest.mark.asyncio
async def test_send_raw_raises_on_closed_stdout() -> None:
    adapter = KataGoAdapter()
    _attach(adapter, _make_fake_proc([b""]))  # empty line → EOF semantics
    with pytest.raises(RuntimeError):
        await adapter._send_raw("anything")


@pytest.mark.asyncio
async def test_send_raw_raises_when_proc_missing() -> None:
    adapter = KataGoAdapter()
    adapter._proc = None
    with pytest.raises(RuntimeError):
        await adapter._send_raw("anything")


@pytest.mark.asyncio
async def test_send_restarts_on_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """If `_send_raw` raises, `send` restarts the subprocess once and retries."""
    adapter = KataGoAdapter()

    calls = {"raw": 0, "ensure": 0}

    async def flaky_send_raw(cmd: str, timeout: float | None = None) -> Any:
        calls["raw"] += 1
        if calls["raw"] == 1:
            raise RuntimeError("pipe closed")
        from app.core.katago.adapter import GTPResult
        return GTPResult(ok=True, body="restarted")

    async def fake_ensure() -> None:
        calls["ensure"] += 1
        adapter._proc = _make_fake_proc([])

    monkeypatch.setattr(adapter, "_send_raw", flaky_send_raw)
    monkeypatch.setattr(adapter, "_ensure_alive", fake_ensure)

    r = await adapter.send("genmove B")
    assert r.ok is True
    assert calls["raw"] == 2  # original + retry
    assert calls["ensure"] == 2  # initial + restart


# ─── high-level wrappers update _replay state ─────────────────────────────────


def _stub_send(adapter: KataGoAdapter, body: str = "") -> list[str]:
    """Replace .send with a stub that records issued commands."""
    sent: list[str] = []
    from app.core.katago.adapter import GTPResult

    async def fake_send(cmd: str, timeout: float | None = None) -> GTPResult:
        sent.append(cmd)
        return GTPResult(ok=True, body=body)

    adapter.send = fake_send  # type: ignore[assignment]
    return sent


@pytest.mark.asyncio
async def test_clear_board_resets_replay_history() -> None:
    adapter = KataGoAdapter()
    adapter._replay.plays = [("B", "Q16")]
    sent = _stub_send(adapter)
    await adapter.clear_board()
    assert sent == ["clear_board"]
    assert adapter._replay.plays == []


@pytest.mark.asyncio
async def test_set_boardsize_updates_replay() -> None:
    adapter = KataGoAdapter()
    adapter._replay.plays = [("B", "Q16")]  # should be cleared
    sent = _stub_send(adapter)
    await adapter.set_boardsize(13)
    assert sent == ["boardsize 13"]
    assert adapter._replay.boardsize == 13
    assert adapter._replay.plays == []


@pytest.mark.asyncio
async def test_set_komi_updates_replay() -> None:
    adapter = KataGoAdapter()
    sent = _stub_send(adapter)
    await adapter.set_komi(7.5)
    assert sent == ["komi 7.5"]
    assert adapter._replay.komi == 7.5


@pytest.mark.asyncio
async def test_play_appends_replay_entry() -> None:
    adapter = KataGoAdapter()
    sent = _stub_send(adapter)
    await adapter.play("B", "Q16")
    assert sent == ["play B Q16"]
    assert adapter._replay.plays == [("B", "Q16")]


@pytest.mark.asyncio
async def test_play_raises_when_engine_rejects() -> None:
    adapter = KataGoAdapter()
    from app.core.katago.adapter import GTPResult

    async def fake_send(cmd: str, timeout: float | None = None) -> GTPResult:
        return GTPResult(ok=False, body="illegal move")

    adapter.send = fake_send  # type: ignore[assignment]
    with pytest.raises(ValueError, match="rejected"):
        await adapter.play("B", "Q16")


@pytest.mark.asyncio
async def test_undo_pops_last_play() -> None:
    adapter = KataGoAdapter()
    adapter._replay.plays = [("B", "Q16"), ("W", "D17")]
    _stub_send(adapter)
    await adapter.undo()
    assert adapter._replay.plays == [("B", "Q16")]


@pytest.mark.asyncio
async def test_undo_no_op_when_history_empty() -> None:
    adapter = KataGoAdapter()
    _stub_send(adapter)
    await adapter.undo()  # should not raise even with empty plays
    assert adapter._replay.plays == []


@pytest.mark.asyncio
async def test_genmove_records_unless_pass_or_resign() -> None:
    adapter = KataGoAdapter()
    _stub_send(adapter, body="Q16")
    move = await adapter.genmove("B")
    assert move == "Q16"
    assert adapter._replay.plays == [("B", "Q16")]


@pytest.mark.asyncio
async def test_genmove_pass_does_not_pollute_replay() -> None:
    adapter = KataGoAdapter()
    _stub_send(adapter, body="pass")
    move = await adapter.genmove("W")
    assert move == "pass"
    assert adapter._replay.plays == []


@pytest.mark.asyncio
async def test_genmove_resign_does_not_pollute_replay() -> None:
    adapter = KataGoAdapter()
    _stub_send(adapter, body="resign")
    move = await adapter.genmove("W")
    assert move == "resign"
    assert adapter._replay.plays == []


@pytest.mark.asyncio
async def test_genmove_raises_on_engine_error() -> None:
    adapter = KataGoAdapter()
    from app.core.katago.adapter import GTPResult

    async def fake_send(cmd: str, timeout: float | None = None) -> GTPResult:
        return GTPResult(ok=False, body="busy")

    adapter.send = fake_send  # type: ignore[assignment]
    with pytest.raises(ValueError):
        await adapter.genmove("B")


@pytest.mark.asyncio
async def test_final_score_returns_body_string() -> None:
    adapter = KataGoAdapter()
    _stub_send(adapter, body="B+12.5")
    out = await adapter.final_score()
    assert out == "B+12.5"


@pytest.mark.asyncio
async def test_final_score_raises_on_engine_error() -> None:
    adapter = KataGoAdapter()
    from app.core.katago.adapter import GTPResult

    async def fake_send(cmd: str, timeout: float | None = None) -> GTPResult:
        return GTPResult(ok=False, body="not finished")

    adapter.send = fake_send  # type: ignore[assignment]
    with pytest.raises(ValueError):
        await adapter.final_score()


@pytest.mark.asyncio
async def test_set_profile_with_strength_config() -> None:
    from app.core.katago.strength import StrengthConfig

    adapter = KataGoAdapter()
    sent = _stub_send(adapter)
    cfg = StrengthConfig(rank="5k", human_sl_profile="rank_5k", max_visits=64)
    await adapter.set_profile(cfg)
    assert "kata-set-param humanSLProfile rank_5k" in sent
    assert "kata-set-param maxVisits 64" in sent
    assert adapter._replay.profile == ("rank_5k", 64)


@pytest.mark.asyncio
async def test_set_profile_with_string_and_visits() -> None:
    adapter = KataGoAdapter()
    sent = _stub_send(adapter)
    await adapter.set_profile("rank_3d", max_visits=128)
    assert sent == [
        "kata-set-param humanSLProfile rank_3d",
        "kata-set-param maxVisits 128",
    ]
    assert adapter._replay.profile == ("rank_3d", 128)


@pytest.mark.asyncio
async def test_set_profile_tolerates_unknown_humansl_param() -> None:
    """If KataGo rejects humanSLProfile (standard model w/o human-SL), the
    adapter still issues maxVisits and treats the call as successful."""
    adapter = KataGoAdapter()
    from app.core.katago.adapter import GTPResult

    sent: list[str] = []

    async def fake_send(cmd: str, timeout: float | None = None) -> GTPResult:
        sent.append(cmd)
        # Reject humanSLProfile, accept everything else.
        if "humanSLProfile" in cmd:
            return GTPResult(ok=False, body="unknown command")
        return GTPResult(ok=True, body="")

    adapter.send = fake_send  # type: ignore[assignment]
    await adapter.set_profile("rank_5k", max_visits=64)
    assert any("maxVisits 64" in c for c in sent)


# ─── _replay_state restoration ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_replay_state_emits_recorded_commands() -> None:
    adapter = KataGoAdapter()
    adapter._replay.boardsize = 13
    adapter._replay.komi = 7.5
    adapter._replay.profile = ("rank_5k", 64)
    adapter._replay.plays = [("B", "G7"), ("W", "G6")]

    sent: list[str] = []
    from app.core.katago.adapter import GTPResult

    async def fake_send_raw(cmd: str, timeout: float | None = None) -> GTPResult:
        sent.append(cmd)
        return GTPResult(ok=True, body="")

    adapter._send_raw = fake_send_raw  # type: ignore[assignment]
    await adapter._replay_state()

    assert "boardsize 13" in sent
    assert "komi 7.5" in sent
    assert "kata-set-param humanSLProfile rank_5k" in sent
    assert "kata-set-param maxVisits 64" in sent
    assert "play B G7" in sent
    assert "play W G6" in sent


# ─── stop() lifecycle ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stop_quits_gracefully_when_alive() -> None:
    adapter = KataGoAdapter()
    proc = _make_fake_proc([b"= bye\n", b"\n"])
    proc.wait = AsyncMock(return_value=0)
    _attach(adapter, proc)
    await adapter.stop()
    assert adapter._proc is None


@pytest.mark.asyncio
async def test_stop_swallows_quit_send_failure() -> None:
    """If `_send_raw('quit')` raises, stop() still proceeds to wait/terminate
    instead of bubbling the error — tests the noqa-tagged S110 branch."""
    adapter = KataGoAdapter()
    proc = Mock()
    proc.returncode = None
    proc.stdin = _FakeStdin()
    proc.stdout = Mock()
    proc.terminate = Mock()
    proc.kill = Mock()
    proc.wait = AsyncMock(return_value=0)
    _attach(adapter, proc)

    async def boom(cmd: str, timeout: float | None = None) -> Any:
        raise RuntimeError("pipe broken")

    adapter._send_raw = boom  # type: ignore[assignment]
    await adapter.stop()
    assert adapter._proc is None


@pytest.mark.asyncio
async def test_stop_no_op_when_no_process() -> None:
    adapter = KataGoAdapter()
    adapter._proc = None
    await adapter.stop()  # should not raise
    assert adapter._proc is None
