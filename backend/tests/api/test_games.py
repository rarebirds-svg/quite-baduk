import pytest
from httpx import AsyncClient

_ctr = 0


async def _signup(client: AsyncClient, email: str | None = None) -> None:
    """Bridge helper kept for existing call sites — creates a fresh session
    with a unique nickname. Email arg is accepted but ignored."""
    global _ctr
    _ctr += 1
    # Derive a nickname from call order / optional email hint so repeat calls
    # inside a single test don't collide with the DB UNIQUE(nickname_key).
    nick = (email or "p").replace("@", "_").replace(".", "_")[:24]
    nick = f"{nick}_{_ctr}"
    r = await client.post("/api/session", json={"nickname": nick})
    assert r.status_code == 201, r.text


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [9, 13, 19])
async def test_create_game_each_size(client: AsyncClient, size: int) -> None:
    await _signup(client, email=f"u{size}@example.com")
    r = await client.post(
        "/api/games",
        json={"ai_rank": "5k", "handicap": 0, "user_color": "black", "board_size": size},
    )
    assert r.status_code == 201, r.text
    g = r.json()
    assert g["board_size"] == size
    assert g["komi"] == 6.5


@pytest.mark.asyncio
async def test_create_game_default_board_size_is_19(client: AsyncClient) -> None:
    await _signup(client)
    r = await client.post(
        "/api/games",
        json={"ai_rank": "5k", "handicap": 0, "user_color": "black"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["board_size"] == 19


@pytest.mark.asyncio
async def test_create_game_rejects_invalid_size(client: AsyncClient) -> None:
    await _signup(client)
    r = await client.post(
        "/api/games",
        json={"ai_rank": "5k", "handicap": 0, "user_color": "black", "board_size": 7},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_9x9_rejects_handicap_6(client: AsyncClient) -> None:
    await _signup(client)
    r = await client.post(
        "/api/games",
        json={"ai_rank": "1d", "handicap": 6, "user_color": "black", "board_size": 9},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_HANDICAP"


@pytest.mark.asyncio
async def test_create_handicap_game_13(client: AsyncClient) -> None:
    await _signup(client)
    r = await client.post(
        "/api/games",
        json={"ai_rank": "1d", "handicap": 4, "user_color": "black", "board_size": 13},
    )
    assert r.status_code == 201
    g = r.json()
    assert g["handicap"] == 4
    assert g["komi"] == 0.5
    assert g["board_size"] == 13


@pytest.mark.asyncio
async def test_list_games(client: AsyncClient) -> None:
    await _signup(client)
    await client.post("/api/games", json={"ai_rank": "5k", "handicap": 0, "user_color": "black"})
    await client.post(
        "/api/games", json={"ai_rank": "1k", "handicap": 2, "user_color": "black", "board_size": 9}
    )
    r = await client.get("/api/games")
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_games_survive_session_end_but_are_forbidden_to_others(
    client: AsyncClient,
) -> None:
    """After a session ends, its games are preserved (so the admin console
    keeps its audit trail), but a different user's session cannot access
    them — a non-admin peer gets 403, not a 404."""
    await _signup(client, email="u1@example.com")
    r = await client.post("/api/games", json={"ai_rank": "5k", "handicap": 0, "user_color": "black"})
    game_id = r.json()["id"]
    await client.post("/api/session/end")
    await _signup(client, email="u2@example.com")
    r2 = await client.get(f"/api/games/{game_id}")
    assert r2.status_code == 403


@pytest.mark.asyncio
async def test_resign(client: AsyncClient) -> None:
    await _signup(client)
    r = await client.post("/api/games", json={"ai_rank": "5k", "handicap": 0, "user_color": "black"})
    game_id = r.json()["id"]
    r2 = await client.post(f"/api/games/{game_id}/resign")
    assert r2.status_code == 200
    g = r2.json()
    assert g["status"] == "resigned"
    assert g["result"] == "W+R"


@pytest.mark.asyncio
async def test_sgf_download(client: AsyncClient) -> None:
    await _signup(client)
    r = await client.post("/api/games", json={"ai_rank": "5k", "handicap": 0, "user_color": "black"})
    game_id = r.json()["id"]
    await client.post(f"/api/games/{game_id}/resign")
    r2 = await client.get(f"/api/games/{game_id}/sgf")
    assert r2.status_code == 200
    assert "GM[1]" in r2.text


@pytest.mark.asyncio
async def test_hint(client: AsyncClient) -> None:
    await _signup(client)
    r = await client.post("/api/games", json={"ai_rank": "5k", "handicap": 0, "user_color": "black"})
    game_id = r.json()["id"]
    r2 = await client.post(f"/api/games/{game_id}/hint")
    assert r2.status_code == 200
    assert "hints" in r2.json()


@pytest.mark.asyncio
async def test_score_request_includes_territory_points(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the user requests scoring on a finished position, ScoringDetail
    exposes per-side territory coordinates and the dead-stones set inferred
    by the engine."""
    await _signup(client)
    r = await client.post(
        "/api/games",
        json={"board_size": 9, "handicap": 0, "ai_rank": "5k", "user_color": "black"},
    )
    assert r.status_code == 201
    game_id = r.json()["id"]

    # Bypass the endgame-phase gate so score_by_request can run on a fresh game.
    import app.services.game_service as _svc
    monkeypatch.setattr(_svc, "_endgame_phase_from_ownership", lambda state, ownership: True)

    from sqlalchemy import select

    from app.db import AsyncSessionLocal
    from app.models import Game, Session
    from app.services.game_service import score_by_request

    session_token = client.cookies.get("baduk_session")
    async with AsyncSessionLocal() as db:
        sess = (
            await db.execute(
                select(Session).where(Session.token == session_token)
            )
        ).scalar_one()
        game = (
            await db.execute(select(Game).where(Game.id == game_id))
        ).scalar_one()
        detail = await score_by_request(db, game=game, session=sess)

    assert isinstance(detail.black_points, frozenset)
    assert isinstance(detail.white_points, frozenset)
    assert isinstance(detail.dame_points, frozenset)
    assert isinstance(detail.dead_stones, frozenset)
    assert len(detail.black_points) == detail.black_territory
    assert len(detail.white_points) == detail.white_territory


def test_ws_score_result_payload_includes_points(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end: open the WS, send a score_request, expect the payload
    fields the frontend renders the territory map from.

    Uses Starlette's synchronous TestClient (the only path that exposes
    websocket_connect) with a fresh in-memory SQLite database and the mock
    KataGo adapter.
    """
    import asyncio
    import os
    import tempfile

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool
    from starlette.testclient import TestClient

    import app.services.game_service as _svc
    from app.core.katago.mock import MockKataGoAdapter
    from app.db import Base
    from app.engine_pool import set_adapter

    # --- fresh isolated DB -----------------------------------------------
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = tmp.name

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    asyncio.run(_create_schema(engine, Base))
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    import app.db as db_module
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "AsyncSessionLocal", session_factory)

    # --- mock KataGo + bypass endgame gate --------------------------------
    os.environ["KATAGO_MOCK"] = "true"
    mock = MockKataGoAdapter()
    set_adapter(mock)
    asyncio.run(mock.start())

    monkeypatch.setattr(_svc, "_endgame_phase_from_ownership", lambda state, ownership: True)

    # --- build app --------------------------------------------------------
    from app.main import create_app
    app_instance = create_app()

    with TestClient(app_instance, raise_server_exceptions=True) as tc:
        # create session
        r = tc.post("/api/session", json={"nickname": "ws_tester_1"})
        assert r.status_code == 201, r.text
        session_cookie = r.cookies.get("baduk_session")
        assert session_cookie is not None

        # create game
        r = tc.post(
            "/api/games",
            json={"board_size": 9, "handicap": 0, "ai_rank": "5k", "user_color": "black"},
            cookies={"baduk_session": session_cookie},
        )
        assert r.status_code == 201, r.text
        game_id = r.json()["id"]

        # open WS and send score_request
        with tc.websocket_connect(
            f"/api/ws/games/{game_id}",
            cookies={"baduk_session": session_cookie},
        ) as ws:
            # Drain until we've consumed the initial state (and optional
            # winrate push that the server sends on connection).
            init = ws.receive_json()
            assert init["type"] == "state"
            # Optionally consume a winrate push that follows initial state.
            ws.send_json({"type": "score_request"})
            # Receive messages until we find score_result, skipping winrate
            msg = ws.receive_json()
            if msg["type"] == "winrate":
                msg = ws.receive_json()
            assert msg["type"] == "score_result"
            assert isinstance(msg["black_points"], list)
            assert isinstance(msg["white_points"], list)
            assert isinstance(msg["dame_points"], list)
            assert isinstance(msg["dead_stones"], list)
            for pt in msg["black_points"]:
                assert isinstance(pt, list) and len(pt) == 2

    # cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


async def _create_schema(engine, base) -> None:  # type: ignore[no-untyped-def]
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)
