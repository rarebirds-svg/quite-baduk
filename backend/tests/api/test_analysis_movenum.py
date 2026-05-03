"""Reviewing moveNum=2 must analyze the board state after move 2, not
after the latest move.

The analyze endpoint used to skip the replay-to-N step and always read the
shared adapter's *current* board, which is whatever the most recent
`place_move` left on it. That made every "review at move N" call surface
identical, late-game data. The fix is to replay the rules state up to
``moveNum`` and reseed the adapter before issuing `analyze`.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models import Game, Session
from app.services.game_service import place_move


@pytest.mark.asyncio
async def test_analyze_at_early_move_differs_from_latest(
    client: AsyncClient,
) -> None:
    r = await client.post("/api/session", json={"nickname": "movenum"})
    assert r.status_code == 201

    g = await client.post(
        "/api/games",
        json={
            "ai_rank": "5k",
            "handicap": 0,
            "user_color": "black",
            "board_size": 9,
        },
    )
    assert g.status_code == 201
    gid = int(g.json()["id"])

    # Drive several moves directly through the service (faster than WS in
    # tests). The mock adapter responds deterministically.
    coords = ["D4", "C3", "F5", "E6", "G7"]
    session_token = client.cookies.get("baduk_session")
    from app.db import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        sess = (
            await db.execute(
                select(Session).where(Session.token == session_token)
            )
        ).scalar_one()
        game = (
            await db.execute(select(Game).where(Game.id == gid))
        ).scalar_one()
        for c in coords:
            await place_move(db, game=game, session=sess, coord=c)

    # Hit the analyze endpoint at moveNum=2 and at the latest moveNum
    r2 = await client.post(f"/api/games/{gid}/analyze?moveNum=2")
    r_latest = await client.post(f"/api/games/{gid}/analyze?moveNum=10")
    assert r2.status_code == 200, r2.text
    assert r_latest.status_code == 200, r_latest.text
    j2 = r2.json()
    j_latest = r_latest.json()
    # Mid-game vs much-earlier position must differ. With the mock adapter
    # this is reliable: top_moves are scan-order legal points, so a board
    # with more occupied cells skips different cells than an early board,
    # producing a different hint list.
    assert j2 != j_latest


@pytest.mark.asyncio
async def test_analyze_at_movenum_zero_returns_initial_position(
    client: AsyncClient,
) -> None:
    """``moveNum=0`` must analyze the empty (or handicap-stones-only) board,
    not whatever the adapter happens to be holding."""
    r = await client.post("/api/session", json={"nickname": "movenum_zero"})
    assert r.status_code == 201

    g = await client.post(
        "/api/games",
        json={
            "ai_rank": "5k",
            "handicap": 0,
            "user_color": "black",
            "board_size": 9,
        },
    )
    gid = int(g.json()["id"])

    session_token = client.cookies.get("baduk_session")
    from app.db import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        sess = (
            await db.execute(
                select(Session).where(Session.token == session_token)
            )
        ).scalar_one()
        game = (
            await db.execute(select(Game).where(Game.id == gid))
        ).scalar_one()
        for c in ["E5", "D5", "F5", "C5"]:
            await place_move(db, game=game, session=sess, coord=c)

    r0 = await client.post(f"/api/games/{gid}/analyze?moveNum=0")
    assert r0.status_code == 200, r0.text
    body = r0.json()
    # At move 0 the board is empty; the mock adapter's top hints scan from
    # the top-left corner, so A9 must be in the suggested list.
    moves = [m["move"] for m in body["top_moves"]]
    assert "A9" in moves
