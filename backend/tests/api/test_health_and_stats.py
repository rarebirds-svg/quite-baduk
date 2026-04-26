import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    r = await client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert "status" in body


@pytest.mark.asyncio
async def test_stats_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/api/stats")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_stats_empty(client: AsyncClient) -> None:
    await client.post("/api/session", json={"nickname": "stats_user"})
    r = await client.get("/api/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_stats_aggregates_by_rank_board_player(client: AsyncClient) -> None:
    """Drive the by_rank / by_board_size / by_ai_player buckets so the
    aggregation paths in stats.py get exercised."""
    await client.post("/api/session", json={"nickname": "stats_user2"})
    g = await client.post(
        "/api/games",
        json={
            "ai_rank": "5k",
            "handicap": 0,
            "user_color": "black",
            "ai_player": "lee_sedol",
        },
    )
    assert g.status_code == 201
    gid = g.json()["id"]
    # Resign to produce a finished, decisive row for win-rate aggregation.
    assert (await client.post(f"/api/games/{gid}/resign")).status_code == 200

    body = (await client.get("/api/stats")).json()
    assert body["total"] >= 1
    assert isinstance(body["by_rank"], list)
    assert isinstance(body["by_board_size"], list)
    assert isinstance(body["by_ai_player"], list)
    assert any(b["ai_rank"] == "5k" for b in body["by_rank"])
    assert any(b["ai_player"] == "lee_sedol" for b in body["by_ai_player"])
    assert isinstance(body["breakdown"], list)
    assert len(body["breakdown"]) >= 1
