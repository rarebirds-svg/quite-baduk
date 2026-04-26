"""Coverage for /api/games/{id}/analyze — the analysis endpoint runs the
mock KataGo adapter and persists a row in analysis_cache."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _signup_and_create_game(client: AsyncClient, nickname: str) -> int:
    r = await client.post("/api/session", json={"nickname": nickname})
    assert r.status_code == 201
    g = await client.post(
        "/api/games",
        json={"ai_rank": "5k", "handicap": 0, "user_color": "black"},
    )
    assert g.status_code == 201
    return int(g.json()["id"])


@pytest.mark.asyncio
async def test_analyze_returns_winrate_and_top_moves(client: AsyncClient) -> None:
    gid = await _signup_and_create_game(client, "analyzer1")
    r = await client.post(f"/api/games/{gid}/analyze?moveNum=0")
    assert r.status_code == 200
    body = r.json()
    assert "winrate" in body
    assert isinstance(body["top_moves"], list)
    assert "ownership" in body


@pytest.mark.asyncio
async def test_analyze_caches_subsequent_calls(client: AsyncClient) -> None:
    """Second call for the same (game, move) reads from analysis_cache, hitting
    the cached-branch in api/analysis.py."""
    gid = await _signup_and_create_game(client, "analyzer2")
    first = await client.post(f"/api/games/{gid}/analyze?moveNum=0")
    second = await client.post(f"/api/games/{gid}/analyze?moveNum=0")
    assert first.status_code == 200
    assert second.status_code == 200
    # The cache deserialization path returns the same payload.
    assert first.json()["winrate"] == second.json()["winrate"]


@pytest.mark.asyncio
async def test_analyze_404_when_game_missing(client: AsyncClient) -> None:
    r = await client.post("/api/session", json={"nickname": "analyzer3"})
    assert r.status_code == 201
    r2 = await client.post("/api/games/99999/analyze?moveNum=0")
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_analyze_403_when_other_session(client: AsyncClient) -> None:
    gid = await _signup_and_create_game(client, "analyzer_owner")
    other = AsyncClient(transport=client._transport, base_url=client.base_url)
    try:
        await other.post("/api/session", json={"nickname": "analyzer_intruder"})
        r = await other.post(f"/api/games/{gid}/analyze?moveNum=0")
        assert r.status_code == 403
    finally:
        await other.aclose()
