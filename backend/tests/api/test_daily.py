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
async def test_answer_unknown_id_returns_404(client: AsyncClient) -> None:
    """Daily-only gate is removed — any catalogue id is gradable. An ID
    that doesn't exist in the catalogue 404s instead of 410."""
    await client.post("/api/session", json={"nickname": "daily_unknown"})
    r = await client.post(
        "/api/daily-challenge/answer",
        json={"challenge_id": "ch-not-real", "coord": "A1"},
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "challenge_not_found"


@pytest.mark.asyncio
async def test_random_endpoint_returns_match(client: AsyncClient) -> None:
    await client.post("/api/session", json={"nickname": "daily_random"})
    r = await client.get(
        "/api/daily-challenge/random",
        params={"board_size": 9, "topic": "opening"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["board_size"] == 9
    assert body["topic"] == "opening"


@pytest.mark.asyncio
async def test_random_endpoint_404_when_no_match(client: AsyncClient) -> None:
    """No 19x19 puzzles in the V1 catalogue — request that combo and the
    UI must see a 404 so it can disable the option, not a 500."""
    await client.post("/api/session", json={"nickname": "daily_nomatch"})
    r = await client.get(
        "/api/daily-challenge/random",
        params={"board_size": 19},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_catalogue_returns_options_and_counts(client: AsyncClient) -> None:
    await client.post("/api/session", json={"nickname": "daily_cat"})
    r = await client.get("/api/daily-challenge/catalogue")
    assert r.status_code == 200
    body = r.json()
    assert set(body["board_sizes"]) == {9, 13, 19}
    assert set(body["difficulties"]) == {"easy", "medium", "hard"}
    assert set(body["topics"]) == {
        "opening", "middle_game", "endgame", "life_death",
    }
    # Counts present for every (size, difficulty, topic) cell.
    assert isinstance(body["counts"], dict)
    assert "9|easy|opening" in body["counts"]
    assert isinstance(body["counts"]["9|easy|opening"], int)


@pytest.mark.asyncio
async def test_answer_grades_non_today_challenge(client: AsyncClient) -> None:
    """Pick a catalogue puzzle that is NOT today's and grade against it.
    Used to be 410-blocked; now must succeed."""
    await client.post("/api/session", json={"nickname": "daily_other"})
    other = next(c for c in CHALLENGES if c.id != get_today().id)
    used = {coord.upper() for _, coord in other.setup}
    candidate = next(
        c for c in (
            "A1", "B1", "F1", "H1", "J1", "L1", "M1",
            "A9", "B9", "F9", "H9", "J9",
        ) if c not in used
    )
    r = await client.post(
        "/api/daily-challenge/answer",
        json={"challenge_id": other.id, "coord": candidate},
    )
    assert r.status_code == 200
    assert r.json()["verdict"] in ("best", "ok", "weak", "miss", "illegal")
