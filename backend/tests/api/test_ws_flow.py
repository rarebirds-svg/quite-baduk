"""End-to-end WebSocket flow tests using Starlette's synchronous TestClient.

These exercise the bulk of api/ws.py — the move handler, ai_move emission,
undo handling, and the per-game lock — plus the service-layer paths that
are otherwise only reachable through a live WS.
"""
from __future__ import annotations

import asyncio
import os
import tempfile

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient


async def _create_schema(engine, base) -> None:  # type: ignore[no-untyped-def]
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)


def _wire_test_app(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, str]:
    """Boot a fresh app instance bound to an isolated temp DB and the mock
    KataGo. Returns (client, db_path) — caller closes the client and deletes
    the file."""
    from app.core.katago.mock import MockKataGoAdapter
    from app.db import Base
    from app.engine_pool import set_adapter

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = tmp.name

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    asyncio.run(_create_schema(engine, Base))
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    import app.db as db_module
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "AsyncSessionLocal", factory)

    os.environ["KATAGO_MOCK"] = "true"
    mock = MockKataGoAdapter()
    set_adapter(mock)
    asyncio.run(mock.start())

    from app.main import create_app
    return TestClient(create_app(), raise_server_exceptions=True), db_path


def test_ws_move_emits_state_and_ai_move(monkeypatch: pytest.MonkeyPatch) -> None:
    tc, db_path = _wire_test_app(monkeypatch)
    try:
        with tc:
            r = tc.post("/api/session", json={"nickname": "ws_mover"})
            assert r.status_code == 201
            cookie = r.cookies.get("baduk_session")
            assert cookie is not None
            r = tc.post(
                "/api/games",
                json={
                    "board_size": 9,
                    "handicap": 0,
                    "ai_rank": "5k",
                    "user_color": "black",
                },
                cookies={"baduk_session": cookie},
            )
            game_id = r.json()["id"]

            with tc.websocket_connect(
                f"/api/ws/games/{game_id}",
                cookies={"baduk_session": cookie},
            ) as ws:
                # Initial state push.
                init = ws.receive_json()
                assert init["type"] == "state"
                assert init["board_size"] == 9

                # Send a move; expect at minimum: state (post-user) + ai_move.
                ws.send_json({"type": "move", "coord": "E5"})
                seen = {"state": 0, "ai_move": 0, "winrate": 0}
                # Drain a few messages — exact ordering depends on whether
                # the engine emits a winrate push first.
                for _ in range(8):
                    msg = ws.receive_json()
                    if msg["type"] in seen:
                        seen[msg["type"]] += 1
                    if seen["ai_move"] >= 1 and seen["state"] >= 2:
                        break
                assert seen["state"] >= 2  # post-user + post-AI
                assert seen["ai_move"] >= 1
    finally:
        tc.close()
        try:
            os.unlink(db_path)
        except OSError:
            pass


def test_ws_undo_reverts_state(monkeypatch: pytest.MonkeyPatch) -> None:
    tc, db_path = _wire_test_app(monkeypatch)
    try:
        with tc:
            r = tc.post("/api/session", json={"nickname": "ws_undoer"})
            cookie = r.cookies.get("baduk_session")
            r = tc.post(
                "/api/games",
                json={
                    "board_size": 9,
                    "handicap": 0,
                    "ai_rank": "5k",
                    "user_color": "black",
                },
                cookies={"baduk_session": cookie},
            )
            game_id = r.json()["id"]

            with tc.websocket_connect(
                f"/api/ws/games/{game_id}",
                cookies={"baduk_session": cookie},
            ) as ws:
                ws.receive_json()  # initial state
                ws.send_json({"type": "move", "coord": "E5"})
                # Drain messages until we've seen the AI's response.
                for _ in range(8):
                    m = ws.receive_json()
                    if m["type"] == "ai_move":
                        break

                ws.send_json({"type": "undo"})
                # Server emits a state with an undo_count bump and reverted board.
                for _ in range(4):
                    m = ws.receive_json()
                    if m["type"] == "state" and m.get("undo_count", 0) >= 1:
                        # Empty cells dominate again because we undid both plies.
                        assert m["board"].count(".") > 70
                        return
                pytest.fail("never saw a state with undo_count >= 1")
    finally:
        tc.close()
        try:
            os.unlink(db_path)
        except OSError:
            pass


