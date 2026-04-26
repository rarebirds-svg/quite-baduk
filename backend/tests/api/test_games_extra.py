"""Extra coverage for /api/games error paths + list endpoint pagination /
filter, which the smoke tests in test_games.py don't exercise."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


async def _signup(client: AsyncClient, nickname: str) -> None:
    r = await client.post("/api/session", json={"nickname": nickname})
    assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_list_games_filters_by_status_and_paginates(client: AsyncClient) -> None:
    await _signup(client, "lister")
    # Create 3 games; resign 1.
    ids = []
    for _ in range(3):
        r = await client.post(
            "/api/games",
            json={"ai_rank": "5k", "handicap": 0, "user_color": "black"},
        )
        assert r.status_code == 201
        ids.append(r.json()["id"])
    await client.post(f"/api/games/{ids[0]}/resign")

    active = (await client.get("/api/games?status_=active")).json()
    resigned = (await client.get("/api/games?status_=resigned")).json()
    assert len(active) == 2
    assert len(resigned) == 1
    # Pagination doesn't error on page=2 when there are no more results.
    page2 = (await client.get("/api/games?page=2")).json()
    assert page2 == []


@pytest.mark.asyncio
async def test_get_game_404_when_missing(client: AsyncClient) -> None:
    await _signup(client, "missing_game")
    r = await client.get("/api/games/99999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_game_403_when_other_session(client: AsyncClient) -> None:
    """Non-admin peer cannot read someone else's game even if it exists."""
    await _signup(client, "owner_user")
    r = await client.post(
        "/api/games",
        json={"ai_rank": "5k", "handicap": 0, "user_color": "black"},
    )
    gid = r.json()["id"]
    # Switch to another session via a fresh client with no cookies.
    other = AsyncClient(transport=client._transport, base_url=client.base_url)
    try:
        await _signup(other, "other_user")
        r2 = await other.get(f"/api/games/{gid}")
        assert r2.status_code == 403
    finally:
        await other.aclose()
    _ = ASGITransport


@pytest.mark.asyncio
async def test_resign_404_when_missing(client: AsyncClient) -> None:
    await _signup(client, "resign_missing")
    r = await client.post("/api/games/77777/resign")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_resign_403_when_other_session(client: AsyncClient) -> None:
    await _signup(client, "resign_owner")
    r = await client.post(
        "/api/games",
        json={"ai_rank": "5k", "handicap": 0, "user_color": "black"},
    )
    gid = r.json()["id"]
    other = AsyncClient(transport=client._transport, base_url=client.base_url)
    try:
        await _signup(other, "resign_intruder")
        r2 = await other.post(f"/api/games/{gid}/resign")
        assert r2.status_code == 403
    finally:
        await other.aclose()


@pytest.mark.asyncio
async def test_delete_game_returns_204(client: AsyncClient) -> None:
    await _signup(client, "deleter")
    r = await client.post(
        "/api/games",
        json={"ai_rank": "5k", "handicap": 0, "user_color": "black"},
    )
    gid = r.json()["id"]
    r2 = await client.delete(f"/api/games/{gid}")
    assert r2.status_code == 204
    r3 = await client.get(f"/api/games/{gid}")
    assert r3.status_code == 404


@pytest.mark.asyncio
async def test_sgf_404_for_unknown_game(client: AsyncClient) -> None:
    await _signup(client, "sgf_missing")
    r = await client.get("/api/games/88888/sgf")
    assert r.status_code == 404
