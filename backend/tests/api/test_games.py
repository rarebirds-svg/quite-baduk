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

    from app.services.game_service import score_by_request
    from app.db import AsyncSessionLocal
    from sqlalchemy import select
    from app.models import Game, Session

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
