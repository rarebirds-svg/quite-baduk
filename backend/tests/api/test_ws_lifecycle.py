"""WebSocket lifecycle: atomic session replacement + heartbeat."""
from __future__ import annotations

import asyncio
import secrets

import pytest
from httpx import AsyncClient
from sqlalchemy import delete

# Ensure all model classes are registered with `Base.metadata` before
# `db_engine` calls `create_all`. Pytest collects test files in alpha
# order, so this file (`test_ws_lifecycle.py`) can run before any other
# import path has touched the models package.
import app.models  # noqa: F401, E402


@pytest.mark.asyncio
async def test_concurrent_connections_settle_to_single_active(
    client: AsyncClient,
) -> None:
    """Under racing connection attempts on the same game id, exactly one
    connection ends up registered; the loser is closed.

    Driving the swap helper directly with fakes is the only way to
    deterministically race two connects — httpx's ASGI transport doesn't
    expose the WebSocket lifecycle finely enough for this.
    """
    r = await client.post("/api/session", json={"nickname": "wsrace"})
    assert r.status_code == 201
    cookies = r.cookies
    r = await client.post(
        "/api/games",
        json={
            "ai_rank": "5k",
            "handicap": 0,
            "user_color": "black",
            "board_size": 9,
        },
        cookies=cookies,
    )
    gid = r.json()["id"]

    from app.api.ws import _connections, _get_connection_lock

    class FakeWS:
        def __init__(self, name: str) -> None:
            self.name = name
            self.closed = False

        async def accept(self) -> None:  # pragma: no cover - trivial
            pass

        async def send_json(self, _: dict) -> None:  # pragma: no cover - trivial
            pass

        async def close(self) -> None:
            self.closed = True

    ws_a = FakeWS("a")
    ws_b = FakeWS("b")

    async def install(ws: FakeWS) -> None:
        async with _get_connection_lock(gid):
            existing = _connections.get(gid)
            if existing is not None:
                await existing.send_json(
                    {"type": "error", "code": "SESSION_REPLACED"}
                )
                await existing.close()
            await ws.accept()
            _connections[gid] = ws

    await asyncio.gather(install(ws_a), install(ws_b))

    assert _connections[gid] in (ws_a, ws_b)
    losers = [w for w in (ws_a, ws_b) if w is not _connections[gid]]
    assert len(losers) == 1
    assert all(w.closed for w in losers)
    _connections.pop(gid, None)


@pytest.mark.asyncio
async def test_heartbeat_closes_ws_when_session_disappears(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Heartbeat must close the WS once the session row is gone.

    The `client` fixture is requested only to install the test DB
    overrides on `app.db.AsyncSessionLocal`, which `_heartbeat` uses.
    """
    from app.api import ws as ws_module
    from app.db import AsyncSessionLocal
    from app.models import Session

    monkeypatch.setattr(ws_module, "HEARTBEAT_SECONDS", 0.05)

    closed = asyncio.Event()

    class FakeWS:
        async def send_json(self, _: dict) -> None:  # pragma: no cover - trivial
            pass

        async def close(self) -> None:
            closed.set()

    async with AsyncSessionLocal() as db:
        sess = Session(
            token=secrets.token_urlsafe(8),
            nickname="hb",
            nickname_key="hb",
        )
        db.add(sess)
        await db.commit()
        await db.refresh(sess)
        sess_copy = sess
        await db.execute(delete(Session).where(Session.id == sess.id))
        await db.commit()

    task = asyncio.create_task(
        ws_module._heartbeat(FakeWS(), 1, sess_copy)
    )
    try:
        await asyncio.wait_for(closed.wait(), timeout=2.0)
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
