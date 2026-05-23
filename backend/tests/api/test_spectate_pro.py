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


_SGF2 = (
    "(;GM[1]FF[4]SZ[19]KM[6.5]PB[Kim]PW[Park]BR[9p]WR[9p]"
    "DT[2026-01-01]RE[B+R];B[pd];W[dp])"
)
_SGF3 = (
    "(;GM[1]FF[4]SZ[19]KM[6.5]PB[Cho]PW[Shin]BR[9p]WR[9p]"
    "DT[2025-06-01]RE[W+R];B[qd];W[cd])"
)


async def _insert_pro_game_sgf(
    db_session, sgf: str, collection: str = "masterpiece"
) -> int:
    parsed = parse_pro_sgf(sgf)
    g = ProGame.from_parsed(parsed, collection=collection)
    db_session.add(g)
    await db_session.commit()
    await db_session.refresh(g)
    return g.id


@pytest.mark.asyncio
async def test_sitemap_endpoint_returns_all_pro_games(
    client: AsyncClient, db_session
) -> None:
    # content_hash는 SGF 기준 — 서로 다른 SGF를 사용해 UNIQUE 충돌 방지
    id1 = await _insert_pro_game_sgf(db_session, _SGF, "masterpiece")
    id2 = await _insert_pro_game_sgf(db_session, _SGF2, "recent")
    id3 = await _insert_pro_game_sgf(db_session, _SGF3, "masterpiece")

    resp = await client.get("/api/spectate/pro/sitemap")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    inserted_ids = {id1, id2, id3}
    returned_ids = {item["id"] for item in data}
    assert inserted_ids.issubset(returned_ids)
    item = next(x for x in data if x["id"] == id1)
    assert "id" in item
    assert "created_at" in item
    assert set(item.keys()) == {"id", "created_at"}  # 다른 필드 누설 안 됨


@pytest.mark.asyncio
async def test_themes_list_endpoint_returns_catalog(client: AsyncClient) -> None:
    resp = await client.get("/api/spectate/pro/themes")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    slugs = [t["slug"] for t in data]
    assert "masterpieces" in slugs
    item = data[0]
    assert set(item.keys()) >= {"slug", "label", "description", "count"}


@pytest.mark.asyncio
async def test_themes_list_includes_counts(client: AsyncClient) -> None:
    resp = await client.get("/api/spectate/pro/themes")
    for item in resp.json():
        assert isinstance(item["count"], int)
        assert item["count"] >= 0


@pytest.mark.asyncio
async def test_theme_detail_known_slug(client: AsyncClient) -> None:
    resp = await client.get("/api/spectate/pro/theme/masterpieces")
    assert resp.status_code == 200
    data = resp.json()
    assert "games" in data
    assert "total" in data
    assert isinstance(data["games"], list)
    assert isinstance(data["total"], int)


@pytest.mark.asyncio
async def test_theme_detail_unknown_slug_404(client: AsyncClient) -> None:
    resp = await client.get("/api/spectate/pro/theme/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_pick_monthly_returns_game(client: AsyncClient) -> None:
    resp = await client.get("/api/spectate/pro/pick/monthly/2026-05")
    # 200 또는 404 둘 다 허용 — DB 상태 의존.
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "id" in data
        assert data["yyyymm"] == "2026-05"


@pytest.mark.asyncio
async def test_pick_monthly_deterministic(client: AsyncClient) -> None:
    a = await client.get("/api/spectate/pro/pick/monthly/2026-05")
    b = await client.get("/api/spectate/pro/pick/monthly/2026-05")
    assert a.status_code == b.status_code
    if a.status_code == 200:
        assert a.json()["id"] == b.json()["id"]


@pytest.mark.asyncio
async def test_pick_monthly_invalid_format(client: AsyncClient) -> None:
    resp = await client.get("/api/spectate/pro/pick/monthly/2026-13")
    assert resp.status_code == 400
