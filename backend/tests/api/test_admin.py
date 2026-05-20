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
        "/api/admin/stats",
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
    body = r.json()
    assert body["total"] == 1
    assert body["offset"] == 0
    assert len(body["rows"]) == 1
    assert "user_rank" in body["rows"][0]
    assert body["rows"][0]["ai_rank"] == "5k"


@pytest.mark.asyncio
async def test_admin_games_status_filter(client: AsyncClient) -> None:
    await _signup(client, ADMIN_NICK)
    gid = await _create_game(client)
    # Resign so we have a finished game in the table.
    await client.post(f"/api/games/{gid}/resign")

    active = await client.get("/api/admin/games?status_=active")
    assert active.status_code == 200
    assert all(g["status"] == "active" for g in active.json()["rows"])

    resigned = await client.get("/api/admin/games?status_=resigned")
    assert resigned.status_code == 200
    rbody = resigned.json()
    assert all(g["status"] == "resigned" for g in rbody["rows"])
    assert rbody["total"] == 1


@pytest.mark.asyncio
async def test_admin_games_pagination(client: AsyncClient) -> None:
    """offset + limit page through games; total reflects the filter."""
    await _signup(client, ADMIN_NICK)
    for _ in range(5):
        await _create_game(client)

    r1 = await client.get("/api/admin/games?limit=2&offset=0")
    assert r1.status_code == 200
    p1 = r1.json()
    assert p1["total"] == 5
    assert p1["offset"] == 0
    assert p1["limit"] == 2
    assert len(p1["rows"]) == 2

    r2 = await client.get("/api/admin/games?limit=2&offset=2")
    p2 = r2.json()
    assert p2["offset"] == 2
    assert len(p2["rows"]) == 2
    # Pages don't overlap.
    assert {g["id"] for g in p1["rows"]}.isdisjoint({g["id"] for g in p2["rows"]})

    r3 = await client.get("/api/admin/games?limit=2&offset=4")
    p3 = r3.json()
    assert len(p3["rows"]) == 1  # last page has the leftover game


@pytest.mark.asyncio
async def test_admin_games_nickname_filter(client: AsyncClient) -> None:
    """Substring nickname search narrows the result set + total."""
    await _signup(client, ADMIN_NICK)
    await _create_game(client)
    # Another user with a distinct nickname.
    other = AsyncClient(transport=client._transport, base_url=client.base_url)
    try:
        await _signup(other, "alice_player")
        await _create_game(other)

        # ADMIN_NICK partial substring matches their own games.
        r = await client.get(f"/api/admin/games?nickname={ADMIN_NICK}")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert all(g["nickname"] == ADMIN_NICK for g in body["rows"])

        # Substring "alice" finds the other player.
        r2 = await client.get("/api/admin/games?nickname=alice")
        assert r2.json()["total"] == 1
        assert r2.json()["rows"][0]["nickname"] == "alice_player"

        # No match → empty result, total 0.
        r3 = await client.get("/api/admin/games?nickname=nobody_here_xyz")
        body3 = r3.json()
        assert body3["total"] == 0
        assert body3["rows"] == []
    finally:
        await other.aclose()


@pytest.mark.asyncio
async def test_admin_games_date_range(client: AsyncClient) -> None:
    """from_date / to_date constrains started_at; invalid dates are ignored."""
    import datetime as _dt
    await _signup(client, ADMIN_NICK)
    await _create_game(client)

    # UTC — Game.started_at is stored UTC, so the date filter must compare
    # against the UTC date, not the test machine's local date.
    utc_today = _dt.datetime.utcnow().date()
    today = utc_today.isoformat()
    tomorrow = (utc_today + _dt.timedelta(days=1)).isoformat()
    yesterday = (utc_today - _dt.timedelta(days=1)).isoformat()

    # today..today inclusive — includes the game.
    r = await client.get(f"/api/admin/games?from_date={today}&to_date={today}")
    assert r.json()["total"] == 1

    # tomorrow..tomorrow — excludes today's game.
    r2 = await client.get(f"/api/admin/games?from_date={tomorrow}&to_date={tomorrow}")
    assert r2.json()["total"] == 0

    # yesterday..today — includes.
    r3 = await client.get(f"/api/admin/games?from_date={yesterday}&to_date={today}")
    assert r3.json()["total"] == 1

    # Garbage date → ignored, behaves like no filter.
    r4 = await client.get("/api/admin/games?from_date=not-a-date")
    assert r4.json()["total"] == 1


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


