# 관리자 프로 기보 API(/api/admin/pro-games) 테스트 — 업로드·중복·삭제·게이트
from __future__ import annotations

import pytest
from httpx import AsyncClient

_SGF = (
    "(;GM[1]FF[4]SZ[19]KM[6.5]PB[Shin]PW[Park]BR[9p]WR[9p]"
    "EV[Upload Cup]DT[2026-03-01]RE[B+R];B[pd];W[dp];B[pp];W[dd])"
)


async def _signup(client: AsyncClient, nickname: str) -> None:
    r = await client.post("/api/session", json={"nickname": nickname})
    assert r.status_code == 201, r.text


def _sgf_file(name: str, content: str) -> tuple[str, tuple[str, bytes, str]]:
    return ("files", (name, content.encode("utf-8"), "application/x-go-sgf"))


@pytest.mark.asyncio
async def test_upload_requires_admin(client: AsyncClient) -> None:
    await _signup(client, "normaluser")
    r = await client.post(
        "/api/admin/pro-games", files=[_sgf_file("g.sgf", _SGF)]
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_uploads_and_dedups(client: AsyncClient) -> None:
    await _signup(client, "대공")
    r1 = await client.post(
        "/api/admin/pro-games", files=[_sgf_file("g.sgf", _SGF)]
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["inserted"] == 1

    # 같은 SGF 재업로드 → 중복 스킵.
    r2 = await client.post(
        "/api/admin/pro-games", files=[_sgf_file("g.sgf", _SGF)]
    )
    assert r2.json()["inserted"] == 0
    assert r2.json()["skipped"] == 1


@pytest.mark.asyncio
async def test_admin_upload_dedups_within_batch(client: AsyncClient) -> None:
    await _signup(client, "대공")
    r = await client.post(
        "/api/admin/pro-games",
        files=[_sgf_file("a.sgf", _SGF), _sgf_file("b.sgf", _SGF)],
    )
    assert r.status_code == 200, r.text
    assert r.json()["inserted"] == 1
    assert r.json()["skipped"] == 1


@pytest.mark.asyncio
async def test_admin_upload_rejects_bad_sgf(client: AsyncClient) -> None:
    await _signup(client, "대공")
    r = await client.post(
        "/api/admin/pro-games", files=[_sgf_file("bad.sgf", "not sgf")]
    )
    assert r.status_code == 200
    assert r.json()["inserted"] == 0
    assert "bad.sgf" in r.json()["failed"]


@pytest.mark.asyncio
async def test_admin_lists_and_deletes(client: AsyncClient) -> None:
    await _signup(client, "대공")
    await client.post("/api/admin/pro-games", files=[_sgf_file("g.sgf", _SGF)])

    lst = await client.get("/api/admin/pro-games")
    assert lst.status_code == 200
    rows = lst.json()["rows"]
    assert len(rows) == 1
    gid = rows[0]["id"]

    d = await client.delete(f"/api/admin/pro-games/{gid}")
    assert d.status_code == 200

    lst2 = await client.get("/api/admin/pro-games")
    assert lst2.json()["rows"] == []


@pytest.mark.asyncio
async def test_admin_delete_unknown_404(client: AsyncClient) -> None:
    await _signup(client, "대공")
    r = await client.delete("/api/admin/pro-games/999999")
    assert r.status_code == 404
