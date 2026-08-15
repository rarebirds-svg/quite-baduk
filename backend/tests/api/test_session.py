"""Contract tests for /api/session."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_session_sets_cookie_and_returns_public_info(client: AsyncClient) -> None:
    r = await client.post("/api/session", json={"nickname": "alice"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["nickname"] == "alice"
    # Session cookie present, and persisted for 90 days.
    cookies = {c.name for c in client.cookies.jar}
    assert "baduk_session" in cookies
    assert "Max-Age=7776000" in r.headers["set-cookie"]


@pytest.mark.asyncio
async def test_get_session_after_create(client: AsyncClient) -> None:
    await client.post("/api/session", json={"nickname": "alice2"})
    r = await client.get("/api/session")
    assert r.status_code == 200
    assert r.json()["nickname"] == "alice2"


@pytest.mark.asyncio
async def test_get_session_reissues_sliding_cookie(client: AsyncClient) -> None:
    """방문할 때마다 쿠키가 재발급되어 90일 만료가 앞으로 밀린다."""
    await client.post("/api/session", json={"nickname": "slider"})
    r = await client.get("/api/session")
    assert r.status_code == 200
    set_cookie = r.headers["set-cookie"]
    assert "baduk_session=" in set_cookie
    assert "Max-Age=7776000" in set_cookie


@pytest.mark.asyncio
async def test_get_session_without_cookie_is_401(client: AsyncClient) -> None:
    r = await client.get("/api/session")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_duplicate_nickname_creates_independent_sessions(client: AsyncClient) -> None:
    """닉네임은 더 이상 유니크하지 않다. 같은 이름의 두 세션은 각각 생성되고
    서로의 대국 목록이 보이지 않아야 한다."""
    c1 = await client.post("/api/session", json={"nickname": "bob"})
    assert c1.status_code == 201

    other = AsyncClient(transport=client._transport, base_url=client.base_url)
    c2 = await other.post("/api/session", json={"nickname": "BOB"})
    assert c2.status_code == 201
    assert c1.json()["id"] != c2.json()["id"]
    assert c1.json()["token"] != c2.json()["token"]

    # 첫 세션이 만든 대국은 두 번째 세션에게 보이지 않는다.
    g = await client.post(
        "/api/games",
        json={"ai_rank": "5k", "handicap": 0, "user_color": "black", "board_size": 9},
    )
    assert g.status_code == 201, g.text
    mine = await client.get("/api/games")
    assert [row["id"] for row in mine.json()] == [g.json()["id"]]
    theirs = await other.get("/api/games")
    assert theirs.json() == []


@pytest.mark.asyncio
async def test_end_session_deletes_row_and_clears_cookie(client: AsyncClient) -> None:
    await client.post("/api/session", json={"nickname": "carol"})
    r = await client.post("/api/session/end")
    assert r.status_code == 204
    # GET /api/session with the stale cookie must 401.
    r2 = await client.get("/api/session")
    assert r2.status_code == 401


@pytest.mark.asyncio
async def test_invalid_nickname_is_422(client: AsyncClient) -> None:
    r = await client.post("/api/session", json={"nickname": "a"})
    assert r.status_code == 422
    r2 = await client.post("/api/session", json={"nickname": "alice😀"})
    assert r2.status_code == 422


@pytest.mark.asyncio
async def test_nickname_check_reports_availability(client: AsyncClient) -> None:
    r = await client.get("/api/session/nickname/check", params={"name": "freshname"})
    assert r.status_code == 200
    assert r.json()["available"] is True


@pytest.mark.asyncio
async def test_nickname_check_allows_reuse_of_live_nickname(client: AsyncClient) -> None:
    """일반 닉네임은 이미 쓰이고 있어도 항상 사용 가능하다."""
    await client.post("/api/session", json={"nickname": "taken1"})
    r = await client.get("/api/session/nickname/check", params={"name": "taken1"})
    assert r.status_code == 200
    assert r.json()["available"] is True


@pytest.mark.asyncio
async def test_admin_nickname_is_reserved_while_live(client: AsyncClient) -> None:
    """어드민 예약 키는 라이브 세션이 있으면 재선점할 수 없다 — 어드민 게이트가
    닉네임 키 하나에 걸려 있기 때문이다."""
    first = await client.post("/api/session", json={"nickname": "대공"})
    assert first.status_code == 201

    other = AsyncClient(transport=client._transport, base_url=client.base_url)
    dup = await other.post("/api/session", json={"nickname": "대공"})
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "nickname_taken"

    check = await other.get("/api/session/nickname/check", params={"name": "대공"})
    assert check.json() == {"available": False, "reason": "taken"}

    # 세션이 끝나면 다시 열린다.
    assert (await client.post("/api/session/end")).status_code == 204
    assert (
        await other.post("/api/session", json={"nickname": "대공"})
    ).status_code == 201


@pytest.mark.asyncio
async def test_nickname_check_reports_invalid(client: AsyncClient) -> None:
    r = await client.get("/api/session/nickname/check", params={"name": "🙂"})
    assert r.status_code == 200
    assert r.json() == {"available": False, "reason": "invalid"}


@pytest.mark.asyncio
async def test_end_session_idempotent_without_cookie(client: AsyncClient) -> None:
    """No cookie at all → 204, not 401. The endpoint is fired twice during
    pagehide on most browsers, so it must be idempotent."""
    r = await client.post("/api/session/end")
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_end_session_idempotent_with_stale_cookie(client: AsyncClient) -> None:
    """A cookie pointing to a deleted session row should still return 204."""
    await client.post("/api/session", json={"nickname": "ephemeral"})
    # First end deletes the row; second end with the same (now-stale) cookie
    # must not 500 or 401.
    assert (await client.post("/api/session/end")).status_code == 204
    # Cookie may have been cleared by the first call; force a stale value.
    client.cookies.set("baduk_session", "definitely-not-a-real-token")
    assert (await client.post("/api/session/end")).status_code == 204


@pytest.mark.asyncio
async def test_create_session_too_long_nickname_is_422(client: AsyncClient) -> None:
    long_name = "x" * 100
    r = await client.post("/api/session", json={"nickname": long_name})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_nickname_check_invalid_then_available(client: AsyncClient) -> None:
    """Drive both the 'invalid' and the available branch in one test."""
    invalid = await client.get("/api/session/nickname/check", params={"name": "x"})
    assert invalid.json()["reason"] == "invalid"

    await client.post("/api/session", json={"nickname": "claimed_one"})
    reused = await client.get(
        "/api/session/nickname/check", params={"name": "claimed_one"}
    )
    assert reused.json()["available"] is True


@pytest.mark.asyncio
async def test_create_session_returns_token_in_body(client: AsyncClient) -> None:
    r = await client.post("/api/session", json={"nickname": "tokuser"})
    assert r.status_code == 201
    body = r.json()
    assert isinstance(body.get("token"), str)
    assert len(body["token"]) >= 32
    # GET /api/session은 토큰을 재노출하지 않는다 (생성 시 1회만).
    r2 = await client.get("/api/session")
    assert r2.status_code == 200
    assert r2.json().get("token") is None


@pytest.mark.asyncio
async def test_bearer_header_authenticates_without_cookie(client: AsyncClient) -> None:
    r = await client.post("/api/session", json={"nickname": "appuser"})
    token = r.json()["token"]
    client.cookies.clear()
    r2 = await client.get("/api/session", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["nickname"] == "appuser"


@pytest.mark.asyncio
async def test_bad_bearer_token_is_401(client: AsyncClient) -> None:
    client.cookies.clear()
    r = await client.get("/api/session", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_end_session_via_bearer_header(client: AsyncClient) -> None:
    r = await client.post("/api/session", json={"nickname": "enduser"})
    token = r.json()["token"]
    client.cookies.clear()
    r2 = await client.post(
        "/api/session/end", headers={"Authorization": f"Bearer {token}"}
    )
    assert r2.status_code == 204
    r3 = await client.get("/api/session", headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 401


@pytest.mark.asyncio
async def test_cookie_wins_over_bearer_header(client: AsyncClient) -> None:
    # 쿠키(첫 세션)와 다른 세션의 Bearer 헤더가 동시에 오면 쿠키가 이긴다.
    await client.post("/api/session", json={"nickname": "cookieuser"})
    from httpx import AsyncClient as _AC

    other = _AC(transport=client._transport, base_url=client.base_url)
    r_other = await other.post("/api/session", json={"nickname": "headeruser"})
    other_token = r_other.json()["token"]
    r = await client.get(
        "/api/session", headers={"Authorization": f"Bearer {other_token}"}
    )
    assert r.status_code == 200
    assert r.json()["nickname"] == "cookieuser"


@pytest.mark.asyncio
async def test_lowercase_bearer_scheme_accepted(client: AsyncClient) -> None:
    r = await client.post("/api/session", json={"nickname": "lcuser"})
    token = r.json()["token"]
    client.cookies.clear()
    r2 = await client.get("/api/session", headers={"Authorization": f"bearer {token}"})
    assert r2.status_code == 200