@pytest.mark.asyncio
async def test_admin_disconnect_session_removes_row_and_ends_history(
    client: AsyncClient,
) -> None:
    """Admin DELETE /api/admin/sessions/{id} kills a live session: row gone,
    history row's ended_at set with admin_disconnect reason, and the
    nickname becomes available again."""
    await _signup(client, ADMIN_NICK)
    other = AsyncClient(transport=client._transport, base_url=client.base_url)
    try:
        r = await other.post("/api/session", json={"nickname": "victim_user"})
        assert r.status_code == 201

        sessions = (await client.get("/api/admin/sessions")).json()
        victim_sid = next(s["id"] for s in sessions if s["nickname"] == "victim_user")

        r = await client.delete(f"/api/admin/sessions/{victim_sid}")
        assert r.status_code == 204

        sessions_after = (await client.get("/api/admin/sessions")).json()
        assert not any(s["id"] == victim_sid for s in sessions_after)

        history = (await client.get("/api/admin/login-history")).json()
        row = next(
            (h for h in history if h["session_id"] == victim_sid),
            None,
        )
        assert row is not None
        assert row["ended_at"] is not None
        assert row["end_reason"] == "admin_disconnect"

        # Idempotent — second call on the now-gone session still 204s.
        r2 = await client.delete(f"/api/admin/sessions/{victim_sid}")
        assert r2.status_code == 204

        # Nickname is released, so the same name can be claimed again.
        retry = AsyncClient(transport=client._transport, base_url=client.base_url)
        try:
            r3 = await retry.post("/api/session", json={"nickname": "victim_user"})
            assert r3.status_code == 201, r3.text
        finally:
            await retry.aclose()
    finally:
        await other.aclose()


@pytest.mark.asyncio
async def test_admin_disconnect_non_admin_forbidden(client: AsyncClient) -> None:
    await _signup(client, "not_admin")
    r = await client.delete("/api/admin/sessions/9999")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_stats_empty(client: AsyncClient) -> None:
    """Stats endpoint returns full shape even when there's nothing to bucket."""
    await _signup(client, ADMIN_NICK)
    r = await client.get("/api/admin/stats?days=7&hourly_days=3&top=5")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["window_days_daily"] == 7
    assert body["window_days_hourly"] == 3
    assert len(body["daily_logins"]) == 7
    assert all(isinstance(b["count"], int) and b["count"] >= 0 for b in body["daily_logins"])
    assert len(body["daily_games"]) == 7
    assert len(body["hourly_activity"]) == 24
    assert {b["hour"] for b in body["hourly_activity"]} == set(range(24))
    # Lists are present (may be empty depending on test data)
    for key in (
        "rank_distribution",
        "ai_player_picks",
        "ai_style_picks",
        "board_size_picks",
        "handicap_picks",
        "nickname_summary",
    ):
        assert key in body
        assert isinstance(body[key], list)


@pytest.mark.asyncio
async def test_admin_stats_with_games(client: AsyncClient) -> None:
    """Picks reflect the games created in this session."""
    await _signup(client, ADMIN_NICK)
    await _create_game(client, ai_rank="5k")
    await _create_game(client, ai_rank="3d", handicap=2)
    r = await client.get("/api/admin/stats")
    assert r.status_code == 200
    body = r.json()
    # Today's started count should be >= 2 (two games we just created).
    today_iso = (await client.get("/api/admin/summary")).json()  # warm-up
    _ = today_iso
    today_bucket = body["daily_games"][-1]
    assert today_bucket["started"] >= 2
    # AI style "balanced" is the default; expect it to show up.
    styles = {row["label"] for row in body["ai_style_picks"]}
    assert "balanced" in styles
    # Two board sizes default to 19×19 — should appear in board picks.
    boards = {row["label"] for row in body["board_size_picks"]}
    assert "19" in boards


@pytest.mark.asyncio
async def test_admin_stats_nickname_summary(client: AsyncClient) -> None:
    """Nickname summary aggregates games + W/L per user_nickname."""
    await _signup(client, ADMIN_NICK)
    gid1 = await _create_game(client)
    gid2 = await _create_game(client)
    # Resign one — that becomes a loss for the user (winner = ai).
    await client.post(f"/api/games/{gid1}/resign")
    # Leave the other active.
    _ = gid2

    r = await client.get("/api/admin/stats")
    assert r.status_code == 200
    summary = r.json()["nickname_summary"]
    row = next((s for s in summary if s["nickname"] == ADMIN_NICK), None)
    assert row is not None, summary
    assert row["games"] == 2
    assert row["losses"] == 1
    assert row["wins"] == 0
    assert row["decisive"] == 1
    assert row["win_rate"] == 0.0


@pytest.mark.asyncio
async def test_admin_stats_window_clamped(client: AsyncClient) -> None:
    """Out-of-range days values get clamped without 4xx."""
    await _signup(client, ADMIN_NICK)
    r = await client.get("/api/admin/stats?days=999&hourly_days=999")
    assert r.status_code == 200
    body = r.json()
    assert body["window_days_daily"] <= 90
    assert body["window_days_hourly"] <= 30
