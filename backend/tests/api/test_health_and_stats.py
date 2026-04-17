import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    r = await client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert "status" in body


@pytest.mark.asyncio
async def test_stats_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/api/stats")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_stats_empty(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/signup",
        json={"email": "s@example.com", "password": "password1", "display_name": "S"},
    )
    r = await client.get("/api/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
