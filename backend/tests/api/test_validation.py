"""Schema-level validation guards for query parameters and config parsing.

Covers Task B4 (P1-8 + P1-9):
- ``moveNum``/``page`` must reject out-of-range values at the schema layer
  (FastAPI returns 422 before the handler runs).
- ``Settings.cors_origins_list`` must tolerate whitespace and skip empty
  segments — production deployments often paste comma-separated origins
  with stray spaces.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analyze_rejects_negative_movenum(client: AsyncClient) -> None:
    r = await client.post("/api/session", json={"nickname": "negmv"})
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

    r = await client.post(f"/api/games/{gid}/analyze?moveNum=-1")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_games_rejects_zero_page(client: AsyncClient) -> None:
    r = await client.post("/api/session", json={"nickname": "pgzero"})
    assert r.status_code == 201
    r = await client.get("/api/games?page=0")
    assert r.status_code == 422


def test_cors_origins_list_strips_whitespace() -> None:
    from app.config import Settings

    s = Settings(cors_origins=" http://a , http://b ")
    assert s.cors_origins_list == ["http://a", "http://b"]


def test_cors_origins_list_drops_empty_segments() -> None:
    from app.config import Settings

    s = Settings(cors_origins="http://a,,http://b,")
    assert s.cors_origins_list == ["http://a", "http://b"]
