import pytest
from httpx import AsyncClient


async def _signup(client: AsyncClient, email: str = "p@example.com") -> None:
    await client.post(
        "/api/auth/signup",
        json={"email": email, "password": "password1", "display_name": "P"},
    )


@pytest.mark.asyncio
async def test_create_game(client: AsyncClient) -> None:
    await _signup(client)
    r = await client.post(
        "/api/games",
        json={"ai_rank": "5k", "handicap": 0, "user_color": "black"},
    )
    assert r.status_code == 201
    g = r.json()
    assert g["ai_rank"] == "5k"
    assert g["handicap"] == 0
    assert g["komi"] == 6.5


@pytest.mark.asyncio
async def test_create_handicap_game(client: AsyncClient) -> None:
    await _signup(client)
    r = await client.post(
        "/api/games",
        json={"ai_rank": "1d", "handicap": 4, "user_color": "black"},
    )
    assert r.status_code == 201
    g = r.json()
    assert g["handicap"] == 4
    assert g["komi"] == 0.5


@pytest.mark.asyncio
async def test_list_games(client: AsyncClient) -> None:
    await _signup(client)
    await client.post("/api/games", json={"ai_rank": "5k", "handicap": 0, "user_color": "black"})
    await client.post("/api/games", json={"ai_rank": "1k", "handicap": 2, "user_color": "black"})
    r = await client.get("/api/games")
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_cannot_access_other_users_game(client: AsyncClient) -> None:
    await _signup(client, email="u1@example.com")
    r = await client.post("/api/games", json={"ai_rank": "5k", "handicap": 0, "user_color": "black"})
    game_id = r.json()["id"]
    # New user
    await client.post("/api/auth/logout")
    await _signup(client, email="u2@example.com")
    r2 = await client.get(f"/api/games/{game_id}")
    assert r2.status_code == 403


@pytest.mark.asyncio
async def test_resign(client: AsyncClient) -> None:
    await _signup(client)
    r = await client.post("/api/games", json={"ai_rank": "5k", "handicap": 0, "user_color": "black"})
    game_id = r.json()["id"]
    r2 = await client.post(f"/api/games/{game_id}/resign")
    assert r2.status_code == 200
    g = r2.json()
    assert g["status"] == "resigned"
    assert g["result"] == "W+R"


@pytest.mark.asyncio
async def test_sgf_download(client: AsyncClient) -> None:
    await _signup(client)
    r = await client.post("/api/games", json={"ai_rank": "5k", "handicap": 0, "user_color": "black"})
    game_id = r.json()["id"]
    await client.post(f"/api/games/{game_id}/resign")
    r2 = await client.get(f"/api/games/{game_id}/sgf")
    assert r2.status_code == 200
    assert "GM[1]" in r2.text


@pytest.mark.asyncio
async def test_hint(client: AsyncClient) -> None:
    await _signup(client)
    r = await client.post("/api/games", json={"ai_rank": "5k", "handicap": 0, "user_color": "black"})
    game_id = r.json()["id"]
    r2 = await client.post(f"/api/games/{game_id}/hint")
    assert r2.status_code == 200
    assert "hints" in r2.json()
