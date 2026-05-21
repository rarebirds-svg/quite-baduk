# 공개 관전 API(/api/spectate) 계약 테스트 — 노출 필터·상세 접근 검증
from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _signup(client: AsyncClient, nickname: str) -> None:
    r = await client.post("/api/session", json={"nickname": nickname})
    assert r.status_code == 201, r.text


async def _create_game(client: AsyncClient, *, ai_rank: str = "5k") -> int:
    r = await client.post(
        "/api/games",
        json={"ai_rank": ai_rank, "handicap": 0, "user_color": "black"},
    )
    assert r.status_code == 201, r.text
    return int(r.json()["id"])


@pytest.mark.asyncio
async def test_spectate_requires_session(client: AsyncClient) -> None:
    """닉네임 세션 없이는 401."""
    fresh = AsyncClient(transport=client._transport, base_url=client.base_url)
    try:
        r = await fresh.get("/api/spectate")
        assert r.status_code == 401
    finally:
        await fresh.aclose()


@pytest.mark.asyncio
async def test_spectate_lists_active_game_with_live_session(
    client: AsyncClient,
) -> None:
    """진행 중 + 세션 생존 대국은 목록에 노출."""
    await _signup(client, "watcher")
    gid = await _create_game(client)
    r = await client.get("/api/spectate")
    assert r.status_code == 200
    rows = r.json()["rows"]
    row = next((x for x in rows if x["id"] == gid), None)
    assert row is not None
    assert row["status"] == "active"
    assert row["is_live"] is True


@pytest.mark.asyncio
async def test_spectate_lists_finished_game(client: AsyncClient) -> None:
    """종료(기권) 대국은 목록에 노출."""
    await _signup(client, "watcher")
    gid = await _create_game(client)
    await client.post(f"/api/games/{gid}/resign")
    r = await client.get("/api/spectate")
    row = next((x for x in r.json()["rows"] if x["id"] == gid), None)
    assert row is not None
    assert row["status"] == "resigned"
    assert row["is_live"] is False


@pytest.mark.asyncio
async def test_spectate_hides_abandoned_game(client: AsyncClient) -> None:
    """active인데 세션이 사라진 대국(버려진 대국)은 목록·상세 모두에서 제외."""
    # 다른 사용자가 active 대국을 만든 뒤 세션 종료.
    other = AsyncClient(transport=client._transport, base_url=client.base_url)
    try:
        await _signup(other, "quitter")
        gid = await _create_game(other)
        # 세션 종료 → Session 행 삭제 → 대국은 active로 남되 버려짐.
        await other.post("/api/session/end")
    finally:
        await other.aclose()

    await _signup(client, "watcher")
    r = await client.get("/api/spectate")
    ids = {x["id"] for x in r.json()["rows"]}
    assert gid not in ids, "버려진 active 대국이 목록에 노출됨"

    # 상세도 404.
    detail = await client.get(f"/api/spectate/{gid}")
    assert detail.status_code == 404


@pytest.mark.asyncio
async def test_spectate_hides_admin_game(client: AsyncClient) -> None:
    """관리자 닉네임으로 둔 대국은 목록·상세 모두에서 제외."""
    admin = AsyncClient(transport=client._transport, base_url=client.base_url)
    try:
        await _signup(admin, "대공")
        gid = await _create_game(admin)
        await admin.post(f"/api/games/{gid}/resign")
    finally:
        await admin.aclose()

    await _signup(client, "watcher")
    r = await client.get("/api/spectate")
    ids = {x["id"] for x in r.json()["rows"]}
    assert gid not in ids, "관리자 대국이 관전 목록에 노출됨"

    detail = await client.get(f"/api/spectate/{gid}")
    assert detail.status_code == 404


@pytest.mark.asyncio
async def test_spectate_detail_returns_moves(client: AsyncClient) -> None:
    """관전 가능 대국의 상세는 수순을 포함해 200."""
    await _signup(client, "watcher")
    gid = await _create_game(client)
    r = await client.get(f"/api/spectate/{gid}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == gid
    assert isinstance(body["moves"], list)


@pytest.mark.asyncio
async def test_spectate_detail_unknown_id_404(client: AsyncClient) -> None:
    await _signup(client, "watcher")
    r = await client.get("/api/spectate/999999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_spectate_detail_other_users_finished_game(
    client: AsyncClient,
) -> None:
    """소유자가 아니어도 종료된 남의 대국을 관전 상세로 볼 수 있다."""
    other = AsyncClient(transport=client._transport, base_url=client.base_url)
    try:
        await _signup(other, "opponent")
        gid = await _create_game(other)
        await other.post(f"/api/games/{gid}/resign")
    finally:
        await other.aclose()

    await _signup(client, "watcher")
    r = await client.get(f"/api/spectate/{gid}")
    assert r.status_code == 200
    assert r.json()["id"] == gid
