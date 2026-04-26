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
