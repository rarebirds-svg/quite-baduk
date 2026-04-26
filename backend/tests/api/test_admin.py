"""Contract tests for /api/admin/* — exercise the auth gate and each
endpoint's happy path so we cover the bulk of admin.py."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

# The admin gate is keyed off a fixed nickname (deps.ADMIN_NICKNAME_KEYS).
# Registering this nickname is how a test "becomes" admin.
ADMIN_NICK = "대공"


async def _signup(client: AsyncClient, nickname: str) -> None:
    r = await client.post("/api/session", json={"nickname": nickname})
    assert r.status_code == 201, r.text


async def _create_game(
    client: AsyncClient, *, ai_rank: str = "5k", handicap: int = 0
) -> int:
    r = await client.post(
        "/api/games",
        json={
            "ai_rank": ai_rank,
            "handicap": handicap,
            "user_color": "black",
        },
    )
    assert r.status_code == 201, r.text
    return int(r.json()["id"])


@pytest.mark.asyncio
async def test_admin_me_reports_admin_flag(client: AsyncClient) -> None:
    await _signup(client, ADMIN_NICK)
    r = await client.get("/api/admin/me")
    assert r.status_code == 200
    assert r.json() == {"is_admin": True}


@pytest.mark.asyncio
async def test_admin_me_non_admin_user(client: AsyncClient) -> None:
    await _signup(client, "regular_user")
    r = await client.get("/api/admin/me")
    assert r.status_code == 200
    assert r.json() == {"is_admin": False}


@pytest.mark.asyncio
async def test_admin_endpoints_403_for_non_admin(client: AsyncClient) -> None:
    await _signup(client, "not_admin")
    for path in (
        "/api/admin/summary",
        "/api/admin/games",
        "/api/admin/sessions",
        "/api/admin/login-history",
        "/api/admin/engine",
    ):
        r = await client.get(path)
        assert r.status_code == 403, f"{path} should require admin"


@pytest.mark.asyncio
async def test_admin_summary_zero_games(client: AsyncClient) -> None:
    await _signup(client, ADMIN_NICK)
    r = await client.get("/api/admin/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["total_games"] == 0
    assert body["active_games"] == 0
    assert body["user_win_rate"] == 0.0
    assert body["live_sessions"] == 0


@pytest.mark.asyncio
async def test_admin_summary_with_games(client: AsyncClient) -> None:
    await _signup(client, ADMIN_NICK)
    await _create_game(client)
    r = await client.get("/api/admin/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["total_games"] == 1
    assert body["active_games"] == 1


@pytest.mark.asyncio
async def test_admin_games_list_includes_user_rank(client: AsyncClient) -> None:
    await _signup(client, ADMIN_NICK)
    await _create_game(client)
    r = await client.get("/api/admin/games")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert "user_rank" in rows[0]
    assert rows[0]["ai_rank"] == "5k"


@pytest.mark.asyncio
async def test_admin_games_status_filter(client: AsyncClient) -> None:
    await _signup(client, ADMIN_NICK)
    gid = await _create_game(client)
    # Resign so we have a finished game in the table.
    await client.post(f"/api/games/{gid}/resign")

    active = await client.get("/api/admin/games?status_=active")
    assert active.status_code == 200
    assert all(g["status"] == "active" for g in active.json())

    resigned = await client.get("/api/admin/games?status_=resigned")
    assert resigned.status_code == 200
    assert all(g["status"] == "resigned" for g in resigned.json())
    assert len(resigned.json()) == 1


@pytest.mark.asyncio
async def test_admin_sessions_list(client: AsyncClient) -> None:
    await _signup(client, ADMIN_NICK)
    r = await client.get("/api/admin/sessions")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 1
    assert any(s["nickname"] == ADMIN_NICK for s in rows)


@pytest.mark.asyncio
async def test_admin_session_detail_aggregates_games(client: AsyncClient) -> None:
    await _signup(client, ADMIN_NICK)
    await _create_game(client)
    sessions = (await client.get("/api/admin/sessions")).json()
    sid = next(s["id"] for s in sessions if s["nickname"] == ADMIN_NICK)

    r = await client.get(f"/api/admin/sessions/{sid}")
    assert r.status_code == 200
    body = r.json()
    assert body["nickname"] == ADMIN_NICK
    assert body["total_games"] == 1
    assert isinstance(body["games"], list)
    assert isinstance(body["history"], list)


@pytest.mark.asyncio
async def test_admin_engine_health_response_shape(client: AsyncClient) -> None:
    await _signup(client, ADMIN_NICK)
    r = await client.get("/api/admin/engine")
    assert r.status_code == 200
    body = r.json()
    # Mode depends on whether KATAGO_MOCK was set before pydantic-settings
    # cached. Just assert the response is well-formed.
    assert body["mode"] in ("mock", "real")
    assert isinstance(body["is_alive"], bool)
    assert "backend_started_at" in body


@pytest.mark.asyncio
async def test_admin_login_history_records_session_create(client: AsyncClient) -> None:
    await _signup(client, ADMIN_NICK)
    r = await client.get("/api/admin/login-history")
    assert r.status_code == 200
    rows = r.json()
    # Just creating the admin session should leave a login row.
    assert any(row["nickname"] == ADMIN_NICK for row in rows)


@pytest.mark.asyncio
async def test_admin_session_detail_unknown_id_returns_empty(
    client: AsyncClient,
) -> None:
    await _signup(client, ADMIN_NICK)
    r = await client.get("/api/admin/sessions/9999")
    assert r.status_code == 200
    body = r.json()
    # No live session and no history row → empty detail rather than 500/404.
    assert body["nickname"] == ""
    assert body["total_games"] == 0
    assert body["games"] == []
    assert body["history"] == []


@pytest.mark.asyncio
async def test_admin_session_detail_via_live_session(
    client: AsyncClient,
) -> None:
    """Lock down the live-session detail endpoint with games + history."""
    # Set up a regular user with one game, leave the session open.
    await _signup(client, "live_user")
    g = await client.post(
        "/api/games",
        json={"ai_rank": "5k", "handicap": 0, "user_color": "black"},
    )
    assert g.status_code == 201

    # Switch to admin and query the live session through admin/sessions list.
    other = AsyncClient(transport=client._transport, base_url=client.base_url)
    try:
        await _signup(other, ADMIN_NICK)
        sessions = (await other.get("/api/admin/sessions")).json()
        target = next(s for s in sessions if s["nickname"] == "live_user")
        r = await other.get(f"/api/admin/sessions/{target['id']}")
        assert r.status_code == 200
        body = r.json()
        assert body["nickname"] == "live_user"
        assert body["total_games"] >= 1
        assert any(g["nickname"] == "live_user" for g in body["games"])
    finally:
        await other.aclose()


@pytest.mark.asyncio
async def test_admin_endpoints_401_without_session(client: AsyncClient) -> None:
    """No cookie at all → 401 (auth gate runs before the admin gate)."""
    fresh = AsyncClient(transport=client._transport, base_url=client.base_url)
    try:
        r = await fresh.get("/api/admin/summary")
        assert r.status_code == 401
    finally:
        await fresh.aclose()
    # silence unused-import lint
    _ = ASGITransport
