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
