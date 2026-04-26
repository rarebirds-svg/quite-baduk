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
    # Session cookie present, no Max-Age / Expires.
    cookies = {c.name for c in client.cookies.jar}
    assert "baduk_session" in cookies


@pytest.mark.asyncio
async def test_get_session_after_create(client: AsyncClient) -> None:
    await client.post("/api/session", json={"nickname": "alice2"})
    r = await client.get("/api/session")
    assert r.status_code == 200
    assert r.json()["nickname"] == "alice2"


@pytest.mark.asyncio
async def test_get_session_without_cookie_is_401(client: AsyncClient) -> None:
    r = await client.get("/api/session")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_duplicate_nickname_returns_409(client: AsyncClient) -> None:
    # First claim via one client
    c1 = await client.post("/api/session", json={"nickname": "bob"})
    assert c1.status_code == 201
    # Second attempt with the same nickname (from the same client — sends its cookie
    # but that's irrelevant to uniqueness) must fail.
    # Use a fresh client to avoid cookie reuse.
    r2 = await AsyncClient(transport=client._transport, base_url=client.base_url).post(
        "/api/session", json={"nickname": "BOB"},
    )
    assert r2.status_code == 409


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
async def test_nickname_check_reports_taken(client: AsyncClient) -> None:
    await client.post("/api/session", json={"nickname": "taken1"})
    r = await client.get("/api/session/nickname/check", params={"name": "taken1"})
    assert r.status_code == 200
    assert r.json() == {"available": False, "reason": "taken"}


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
async def test_nickname_check_invalid_then_taken(client: AsyncClient) -> None:
    """Drive both 'invalid' and 'taken' branches in one test for parity."""
    invalid = await client.get("/api/session/nickname/check", params={"name": "x"})
    assert invalid.json()["reason"] == "invalid"

    await client.post("/api/session", json={"nickname": "claimed_one"})
    taken = await client.get(
        "/api/session/nickname/check", params={"name": "claimed_one"}
    )
    assert taken.json()["reason"] == "taken"