def test_ws_send_after_close_during_place_move_is_silent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the socket is closed (heartbeat expiry / eviction) while place_move
    is in flight, the post-move send_json must be swallowed — not surface as a
    RuntimeError('Cannot call "send" once a close message has been sent.') that
    floods baduk-api.err (#39)."""
    from starlette.websockets import WebSocketDisconnect

    tc, db_path = _wire_test_app(monkeypatch)
    try:
        with tc:
            r = tc.post("/api/session", json={"nickname": "ws_racer"})
            cookie = r.cookies.get("baduk_session")
            r = tc.post(
                "/api/games",
                json={
                    "board_size": 9,
                    "handicap": 0,
                    "ai_rank": "5k",
                    "user_color": "black",
                },
                cookies={"baduk_session": cookie},
            )
            game_id = r.json()["id"]

            from app.api import ws as ws_module

            real_place_move = ws_module.place_move

            async def closing_place_move(db, **kwargs):  # type: ignore[no-untyped-def]
                result = await real_place_move(db, **kwargs)
                # Simulate the heartbeat/eviction task closing the socket
                # while we were busy computing the AI reply. The handler's
                # next send_json now hits a closed socket.
                await ws_module._connections[game_id].close()
                return result

            monkeypatch.setattr(ws_module, "place_move", closing_place_move)

            with tc.websocket_connect(
                f"/api/ws/games/{game_id}",
                cookies={"baduk_session": cookie},
            ) as ws:
                ws.receive_json()  # initial state
                ws.send_json({"type": "move", "coord": "E5"})
                # Draining must end in a clean WebSocketDisconnect, never a
                # RuntimeError leaking from the server handler.
                try:
                    for _ in range(12):
                        ws.receive_json()
                except WebSocketDisconnect:
                    pass
    finally:
        tc.close()
        try:
            os.unlink(db_path)
        except OSError:
            pass


def test_ws_receive_after_disconnect_is_silent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the socket flips to DISCONNECTED (eviction / client drop / heartbeat
    close) between loop iterations, the top-of-loop websocket.receive_json()
    raises RuntimeError('WebSocket is not connected. Need to call "accept"
    first.') instead of WebSocketDisconnect. That must be swallowed too — not
    surface as a server error that floods baduk-api.err (#39 receive-side
    variant, 70x).

    We patch the *server-side* WebSocket.receive_json (a different class than
    the TestClient's WebSocketTestSession, so the client side is unaffected) to
    raise that exact RuntimeError on its first call — i.e. the loop's line 186.
    """
    from starlette.websockets import WebSocket, WebSocketDisconnect

    real_receive_json = WebSocket.receive_json
    calls = {"n": 0}

    async def flaky_receive_json(self, mode: str = "text"):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        if calls["n"] == 1:
            # Simulate a concurrent close (heartbeat expiry / eviction) having
            # flipped the socket to DISCONNECTED before this loop iteration:
            # close the transport, then raise exactly what Starlette's
            # receive_json raises when entered on a disconnected socket.
            await self.close()
            raise RuntimeError(
                'WebSocket is not connected. Need to call "accept" first.'
            )
        return await real_receive_json(self, mode)

    monkeypatch.setattr(WebSocket, "receive_json", flaky_receive_json)

    tc, db_path = _wire_test_app(monkeypatch)
    try:
        with tc:
            r = tc.post("/api/session", json={"nickname": "ws_recv_racer"})
            cookie = r.cookies.get("baduk_session")
            r = tc.post(
                "/api/games",
                json={
                    "board_size": 9,
                    "handicap": 0,
                    "ai_rank": "5k",
                    "user_color": "black",
                },
                cookies={"baduk_session": cookie},
            )
            game_id = r.json()["id"]

            with tc.websocket_connect(
                f"/api/ws/games/{game_id}",
                cookies={"baduk_session": cookie},
            ) as ws:
                ws.receive_json()  # initial state (sent before the loop)
                # The server's first loop receive_json now raises the
                # RuntimeError. Draining must end in a clean WebSocketDisconnect,
                # never a RuntimeError leaking from the server handler.
                with pytest.raises(WebSocketDisconnect):
                    for _ in range(5):
                        ws.receive_json()
    finally:
        tc.close()
        try:
            os.unlink(db_path)
        except OSError:
            pass


def test_ws_eviction_on_second_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Opening a second WS for the same game evicts the first with a
    SESSION_REPLACED error frame — exercises the existing-connection cleanup
    branch in ws.py."""
    tc, db_path = _wire_test_app(monkeypatch)
    try:
        with tc:
            r = tc.post("/api/session", json={"nickname": "ws_evictor"})
            cookie = r.cookies.get("baduk_session")
            r = tc.post(
                "/api/games",
                json={
                    "board_size": 9,
                    "handicap": 0,
                    "ai_rank": "5k",
                    "user_color": "black",
                },
                cookies={"baduk_session": cookie},
            )
            game_id = r.json()["id"]

            with tc.websocket_connect(
                f"/api/ws/games/{game_id}",
                cookies={"baduk_session": cookie},
            ) as ws1:
                ws1.receive_json()  # initial state — confirms ws1 is open

                # Second connection should cause ws1 to receive an error frame
                # then close. We just check that the second one accepts.
                with tc.websocket_connect(
                    f"/api/ws/games/{game_id}",
                    cookies={"baduk_session": cookie},
                ) as ws2:
                    init2 = ws2.receive_json()
                    assert init2["type"] == "state"
    finally:
        tc.close()
        try:
            os.unlink(db_path)
        except OSError:
            pass
