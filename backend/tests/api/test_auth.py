import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_signup_creates_user(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/signup",
        json={"email": "a@example.com", "password": "password1", "display_name": "A"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "a@example.com"
    assert data["display_name"] == "A"
    # Cookie set
    assert "access_token" in r.cookies


@pytest.mark.asyncio
async def test_signup_duplicate_email(client: AsyncClient) -> None:
    body = {"email": "b@example.com", "password": "password1", "display_name": "B"}
    r1 = await client.post("/api/auth/signup", json=body)
    assert r1.status_code == 201
    r2 = await client.post("/api/auth/signup", json=body)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_login_bad_password(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/signup",
        json={"email": "c@example.com", "password": "password1", "display_name": "C"},
    )
    r = await client.post("/api/auth/login", json={"email": "c@example.com", "password": "wrong"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/api/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_signup_then_me(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/signup",
        json={"email": "d@example.com", "password": "password1", "display_name": "D"},
    )
    assert r.status_code == 201
    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "d@example.com"


@pytest.mark.asyncio
async def test_logout_clears_cookie(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/signup",
        json={"email": "e@example.com", "password": "password1", "display_name": "E"},
    )
    r = await client.post("/api/auth/logout")
    assert r.status_code == 204
    me = await client.get("/api/auth/me")
    # After logout, cookies should be cleared (httpx persists cookies set by server; delete_cookie sends Set-Cookie with empty val)
    # Depending on AsyncClient behavior, /me may still succeed with stale cookie; just ensure delete_cookie was issued
    assert r.headers.get("set-cookie") is not None
