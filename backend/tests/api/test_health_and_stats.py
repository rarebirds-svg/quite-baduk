import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    r = await client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert "status" in body


@pytest.mark.asyncio
async def test_health_db_failure_returns_degraded(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Force `db.execute` to blow up so we exercise the `db_ok = False`
    branch of the health endpoint."""
    import app.api.health as _health

    class _FailingExec:
        async def execute(self, *_a: object, **_kw: object) -> None:
            raise RuntimeError("simulated DB failure")

    async def fake_get_db() -> object:
        # Generator-style override matching `Annotated[..., Depends(get_db)]`.
        yield _FailingExec()

    from app.deps import get_db
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_db] = fake_get_db

    from httpx import ASGITransport
    from httpx import AsyncClient as _AC
    async with _AC(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["db"] is False
    assert body["status"] == "degraded"
    _ = _health  # silence unused-import lint


@pytest.mark.asyncio
async def test_stats_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/api/stats")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_stats_empty(client: AsyncClient) -> None:
    await client.post("/api/session", json={"nickname": "stats_user"})
    r = await client.get("/api/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_stats_aggregates_by_rank_board_player(client: AsyncClient) -> None:
    """Drive the by_rank / by_board_size / by_ai_player buckets so the
    aggregation paths in stats.py get exercised."""
    await client.post("/api/session", json={"nickname": "stats_user2"})
    g = await client.post(
        "/api/games",
        json={
            "ai_rank": "5k",
            "handicap": 0,
            "user_color": "black",
            "ai_player": "lee_sedol",
        },
    )
    assert g.status_code == 201
    gid = g.json()["id"]
    # Resign to produce a finished, decisive row for win-rate aggregation.
    assert (await client.post(f"/api/games/{gid}/resign")).status_code == 200

    body = (await client.get("/api/stats")).json()
    assert body["total"] >= 1
    assert isinstance(body["by_rank"], list)
    assert isinstance(body["by_board_size"], list)
    assert isinstance(body["by_ai_player"], list)
    assert any(b["ai_rank"] == "5k" for b in body["by_rank"])
    assert any(b["ai_player"] == "lee_sedol" for b in body["by_ai_player"])
    assert isinstance(body["breakdown"], list)
    assert len(body["breakdown"]) >= 1
