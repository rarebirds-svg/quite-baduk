"""Daily challenge endpoints — happy path + auth + grading verdicts."""
from __future__ import annotations

import datetime as _dt

import pytest
from httpx import AsyncClient

from app.services.daily_challenge import (
    CHALLENGES,
    daily_index,
    get_today,
)


def test_daily_index_is_deterministic_per_date() -> None:
    d1 = _dt.date(2026, 5, 5)
    d2 = _dt.date(2026, 5, 6)
    # Same date → same index. Adjacent dates increment cleanly.
    assert daily_index(d1) == daily_index(d1)
    assert daily_index(d2) == (daily_index(d1) + 1) % len(CHALLENGES)


def test_daily_index_in_bounds() -> None:
    for n in range(1, 100):
        idx = daily_index(_dt.date(2026, 1, 1) + _dt.timedelta(days=n))
        assert 0 <= idx < len(CHALLENGES)


def test_get_today_returns_known_challenge() -> None:
    challenge = get_today()
    assert challenge.id in {c.id for c in CHALLENGES}
    assert challenge.board_size in (9, 13, 19)
    assert challenge.to_move in ("B", "W")


@pytest.mark.asyncio
async def test_get_endpoint_unauth_returns_401(client: AsyncClient) -> None:
    r = await client.get("/api/daily-challenge")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_endpoint_returns_today(client: AsyncClient) -> None:
    r = await client.post("/api/session", json={"nickname": "daily_user"})
    assert r.status_code == 201
    r = await client.get("/api/daily-challenge")
    assert r.status_code == 200
    body = r.json()
    assert "id" in body
    assert "board_size" in body
    assert "setup" in body
    assert isinstance(body["setup"], list)
    assert "to_move" in body
    assert "prompt_key" in body


@pytest.mark.asyncio
async def test_answer_grades_via_katago(client: AsyncClient) -> None:
    await client.post("/api/session", json={"nickname": "daily_grader"})
    today = get_today()
    used = {coord.upper() for _, coord in today.setup}
    candidate = next(
        c
        for c in ("A1", "B1", "C1", "D1", "F1", "H1", "J1")
        if c not in used
    )

    r = await client.post(
        "/api/daily-challenge/answer",
        json={"challenge_id": today.id, "coord": candidate},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] in ("best", "ok", "weak", "miss", "illegal")
    assert isinstance(body["top_moves"], list)
    assert "winrate_before" in body
    assert "drop" in body


@pytest.mark.asyncio
async def test_answer_rolled_over_id_rejected(client: AsyncClient) -> None:
    await client.post("/api/session", json={"nickname": "daily_stale"})
    r = await client.post(
        "/api/daily-challenge/answer",
        json={"challenge_id": "ch-not-real", "coord": "A1"},
    )
    assert r.status_code == 410
    # The project wraps HTTPException into {"error": {"code", "message_key"}}.
    assert r.json()["error"]["code"] == "challenge_rolled_over"
