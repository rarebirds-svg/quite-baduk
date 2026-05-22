# 프로 기보 공개 조회 API(/api/spectate/pro) 계약 테스트
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.sgf.import_sgf import parse_pro_sgf
from app.models import ProGame

_SGF = (
    "(;GM[1]FF[4]SZ[19]KM[6.5]PB[Lee]PW[Cho]BR[9p]WR[9p]"
    "EV[Demo Cup]DT[2026-02-01]RE[W+2.5];B[pd];W[dp];B[pp];W[dd])"
)


async def _signup(client: AsyncClient, nickname: str) -> None:
    r = await client.post("/api/session", json={"nickname": nickname})
    assert r.status_code == 201, r.text


async def _insert_pro_game(db_session, collection: str = "masterpiece") -> int:
    parsed = parse_pro_sgf(_SGF)
    g = ProGame.from_parsed(parsed, collection=collection)
    db_session.add(g)
    await db_session.commit()
    await db_session.refresh(g)
    return g.id


@pytest.mark.asyncio
async def test_pro_list_requires_session(client: AsyncClient) -> None:
    fresh = AsyncClient(transport=client._transport, base_url=client.base_url)
    try:
        r = await fresh.get("/api/spectate/pro")
        assert r.status_code == 401
    finally:
        await fresh.aclose()


@pytest.mark.asyncio
async def test_pro_list_returns_inserted_game(
    client: AsyncClient, db_session
) -> None:
    gid = await _insert_pro_game(db_session)
    await _signup(client, "watcher")
    r = await client.get("/api/spectate/pro")
    assert r.status_code == 200
    rows = r.json()["rows"]
    row = next((x for x in rows if x["id"] == gid), None)
    assert row is not None
    assert row["black_player"] == "Lee"
    assert row["collection"] == "masterpiece"
    assert row["move_count"] == 4


@pytest.mark.asyncio
async def test_pro_list_collection_filter(
    client: AsyncClient, db_session
) -> None:
    mid = await _insert_pro_game(db_session, "masterpiece")
    await _signup(client, "watcher")
    r = await client.get("/api/spectate/pro", params={"collection": "recent"})
    ids = {x["id"] for x in r.json()["rows"]}
    assert mid not in ids


@pytest.mark.asyncio
async def test_pro_detail_returns_moves(
    client: AsyncClient, db_session
) -> None:
    gid = await _insert_pro_game(db_session)
    await _signup(client, "watcher")
    r = await client.get(f"/api/spectate/pro/{gid}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == gid
    assert len(body["moves"]) == 4
    assert body["moves"][0]["coord"] == "Q16"


@pytest.mark.asyncio
async def test_pro_detail_unknown_id_404(client: AsyncClient) -> None:
    await _signup(client, "watcher")
    r = await client.get("/api/spectate/pro/999999")
    assert r.status_code == 404


def _sgf(n: int) -> str:
    """n 마다 다른 content_hash 가 나오도록 결과값을 바꾼 SGF."""
    return (
        f"(;GM[1]FF[4]SZ[19]KM[6.5]PB[Lee]PW[Cho]BR[9p]WR[9p]"
        f"EV[Demo Cup]DT[2026-02-01]RE[W+{n}.5];B[pd];W[dp];B[pp];W[dd])"
    )


async def _insert_world_games(db_session, count: int) -> list[int]:
    ids: list[int] = []
    for n in range(count):
        g = ProGame.from_parsed(parse_pro_sgf(_sgf(n)), collection="world")
        db_session.add(g)
        await db_session.commit()
        await db_session.refresh(g)
        ids.append(g.id)
    return ids


@pytest.mark.asyncio
async def test_pro_list_reports_total(client: AsyncClient, db_session) -> None:
    await _insert_pro_game(db_session)
    await _signup(client, "watcher")
    r = await client.get("/api/spectate/pro")
    body = r.json()
    assert body["total"] >= 1
    assert body["total"] == len(body["rows"])


@pytest.mark.asyncio
async def test_pro_list_world_collection_filter(
    client: AsyncClient, db_session
) -> None:
    mid = await _insert_pro_game(db_session, "masterpiece")
    wids = await _insert_world_games(db_session, 1)
    await _signup(client, "watcher")
    r = await client.get("/api/spectate/pro", params={"collection": "world"})
    body = r.json()
    ids = {x["id"] for x in body["rows"]}
    assert wids[0] in ids
    assert mid not in ids
    assert body["total"] == 1
    assert all(x["collection"] == "world" for x in body["rows"])


@pytest.mark.asyncio
async def test_pro_list_pagination(client: AsyncClient, db_session) -> None:
    await _insert_world_games(db_session, 3)
    await _signup(client, "watcher")
    page1 = (
        await client.get(
            "/api/spectate/pro",
            params={"collection": "world", "limit": 2, "offset": 0},
        )
    ).json()
    page2 = (
        await client.get(
            "/api/spectate/pro",
            params={"collection": "world", "limit": 2, "offset": 2},
        )
    ).json()
    assert page1["total"] == 3
    assert page2["total"] == 3
    assert len(page1["rows"]) == 2
    assert len(page2["rows"]) == 1
    ids1 = {x["id"] for x in page1["rows"]}
    ids2 = {x["id"] for x in page2["rows"]}
    assert ids1.isdisjoint(ids2)
